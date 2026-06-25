import logging

from odoo import Command, _, api, fields, models
from odoo.exceptions import MissingError, UserError

_logger = logging.getLogger(__name__)


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    mobile_payment_method = fields.Selection(
        selection=[
            ("cash", "Cash"),
            ("cheque", "Cheque"),
            ("bank_transfer", "Bank Transfer"),
        ],
        string="Payment Method",
        default="cash",
    )
    is_mobile_warehouse = fields.Boolean(
        compute="_compute_is_mobile_warehouse", store=True
    )
    mobile_account_missing = fields.Boolean(
        compute="_compute_mobile_account_warning", store=True
    )
    mobile_account_warning = fields.Html(
        compute="_compute_mobile_account_warning", store=True
    )
    mobile_cheque_number = fields.Char(string="Cheque Number")
    mobile_cheque_bank_id = fields.Many2one("res.bank", string="Cheque Bank")
    mobile_cheque_branch = fields.Char(string="Cheque Branch")
    mobile_cheque_date = fields.Date(string="Cheque Date", default=fields.Date.context_today)
    mobile_payment_line_ids = fields.One2many(
        "sale.advance.payment.inv.mobile.line",
        "wizard_id",
        string="Quick Payment Rows",
    )
    mobile_invoice_total = fields.Monetary(
        string="Invoice Total",
        currency_field="currency_id",
        compute="_compute_mobile_payment_totals",
    )
    mobile_actual_payment_total = fields.Monetary(
        string="Received Total",
        currency_field="currency_id",
        compute="_compute_mobile_payment_totals",
    )
    mobile_rounding_total = fields.Monetary(
        string="Rounding Total",
        currency_field="currency_id",
        compute="_compute_mobile_payment_totals",
    )
    mobile_settlement_total = fields.Monetary(
        string="Settlement Total",
        currency_field="currency_id",
        compute="_compute_mobile_payment_totals",
    )
    mobile_balance = fields.Monetary(
        string="Remaining Balance",
        currency_field="currency_id",
        compute="_compute_mobile_payment_totals",
    )
    mobile_amount_exceeded = fields.Boolean(compute="_compute_mobile_payment_totals")
    mobile_settlement_ready = fields.Boolean(compute="_compute_mobile_payment_totals")

    @api.depends(
        "amount_to_invoice",
        "mobile_payment_line_ids.payment_type",
        "mobile_payment_line_ids.amount",
        "mobile_account_missing",
    )
    def _compute_mobile_payment_totals(self):
        for wizard in self:
            actual_lines = wizard.mobile_payment_line_ids.filtered(
                lambda line: line.payment_type != "rounding"
            )
            rounding_lines = wizard.mobile_payment_line_ids.filtered(
                lambda line: line.payment_type == "rounding"
            )
            invoice_total = wizard.amount_to_invoice
            actual_total = sum(actual_lines.mapped("amount"))
            rounding_total = sum(rounding_lines.mapped("amount"))
            settlement_total = actual_total + rounding_total
            currency = wizard.currency_id or self.env.company.currency_id

            wizard.mobile_invoice_total = invoice_total
            wizard.mobile_actual_payment_total = actual_total
            wizard.mobile_rounding_total = rounding_total
            wizard.mobile_settlement_total = settlement_total
            wizard.mobile_balance = invoice_total - settlement_total
            wizard.mobile_amount_exceeded = (
                currency.compare_amounts(settlement_total, invoice_total) > 0
            )
            wizard.mobile_settlement_ready = bool(actual_lines) and (
                currency.compare_amounts(settlement_total, invoice_total) == 0
            ) and not wizard.mobile_account_missing

    def _validate_mobile_payment_lines(self, invoice_total, allow_partial=False):
        self.ensure_one()
        currency = self.currency_id or self.env.company.currency_id
        actual_lines = self.mobile_payment_line_ids.filtered(
            lambda line: line.payment_type != "rounding"
        )
        if not actual_lines:
            raise UserError(_("At least one actual payment row is required."))
        incomplete_cheques = actual_lines.filtered(
            lambda line: line.payment_type == "cheque"
            and (not line.cheque_number or not line.cheque_bank_id)
        )
        if incomplete_cheques:
            raise UserError(_("Please fill in Cheque Number and Bank for each Cheque payment."))

        settlement_total = sum(self.mobile_payment_line_ids.mapped("amount"))
        comparison = currency.compare_amounts(settlement_total, invoice_total)
        if comparison > 0:
            raise UserError(_("Payment settlement exceeds the invoice total."))
        if comparison < 0 and not allow_partial:
            raise UserError(_("Payment settlement must equal the invoice total."))

    def _prepare_down_payment_lines_values(self, order):
        lines_values, accounts = super()._prepare_down_payment_lines_values(order)

        company = self.company_id or order.company_id
        if (
            self.advance_payment_method in ("percentage", "fixed")
            and company.downpayment_account_id
        ):
            accounts = [company.downpayment_account_id for _ in accounts]

        return lines_values, accounts

    @api.depends("sale_order_ids.warehouse_id.name")
    def _compute_is_mobile_warehouse(self):
        for wizard in self:
            orders = wizard.sale_order_ids
            target_name = "mobile warehouse"
            wizard.is_mobile_warehouse = bool(
                orders
                and all(
                    so.warehouse_id
                    and target_name in (so.warehouse_id.name or "").strip().lower()
                    for so in orders
                )
            )
            if (
                wizard.is_mobile_warehouse
                and wizard.advance_payment_method != "delivered"
            ):
                wizard.advance_payment_method = "delivered"

    @api.depends(
        "sale_order_ids.company_id",
        "mobile_payment_method",
        "is_mobile_warehouse",
        "mobile_payment_line_ids.payment_type",
    )
    def _compute_mobile_account_warning(self):
        for wizard in self:
            wizard.mobile_account_missing = False
            wizard.mobile_account_warning = False
            if not wizard.is_mobile_warehouse:
                continue

            companies = wizard.sale_order_ids.company_id
            if companies and len(companies) > 1:
                wizard.mobile_account_missing = True
                wizard.mobile_account_warning = _(
                    "Select sale orders from a single company to invoice Mobile Warehouse orders."
                )
                continue

            company = companies[:1] or wizard.company_id or self.env.company
            payment_types = set(
                wizard.mobile_payment_line_ids.filtered(
                    lambda line: line.payment_type != "rounding"
                ).mapped("payment_type")
            )
            if not payment_types:
                payment_types = {
                    "bank"
                    if wizard.mobile_payment_method == "bank_transfer"
                    else wizard.mobile_payment_method
                }

            missing_labels = []
            journal_by_type = {
                "cash": (company.mobile_cash_journal_id, _("Cash Journal")),
                "cheque": (company.mobile_cheque_journal_id, _("Cheque Journal")),
                "bank": (
                    company.mobile_bank_transfer_journal_id,
                    _("Bank Transfer Journal"),
                ),
            }
            for payment_type in sorted(payment_types):
                journal, label = journal_by_type.get(payment_type, (False, False))
                if label and not journal:
                    missing_labels.append(label)
            if (
                wizard.mobile_payment_line_ids.filtered(
                    lambda line: line.payment_type == "rounding"
                )
                and not company.auto_diff_account_id
            ):
                missing_labels.append(_("Rounding Difference Account"))

            if missing_labels:
                wizard.mobile_account_missing = True
                wizard.mobile_account_warning = (
                    _(
                        "%s is not set. Go to Sales -> Settings -> Mobile Warehouse Invoicing to configure it."
                    )
                    % ", ".join(missing_labels)
                )

    def action_create_invoice_posted(self):
        self._check_amount_is_positive()
        if self.is_mobile_warehouse:
            if self.mobile_payment_method != "cheque":
                raise UserError(
                    _(
                        "Use Create Invoice Paid for Cash or Bank Transfer. "
                        "Create Invoice (Posted) is available only for Cheque to keep the invoice unpaid."
                    )
                )
            self._ensure_mobile_journal_configured()
            invoices = self._create_invoices(self.sale_order_ids)
        else:
            invoices = self._create_invoices(self.sale_order_ids)
        return self.sale_order_ids.action_view_invoice(invoices=invoices)

    def action_create_invoice_paid(self):
        self._check_amount_is_positive()
        journal = (
            self._ensure_mobile_journal_configured()
            if self.is_mobile_warehouse
            else None
        )
        invoices = self._create_invoices(self.sale_order_ids)
        if invoices and self.is_mobile_warehouse:
            self._log_invoice_partner_lines(invoices, label="before payment")
        if invoices and self.is_mobile_warehouse:
            self._register_mobile_payments(invoices, journal)
        return self.sale_order_ids.action_view_invoice(invoices=invoices)

    def action_create_invoice_mobile(self):
        self.ensure_one()
        if not self.is_mobile_warehouse:
            return self.create_invoices()

        self._check_amount_is_positive()
        invoices = self._create_invoices(self.sale_order_ids)
        return self.sale_order_ids.action_view_invoice(invoices=invoices)

    def _create_invoices(self, sale_orders):
        self._ensure_downpayment_account_configured()
        invoices = super()._create_invoices(sale_orders)
        if self.is_mobile_warehouse and invoices:
            self._log_invoice_partner_lines(
                invoices, label="after creation (no override)"
            )
        draft_moves = invoices.filtered(lambda m: m.state == "draft")
        if draft_moves:
            draft_moves.action_post()
        return invoices

    def _ensure_downpayment_account_configured(self):
        if self.advance_payment_method not in ("percentage", "fixed"):
            return

        company = self.company_id or self.env.company
        if not company.downpayment_account_id:
            raise UserError(
                _(
                    "Please set a Down Payment Account in Sales → Settings → "
                    "Invoicing → Down Payment Accounting."
                )
            )

    def _get_mobile_payment_journal(self):
        self.ensure_one()
        company = self._get_target_company()
        if self.mobile_payment_method == "cash":
            journal = company.mobile_cash_journal_id
            missing = _("Cash Journal")
        elif self.mobile_payment_method == "cheque":
            journal = company.mobile_cheque_journal_id
            missing = _("Cheque Journal")
        else:
            journal = company.mobile_bank_transfer_journal_id
            missing = _("Bank Transfer Journal")

        if not journal:
            raise UserError(
                _(
                    "Please configure the %s in Sales → Settings → Mobile Warehouse Invoicing to invoice Mobile Warehouse orders."
                )
                % missing
            )
        _logger.info(
            "Mobile payment method %s -> journal %s (company %s)",
            self.mobile_payment_method,
            journal.display_name,
            company.display_name,
        )
        return journal

    def _ensure_mobile_journal_configured(self):
        self.ensure_one()
        journal = self._get_mobile_payment_journal()
        if self.mobile_account_missing:
            # Show same message as the warning box to block progression.
            raise UserError(
                self.mobile_account_warning
                or _("Please configure the required journal for this payment method.")
            )
        return journal

    def _get_target_company(self):
        companies = self.sale_order_ids.company_id
        if companies:
            if len(companies) > 1:
                raise UserError(
                    _(
                        "Please select sale orders belonging to a single company when invoicing Mobile Warehouse orders."
                    )
                )
            return companies[:1]
        return self.company_id or self.env.company

    def _register_mobile_payments(self, invoices, journal):
        if not journal:
            return
        try:
            invoices_to_pay = invoices.filtered(
                lambda move: move.state != "cancel" and move.is_invoice(True)
            )
            draft_moves = invoices_to_pay.filtered(lambda move: move.state == "draft")
            if draft_moves:
                draft_moves.action_post()
            posted_invoices = invoices_to_pay.filtered(
                lambda move: move.state == "posted"
            )
            if not posted_invoices:
                return
            companies = posted_invoices.company_id
            if len(companies) > 1:
                raise UserError(
                    _(
                        "Please invoice Mobile Warehouse orders for one company at a time when using the auto-payment button."
                    )
                )
            if companies[:1] != journal.company_id:
                raise UserError(
                    _(
                        "The selected journal '%s' does not belong to company '%s'. Please pick a matching journal."
                    )
                    % (journal.display_name, companies[:1].display_name)
                )
            method_line = self._get_payment_method_line_for_journal(journal)
            ctx = dict(self.env.context or {})
            ctx["skip_caba_zero_cleanup"] = True
            ctx["skip_mobile_caba_adjustments"] = True
            # Mobile auto-pay: avoid cash-basis hooks that may delete lines mid-flow
            ctx["no_cash_basis"] = True
            ctx["active_model"] = "account.move"
            ctx["active_ids"] = posted_invoices.ids
            ctx["active_id"] = posted_invoices.ids[0] if posted_invoices else False
            try:
                register = (
                    self.env["account.payment.register"]
                    .with_context(ctx)
                    .create(
                        {
                            "journal_id": journal.id,
                            "payment_method_line_id": method_line.id,
                        }
                    )
                )

                if self.mobile_payment_method == "cheque":
                    if not self.mobile_cheque_number or not self.mobile_cheque_bank_id:
                        raise UserError(_("Please fill in Cheque Number and Bank for the Cheque Payment."))
                    register.wizard_inbound_cheque_lines = [
                        (0, 0, {
                            "cheque_id": self.mobile_cheque_number,
                            "bank_account_id": self.mobile_cheque_bank_id.id,
                            "branch": self.mobile_cheque_branch or "",
                            "date": self.mobile_cheque_date or fields.Date.context_today(self),
                            "amount": register.amount,
                        })
                    ]

                payments = register.with_context(ctx)._create_payments()
                if not payments:
                    raise UserError(
                        _(
                            "Mobile auto-payment could not be created; please review the cash journal/payment method configuration."
                        )
                    )
            except MissingError:
                _logger.exception(
                    "Mobile auto-payment skipped because a journal item vanished during creation; "
                    "falling back to manual payment creation."
                )
                payments = self._fallback_create_mobile_payments(
                    posted_invoices, journal, method_line, ctx
                )
                if not payments:
                    return
            except UserError as e:
                _logger.exception("Mobile auto-payment failed: %s", str(e))
                raise
            to_post = payments.filtered(lambda p: p.state != "posted")
            if to_post:
                try:
                    to_post.with_context(ctx).action_post()
                except MissingError:
                    _logger.exception(
                        "Mobile auto-payment posting failed because a journal item vanished; "
                        "payments left unposted for manual handling."
                    )
            # Manual reconciliation to ensure payment status
            pay_lines = payments.mapped("move_id.line_ids").filtered(
                lambda l: (
                    l.account_id.account_type
                    in ("asset_receivable", "liability_payable")
                    and not l.reconciled
                    and l.parent_state == "posted"
                )
            )
            inv_lines = posted_invoices.mapped("line_ids").filtered(
                lambda l: (
                    l.account_id.account_type
                    in ("asset_receivable", "liability_payable")
                    and not l.reconciled
                    and l.parent_state == "posted"
                )
            )
            if pay_lines and inv_lines:
                accounts = pay_lines.account_id | inv_lines.account_id
                for acc in accounts:
                    lines = (pay_lines + inv_lines).filtered(
                        lambda l, a=acc: l.account_id == a and not l.reconciled
                    )
                    if len(lines) > 1:
                        lines.with_context(ctx).reconcile()
            unpaid = posted_invoices.filtered(
                lambda m: m.payment_state not in ("paid", "in_payment")
            )
            if unpaid:
                _logger.warning(
                    "Mobile auto-payment created but invoices remain unpaid: %s",
                    ", ".join(unpaid.mapped("name")),
                )
            else:
                _logger.info(
                    "Mobile auto-payment completed for invoices: %s",
                    ", ".join(posted_invoices.mapped("name")),
                )
        except MissingError:
            _logger.exception(
                "Mobile auto-payment aborted because a referenced journal item vanished; "
                "invoices left unpaid for manual handling."
            )

    def _register_mobile_payment_lines(self, invoice):
        self.ensure_one()
        if len(invoice) != 1:
            raise UserError(_("Quick Payment Rows require exactly one customer invoice."))
        invoice.ensure_one()
        if invoice.state != "posted" or not invoice.is_invoice(True):
            raise UserError(_("Quick Payment Rows require one posted customer invoice."))

        self._validate_mobile_payment_lines(invoice.amount_residual, allow_partial=True)
        actual_lines = self.mobile_payment_line_ids.filtered(
            lambda line: line.payment_type != "rounding"
        ).sorted(lambda line: (line.sequence, line.id))
        rounding_total = sum(
            self.mobile_payment_line_ids.filtered(
                lambda line: line.payment_type == "rounding"
            ).mapped("amount")
        )
        company = invoice.company_id
        if rounding_total and not company.auto_diff_account_id:
            raise UserError(
                _("Please configure the Rounding Difference Account before receiving payment.")
            )

        ctx = dict(self.env.context or {})
        for key in (
            "no_cash_basis",
            "skip_caba_zero_cleanup",
            "skip_mobile_caba_adjustments",
            "dont_redirect_to_payments",
        ):
            ctx.pop(key, None)
        ctx.update(
            {
                "active_model": "account.move",
                "active_ids": invoice.ids,
                "active_id": invoice.id,
            }
        )

        cheque_lines = actual_lines.filtered(lambda l: l.payment_type == "cheque")
        for line in cheque_lines:
            journal = self._get_mobile_payment_journal_for_type(line.payment_type)
            method_line = self._get_payment_method_line_for_journal(
                journal, line.payment_type
            )
            register_vals = {
                "journal_id": journal.id,
                "payment_method_line_id": method_line.id,
                "amount": line.amount,
                "payment_date": fields.Date.context_today(self),
            }
            register = (
                self.env["account.payment.register"].with_context(ctx).create(register_vals)
            )
            register.wizard_inbound_cheque_lines = [
                Command.create(
                    {
                        "cheque_id": line.cheque_number,
                        "bank_account_id": line.cheque_bank_id.id,
                        "branch": line.cheque_branch or "",
                        "date": line.cheque_date or fields.Date.context_today(self),
                        "amount": line.amount,
                    }
                )
            ]
            register.action_create_payments()

        other_actual_lines = actual_lines.filtered(lambda l: l.payment_type != "cheque")
        if other_actual_lines:
            main_line = other_actual_lines[0]
            other_lines = other_actual_lines[1:]
            journal = self._get_mobile_payment_journal_for_type(main_line.payment_type)
            method_line = self._get_payment_method_line_for_journal(
                journal, main_line.payment_type
            )
            register_vals = {
                "journal_id": journal.id,
                "payment_method_line_id": method_line.id,
                "amount": main_line.amount,
                "payment_date": fields.Date.context_today(self),
            }

            deduction_commands = []
            for line in other_lines:
                other_journal = self._get_mobile_payment_journal_for_type(line.payment_type)
                other_method_line = self._get_payment_method_line_for_journal(
                    other_journal, line.payment_type
                )
                deduction_commands.append(
                    Command.create(
                        {
                            "account_id": other_method_line.payment_account_id.id,
                            "name": f"{line.payment_type.upper()} Payment",
                            "amount": line.amount,
                            "is_open": False,
                        }
                    )
                )

            if rounding_total:
                deduction_commands.append(
                    Command.create(
                        {
                            "account_id": company.auto_diff_account_id.id,
                            "name": company.auto_diff_label or _("Rounding Difference"),
                            "amount": rounding_total,
                            "analytic_distribution": company.auto_diff_analytic_distribution
                            or {},
                            "is_open": False,
                        }
                    )
                )

            if deduction_commands:
                register_vals.update(
                    {
                        "payment_difference_handling": "reconcile_multi_deduct",
                        "deduction_ids": deduction_commands,
                    }
                )

            register = (
                self.env["account.payment.register"].with_context(ctx).create(register_vals)
            )
            register.action_create_payments()

    def _get_mobile_payment_journal_for_type(self, payment_type):
        self.ensure_one()
        company = self._get_target_company()
        journals = {
            "bank": (company.mobile_bank_transfer_journal_id, _("Bank Transfer Journal")),
            "cash": (company.mobile_cash_journal_id, _("Cash Journal")),
            "cheque": (company.mobile_cheque_journal_id, _("Cheque Journal")),
        }
        journal, label = journals.get(payment_type, (False, _("Payment Journal")))
        if not journal:
            raise UserError(
                _("Please configure the %s for Mobile Warehouse invoicing.") % label
            )
        if journal.company_id != company:
            raise UserError(
                _("The configured %s does not belong to the invoice company.") % label
            )
        return journal

    def _log_invoice_partner_lines(self, invoices, label):
        for inv in invoices:
            partner_lines = inv.line_ids.filtered(
                lambda l: (
                    l.account_id.account_type
                    in ("asset_receivable", "liability_payable")
                )
            )
            entries = []
            for line in partner_lines:
                entries.append(
                    "%s | maturity=%s | balance=%s"
                    % (line.account_id.display_name, line.date_maturity, line.balance)
                )
            _logger.info(
                "Mobile invoice %s [%s]: %s",
                inv.name or inv.id,
                label,
                "; ".join(entries),
            )

    def _normalize_due_dates(self, move):
        maturity = move.invoice_date_due or move.date or fields.Date.context_today(self)
        partner_lines = move.line_ids.filtered(
            lambda line: (
                line.account_id.account_type
                in ("asset_receivable", "liability_payable")
            )
        )
        partner_lines_filtered = partner_lines.filtered(lambda l: not l.date_maturity)
        if partner_lines_filtered:
            partner_lines_filtered.write({"date_maturity": maturity})
        non_partner = move.line_ids.filtered(
            lambda l: (
                l.account_id.account_type
                not in ("asset_receivable", "liability_payable")
                and l.date_maturity
            )
        )
        if non_partner:
            non_partner.write({"date_maturity": False})
        if partner_lines_filtered or non_partner:
            _logger.info(
                "Normalized due dates on move %s: partner set=%s, non-partner cleared=%s",
                move.name or move.id,
                len(partner_lines_filtered),
                len(non_partner),
            )

    def _get_payment_method_line_for_journal(self, journal, payment_type=None):
        self.ensure_one()
        method_lines = journal.inbound_payment_method_line_ids
        cheque_lines = method_lines.filtered(
            lambda line: line.is_cheque_incoming_line
            or line.code in ("cheque", "cheque_incoming")
        )
        if payment_type == "cheque":
            method_line = cheque_lines[:1]
        else:
            method_line = (method_lines - cheque_lines)[:1]
        if not method_line:
            raise UserError(
                _(
                    "No suitable inbound payment method line found for journal '%s'. Please configure one."
                )
                % (journal.display_name,)
            )
        if not method_line.payment_account_id:
            raise UserError(
                _(
                    "Please configure the Outstanding Receipts Account for payment method '%s'."
                )
                % method_line.display_name
            )
        _logger.info(
            "Mobile payment method line selected: %s",
            method_line.display_name,
        )
        return method_line

    def _fallback_create_mobile_payments(
        self, invoices, journal, method_line, ctx
    ):
        """Direct payment creation if the wizard fails with MissingError."""
        payments = self.env["account.payment"]
        for inv in invoices:
            if inv.state != "posted" or not inv.is_invoice(True):
                continue
            pay_vals = {
                "payment_type": "inbound"
                if inv.move_type in ("out_invoice", "out_refund")
                else "outbound",
                "partner_type": "customer"
                if inv.move_type in ("out_invoice", "out_refund")
                else "supplier",
                "partner_id": inv.partner_id.id,
                "amount": abs(inv.amount_residual),
                "currency_id": inv.currency_id.id,
                "journal_id": journal.id,
                "payment_method_line_id": method_line.id,
                "date": fields.Date.context_today(self),
                "payment_reference": inv.payment_reference or inv.name,
                "memo": inv.name,
                "company_id": inv.company_id.id,
            }
            payments |= self.env["account.payment"].with_context(ctx).create(pay_vals)
        if payments:
            _logger.info(
                "Mobile auto-payment fallback created %s payment(s) for invoices: %s",
                len(payments),
                ", ".join(invoices.mapped("name")),
            )
        return payments
