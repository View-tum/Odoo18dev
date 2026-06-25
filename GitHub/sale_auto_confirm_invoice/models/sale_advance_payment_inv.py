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
    mobile_receive_payment_only = fields.Boolean(
        string="Receive Existing Invoice Payment",
        default=lambda self: self.env.context.get("default_mobile_receive_payment_only", False),
    )
    mobile_payment_invoice_ids = fields.Many2many(
        "account.move",
        string="Invoices to Pay",
    )
    mobile_credit_note_line_ids = fields.One2many(
        "sale.advance.payment.inv.credit.note.line",
        "wizard_id",
        string="Customer Credit Notes",
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
    mobile_credit_note_total = fields.Monetary(
        string="Credit Note Total",
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
        "mobile_receive_payment_only",
        "mobile_payment_invoice_ids.amount_residual",
        "mobile_payment_line_ids.payment_type",
        "mobile_payment_line_ids.amount",
        "mobile_credit_note_line_ids.is_selected",
        "mobile_credit_note_line_ids.amount",
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
            invoice_total = wizard._get_mobile_payment_target_amount()
            actual_total = sum(actual_lines.mapped("amount"))
            rounding_total = sum(rounding_lines.mapped("amount"))
            credit_note_total = sum(
                wizard._get_selected_mobile_credit_note_lines().mapped("amount")
            )
            settlement_total = actual_total + rounding_total + credit_note_total
            currency = wizard.currency_id or self.env.company.currency_id

            wizard.mobile_invoice_total = invoice_total
            wizard.mobile_actual_payment_total = actual_total
            wizard.mobile_rounding_total = rounding_total
            wizard.mobile_credit_note_total = credit_note_total
            wizard.mobile_settlement_total = settlement_total
            wizard.mobile_balance = invoice_total - settlement_total
            wizard.mobile_amount_exceeded = (
                currency.compare_amounts(settlement_total, invoice_total) > 0
            )
            wizard.mobile_settlement_ready = bool(actual_lines or credit_note_total) and (
                currency.compare_amounts(settlement_total, invoice_total) == 0
            ) and not wizard.mobile_account_missing

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        if not self.env.context.get("default_mobile_receive_payment_only"):
            return values

        orders = self.env["sale.order"].browse(self.env.context.get("active_ids", []))
        invoices = self._get_open_payment_invoices_for_orders(orders)
        if invoices:
            values["mobile_payment_invoice_ids"] = [Command.set(invoices.ids)]
            values["mobile_credit_note_line_ids"] = self._prepare_credit_note_line_commands(invoices)
        return values

    def _get_mobile_payment_target_amount(self):
        self.ensure_one()
        if self.mobile_receive_payment_only:
            invoices = self._get_mobile_payment_target_invoices()
            return sum(invoices.mapped("amount_residual"))
        return self.amount_to_invoice

    def _get_mobile_payment_target_invoices(self):
        self.ensure_one()
        if self.mobile_payment_invoice_ids:
            return self.mobile_payment_invoice_ids.filtered(
                lambda move: move.state == "posted"
                and move.move_type == "out_invoice"
                and not move.currency_id.is_zero(move.amount_residual)
            )
        return self._get_open_payment_invoices_for_orders(self.sale_order_ids)

    @api.model
    def _get_open_payment_invoices_for_orders(self, orders):
        invoices = self.env["account.move"]
        for order in orders:
            invoices |= order._get_van_sales_open_payment_invoices()
        return invoices

    @api.model
    def _prepare_credit_note_line_commands(self, invoices):
        if not invoices:
            return []
        partner = invoices.partner_id.commercial_partner_id
        company = invoices.company_id
        currency = invoices.currency_id
        if len(partner) != 1 or len(company) != 1 or len(currency) != 1:
            return []
        credit_notes = self.env["account.move"].search(
            [
                ("move_type", "=", "out_refund"),
                ("state", "=", "posted"),
                ("company_id", "=", company.id),
                ("currency_id", "=", currency.id),
                ("commercial_partner_id", "=", partner.id),
                ("amount_residual", ">", 0),
            ],
            order="invoice_date, name, id",
        )
        commands = []
        for credit_note in credit_notes:
            receivable_line = credit_note.line_ids.filtered(
                lambda line: line.account_type == "asset_receivable"
                and not line.reconciled
                and line.parent_state == "posted"
            )[:1]
            commands.append(
                Command.create(
                    {
                        "move_id": credit_note.id,
                        "account_id": receivable_line.account_id.id,
                        "open_amount": credit_note.amount_residual,
                        "amount": 0.0,
                    }
                )
            )
        return commands

    def _get_selected_mobile_credit_note_lines(self):
        self.ensure_one()
        currency = self.currency_id or self.env.company.currency_id
        return self.mobile_credit_note_line_ids.filtered(
            lambda line: line.is_selected and line.move_id and not currency.is_zero(line.amount)
        )

    def _validate_mobile_payment_lines(
        self, invoice_total, allow_partial=False, include_credit_notes=True
    ):
        self.ensure_one()
        currency = self.currency_id or self.env.company.currency_id
        actual_lines = self.mobile_payment_line_ids.filtered(
            lambda line: line.payment_type != "rounding"
        )
        selected_credit_notes = (
            self._get_selected_mobile_credit_note_lines()
            if include_credit_notes
            else self.env["sale.advance.payment.inv.credit.note.line"]
        )
        rounding_lines = self.mobile_payment_line_ids.filtered(
            lambda line: line.payment_type == "rounding"
        )
        if not actual_lines and not selected_credit_notes:
            raise UserError(_("At least one actual payment row is required."))
        if rounding_lines and not actual_lines:
            raise UserError(_("Rounding can be used only together with an actual payment row."))
        incomplete_cheques = actual_lines.filtered(
            lambda line: line.payment_type == "cheque"
            and (not line.cheque_number or not line.cheque_bank_id)
        )
        if incomplete_cheques:
            raise UserError(_("Please fill in Cheque Number and Bank for each Cheque payment."))

        settlement_total = sum(self.mobile_payment_line_ids.mapped("amount")) + sum(
            selected_credit_notes.mapped("amount")
        )
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

    def action_receive_mobile_payment(self):
        self.ensure_one()
        invoices = self._get_mobile_payment_target_invoices()
        if not invoices:
            raise UserError(_("No open posted customer invoice is available for payment."))
        if len(invoices) != 1:
            raise UserError(_("Please receive payment for one invoice at a time from this button."))

        invoice = invoices[:1]
        invoice_total = invoice.amount_residual
        self._normalize_mobile_credit_note_lines()
        self._validate_mobile_credit_note_lines(invoice)
        self._validate_mobile_payment_lines(invoice_total, allow_partial=True)

        actual_lines = self.mobile_payment_line_ids.filtered(
            lambda line: line.payment_type != "rounding"
        )
        if actual_lines:
            self._register_mobile_payment_lines(invoice)
        else:
            self._apply_mobile_credit_notes(invoice)
        return self.sale_order_ids.action_view_invoice(invoices=invoice)

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

    def _validate_mobile_credit_note_lines(self, invoice):
        self.ensure_one()
        invoice.ensure_one()
        currency = invoice.currency_id
        invalid_selected_lines = self.mobile_credit_note_line_ids.filtered(
            lambda line: line.is_selected and not line.move_id
        )
        if invalid_selected_lines:
            raise UserError(_("Please select a valid customer credit note."))
        selected_lines = self._get_selected_mobile_credit_note_lines()
        selected_moves = self.env["account.move"]
        for line in selected_lines:
            credit_note = line.move_id
            if credit_note in selected_moves:
                raise UserError(_("The same credit note cannot be selected more than once."))
            selected_moves |= credit_note
            if credit_note.move_type != "out_refund" or credit_note.state != "posted":
                raise UserError(_("Only posted customer credit notes can be applied."))
            if credit_note.company_id != invoice.company_id:
                raise UserError(_("Credit note company must match the invoice company."))
            if credit_note.currency_id != invoice.currency_id:
                raise UserError(_("Credit note currency must match the invoice currency."))
            if (
                credit_note.commercial_partner_id
                != invoice.commercial_partner_id
            ):
                raise UserError(_("Credit note customer must match the invoice customer."))
            if currency.compare_amounts(line.amount, credit_note.amount_residual) > 0:
                raise UserError(_("Credit note apply amount exceeds the current open amount."))
        if currency.compare_amounts(sum(selected_lines.mapped("amount")), invoice.amount_residual) > 0:
            raise UserError(_("Credit note amount exceeds the invoice open amount."))

    def _apply_mobile_credit_notes(self, invoice):
        self.ensure_one()
        invoice.ensure_one()
        currency = invoice.currency_id
        selected_lines = self._get_selected_mobile_credit_note_lines().sorted(
            lambda line: (line.date or fields.Date.today(), line.move_id.name or "", line.id)
        )
        for selected_line in selected_lines:
            self._apply_single_mobile_credit_note(invoice, selected_line)

    def _normalize_mobile_credit_note_lines(self):
        self.ensure_one()
        for line in self.mobile_credit_note_line_ids.filtered(
            lambda note_line: note_line.is_selected
            and note_line.move_id
            and note_line.currency_id.is_zero(note_line.amount)
        ):
            line.amount = line.open_amount

    def _apply_single_mobile_credit_note(self, invoice, selected_line):
        currency = invoice.currency_id
        remaining = selected_line.amount
        invoice_lines = invoice.line_ids.filtered(
            lambda line: line.account_type == "asset_receivable"
            and line.parent_state == "posted"
            and not line.reconciled
            and currency.compare_amounts(abs(line.amount_residual_currency or line.amount_residual), 0.0) > 0
        )
        credit_lines = selected_line.move_id.line_ids.filtered(
            lambda line: line.account_type == "asset_receivable"
            and line.parent_state == "posted"
            and not line.reconciled
            and line.account_id in invoice_lines.account_id
            and currency.compare_amounts(abs(line.amount_residual_currency or line.amount_residual), 0.0) > 0
        )
        for invoice_line in invoice_lines:
            if currency.is_zero(remaining):
                break
            for credit_line in credit_lines:
                if currency.is_zero(remaining):
                    break
                invoice_available = abs(
                    invoice_line.amount_residual_currency
                    if invoice_line.currency_id == currency
                    else invoice_line.amount_residual
                )
                credit_available = abs(
                    credit_line.amount_residual_currency
                    if credit_line.currency_id == currency
                    else credit_line.amount_residual
                )
                amount_currency = min(remaining, invoice_available, credit_available)
                if currency.is_zero(amount_currency):
                    continue
                debit_line = invoice_line if invoice_line.balance > 0 else credit_line
                credit_move_line = credit_line if debit_line == invoice_line else invoice_line
                amount_company = self._mobile_partial_company_amount(
                    amount_currency, debit_line
                )
                self.env["account.partial.reconcile"].create(
                    {
                        "debit_move_id": debit_line.id,
                        "credit_move_id": credit_move_line.id,
                        "amount": amount_company,
                        "debit_amount_currency": self._mobile_partial_currency_amount(
                            debit_line, amount_company, amount_currency
                        ),
                        "credit_amount_currency": self._mobile_partial_currency_amount(
                            credit_move_line, amount_company, amount_currency
                        ),
                    }
                )
                remaining -= amount_currency
        if not currency.is_zero(remaining):
            raise UserError(_("Credit note could not be fully applied to this invoice."))

    def _prepare_mobile_credit_note_deduction_commands(self, selected_lines):
        commands = []
        for line in selected_lines:
            commands.append(
                Command.create(
                    {
                        "account_id": line.account_id.id,
                        "name": _("Credit Note %s") % line.move_id.name,
                        "amount": line.amount,
                        "is_open": False,
                    }
                )
            )
        return commands

    def _prepare_mobile_open_balance_deduction_command(
        self, invoice, payment_amount, deduction_commands
    ):
        self.ensure_one()
        currency = invoice.currency_id
        deduction_amount = sum(
            (command[2] or {}).get("amount", 0.0)
            for command in deduction_commands
            if isinstance(command, (list, tuple)) and len(command) >= 3
        )
        open_amount = invoice.amount_residual - payment_amount - deduction_amount
        if currency.compare_amounts(open_amount, 0.0) <= 0:
            return False
        return Command.create(
            {
                "name": _("Keep open"),
                "amount": open_amount,
                "is_open": True,
            }
        )

    def _get_mobile_created_payments_from_register(self, register, action_result):
        get_created_payments = getattr(register, "_get_created_payment_records", None)
        if get_created_payments:
            payments = get_created_payments(action_result)
            if payments:
                return payments
        if isinstance(action_result, dict) and action_result.get("res_model") == "account.payment":
            if action_result.get("res_id"):
                return self.env["account.payment"].browse(action_result["res_id"])
            domain = action_result.get("domain") or []
            payment_ids = []
            for domain_item in domain:
                if (
                    isinstance(domain_item, (list, tuple))
                    and len(domain_item) == 3
                    and domain_item[0] == "id"
                    and domain_item[1] == "in"
                ):
                    payment_ids = domain_item[2]
                    break
            if payment_ids:
                return self.env["account.payment"].browse(payment_ids)
        return self.env["account.payment"]

    def _run_mobile_payment_register(self, register):
        payment_model = self.env["account.payment"]
        last_payment = payment_model.search([], order="id desc", limit=1)
        action_result = register.action_create_payments()
        payments = self._get_mobile_created_payments_from_register(
            register, action_result
        )
        new_payments = payment_model.search([("id", ">", last_payment.id or 0)])
        return payments | new_payments

    def _reconcile_mobile_credit_note_payment_invoice_lines(
        self, invoice, payments, selected_line
    ):
        remaining = selected_line.amount
        currency = selected_line.currency_id or selected_line.move_id.currency_id
        invoice_lines = invoice.line_ids.filtered(
            lambda line: line.account_type == "asset_receivable"
            and line.parent_state == "posted"
            and not line.reconciled
            and line.account_id == selected_line.account_id
            and currency.compare_amounts(
                abs(line.amount_residual_currency or line.amount_residual), 0.0
            )
            > 0
        )
        payment_lines = payments.mapped("move_id.line_ids").filtered(
            lambda line: line.account_id == selected_line.account_id
            and line.parent_state == "posted"
            and not line.reconciled
            and line.balance < 0
            and line.partner_id.commercial_partner_id == invoice.commercial_partner_id
        )
        for invoice_line in invoice_lines:
            if currency.is_zero(remaining):
                break
            for payment_line in payment_lines:
                if currency.is_zero(remaining):
                    break
                invoice_available = abs(
                    invoice_line.amount_residual_currency
                    if invoice_line.currency_id == currency
                    else invoice_line.amount_residual
                )
                payment_available = abs(
                    payment_line.amount_residual_currency
                    if payment_line.currency_id == currency
                    else payment_line.amount_residual
                )
                amount_currency = min(remaining, invoice_available, payment_available)
                if currency.is_zero(amount_currency):
                    continue
                amount_company = self._mobile_partial_company_amount(
                    amount_currency, invoice_line
                )
                self.env["account.partial.reconcile"].create(
                    {
                        "debit_move_id": invoice_line.id,
                        "credit_move_id": payment_line.id,
                        "amount": amount_company,
                        "debit_amount_currency": self._mobile_partial_currency_amount(
                            invoice_line, amount_company, amount_currency
                        ),
                        "credit_amount_currency": self._mobile_partial_currency_amount(
                            payment_line, amount_company, amount_currency
                        ),
                    }
                )
                remaining -= amount_currency

    def _reconcile_mobile_credit_note_payment_lines(
        self, invoice, payments, selected_lines, allow_invoice_fallback=False
    ):
        for selected_line in selected_lines:
            currency = selected_line.currency_id or selected_line.move_id.currency_id
            payment_lines = payments.mapped("move_id.line_ids").filtered(
                lambda line: line.account_id == selected_line.account_id
                and line.parent_state == "posted"
                and not line.reconciled
                and line.balance > 0
                and (
                    not line.partner_id
                    or line.partner_id.commercial_partner_id
                    == selected_line.move_id.commercial_partner_id
                )
            )
            if not payment_lines and allow_invoice_fallback:
                self._apply_single_mobile_credit_note(invoice, selected_line)
                continue

            self._reconcile_mobile_credit_note_payment_invoice_lines(
                invoice, payments, selected_line
            )
            remaining = selected_line.amount
            credit_lines = selected_line.move_id.line_ids.filtered(
                lambda line: line.account_type == "asset_receivable"
                and line.parent_state == "posted"
                and not line.reconciled
                and currency.compare_amounts(
                    abs(line.amount_residual_currency or line.amount_residual), 0.0
                )
                > 0
            )
            for payment_line in payment_lines:
                if currency.is_zero(remaining):
                    break
                for credit_line in credit_lines:
                    if currency.is_zero(remaining):
                        break
                    payment_available = abs(
                        payment_line.amount_residual_currency
                        if payment_line.currency_id == currency
                        else payment_line.amount_residual
                    )
                    credit_available = abs(
                        credit_line.amount_residual_currency
                        if credit_line.currency_id == currency
                        else credit_line.amount_residual
                    )
                    amount_currency = min(remaining, payment_available, credit_available)
                    if currency.is_zero(amount_currency):
                        continue
                    amount_company = self._mobile_partial_company_amount(
                        amount_currency, payment_line
                    )
                    self.env["account.partial.reconcile"].create(
                        {
                            "debit_move_id": payment_line.id,
                            "credit_move_id": credit_line.id,
                            "amount": amount_company,
                            "debit_amount_currency": self._mobile_partial_currency_amount(
                                payment_line, amount_company, amount_currency
                            ),
                            "credit_amount_currency": self._mobile_partial_currency_amount(
                                credit_line, amount_company, amount_currency
                            ),
                        }
                    )
                    remaining -= amount_currency
            if not currency.is_zero(remaining):
                raise UserError(
                    _("Credit note %s could not be reconciled with this payment.")
                    % selected_line.move_id.name
                )

    def _mobile_partial_company_amount(self, amount_currency, line):
        company_currency = line.company_currency_id
        if line.currency_id and line.currency_id != company_currency:
            return abs(
                line.currency_id._convert(
                    amount_currency,
                    company_currency,
                    line.company_id,
                    line.date or fields.Date.context_today(line),
                )
            )
        return abs(amount_currency)

    def _mobile_partial_currency_amount(self, line, amount_company, amount_currency):
        if line.currency_id and line.currency_id != line.company_currency_id:
            return abs(amount_currency)
        return abs(amount_company)

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

        self._validate_mobile_payment_lines(
            invoice.amount_residual, allow_partial=True, include_credit_notes=False
        )
        actual_lines = self.mobile_payment_line_ids.filtered(
            lambda line: line.payment_type != "rounding"
        ).sorted(lambda line: (line.sequence, line.id))
        rounding_total = sum(
            self.mobile_payment_line_ids.filtered(
                lambda line: line.payment_type == "rounding"
            ).mapped("amount")
        )
        selected_credit_note_lines = self._get_selected_mobile_credit_note_lines()
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
        credit_notes_reconciled = False

        cheque_lines = actual_lines.filtered(lambda l: l.payment_type == "cheque")
        for line in cheque_lines:
            journal = self._get_mobile_payment_journal_for_type(line.payment_type)
            method_line = self._get_payment_method_line_for_journal(
                journal, line.payment_type
            )
            deduction_commands = []
            if (
                selected_credit_note_lines
                and len(actual_lines) == len(cheque_lines)
                and not credit_notes_reconciled
            ):
                deduction_commands.extend(
                    self._prepare_mobile_credit_note_deduction_commands(
                        selected_credit_note_lines
                    )
                )
                open_command = self._prepare_mobile_open_balance_deduction_command(
                    invoice, line.amount, deduction_commands
                )
                if open_command:
                    deduction_commands.append(open_command)
            register_vals = {
                "journal_id": journal.id,
                "payment_method_line_id": method_line.id,
                "amount": line.amount,
                "payment_date": fields.Date.context_today(self),
            }
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
            payments = self._run_mobile_payment_register(register)
            if deduction_commands and selected_credit_note_lines:
                self._reconcile_mobile_credit_note_payment_lines(
                    invoice,
                    payments,
                    selected_credit_note_lines,
                    allow_invoice_fallback=True,
                )
                credit_notes_reconciled = True

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

            if selected_credit_note_lines:
                deduction_commands.extend(
                    self._prepare_mobile_credit_note_deduction_commands(
                        selected_credit_note_lines
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

            open_command = self._prepare_mobile_open_balance_deduction_command(
                invoice, main_line.amount, deduction_commands
            )
            if open_command:
                deduction_commands.append(open_command)

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
            payments = register._create_payments()
            if selected_credit_note_lines:
                self._reconcile_mobile_credit_note_payment_lines(
                    invoice, payments, selected_credit_note_lines
                )
                credit_notes_reconciled = True

        if selected_credit_note_lines and not credit_notes_reconciled:
            self._apply_mobile_credit_notes(invoice)

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
