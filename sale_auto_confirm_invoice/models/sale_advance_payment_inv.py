import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    mobile_payment_method = fields.Selection(
        selection=[("cash", "Cash"), ("cheque", "Cheque"), ("bank_transfer", "Bank Transfer")],
        string="Payment Method",
        default="cash",
    )
    is_mobile_warehouse = fields.Boolean(compute="_compute_is_mobile_warehouse", store=True)
    mobile_account_missing = fields.Boolean(compute="_compute_mobile_account_warning", store=True)
    mobile_account_warning = fields.Html(compute="_compute_mobile_account_warning", store=True)

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
            if wizard.is_mobile_warehouse and wizard.advance_payment_method != "delivered":
                wizard.advance_payment_method = "delivered"

    @api.depends("sale_order_ids.company_id", "mobile_payment_method", "is_mobile_warehouse")
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
            label = _("Cash Account") if wizard.mobile_payment_method == "cash" else _("Cheque/Bank Account")
            account = (
                company.cash_account_id
                if wizard.mobile_payment_method == "cash"
                else company.cheque_and_bank_account_id
            )
            if not account:
                wizard.mobile_account_missing = True
                wizard.mobile_account_warning = _(
                    "%s is not set. Go to Sales → Settings → Mobile Warehouse Invoicing to configure it."
                ) % label

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
            self._ensure_mobile_account_configured()
            invoices = self._create_invoices(self.sale_order_ids)
        else:
            invoices = self._create_invoices(self.sale_order_ids)
        return self.sale_order_ids.action_view_invoice(invoices=invoices)

    def action_create_invoice_paid(self):
        self._check_amount_is_positive()
        account = (
            self._ensure_mobile_account_configured(require_liquidity=True)
            if self.is_mobile_warehouse
            else None
        )
        invoices = self._create_invoices(self.sale_order_ids)
        if invoices and self.is_mobile_warehouse:
            self._log_invoice_partner_lines(invoices, label="before payment")
        if invoices and self.is_mobile_warehouse:
            self._register_mobile_payments(invoices, account)
        return self.sale_order_ids.action_view_invoice(invoices=invoices)

    def action_create_invoice_mobile(self):
        self.ensure_one()
        if not self.is_mobile_warehouse:
            return self.create_invoices()
        if self.mobile_payment_method == "cheque":
            return self.action_create_invoice_posted()
        return self.action_create_invoice_paid()

    def _create_invoices(self, sale_orders):
        self._ensure_downpayment_account_configured()
        invoices = super()._create_invoices(sale_orders)
        if self.is_mobile_warehouse and invoices:
            self._log_invoice_partner_lines(invoices, label="after creation (no override)")
        draft_moves = invoices.filtered(lambda m: m.state == "draft")
        if draft_moves:
            try:
                # Auto-confirm invoices generated by the wizard (down payments or regular)
                draft_moves.action_post()
            except UserError:
                # Leave drafts as-is if posting fails (e.g., missing accounts/journal)
                pass
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

    def _get_mobile_payment_account(self):
        self.ensure_one()
        company = self._get_target_company()
        if self.mobile_payment_method == "cash":
            account = company.cash_account_id
            missing = _("Cash Account")
        else:
            account = company.cheque_and_bank_account_id
            missing = _("Cheque/Bank Account")
        if not account:
            raise UserError(
                _(
                    "Please configure the %s in Sales → Settings → Mobile Warehouse Invoicing to invoice Mobile Warehouse orders."
                )
                % missing
            )
        _logger.info(
            "Mobile payment method %s -> account %s (company %s)",
            self.mobile_payment_method,
            account.display_name,
            company.display_name,
        )
        return account

    def _ensure_mobile_account_configured(self, require_receivable=False, require_liquidity=False):
        self.ensure_one()
        account = self._get_mobile_payment_account()
        if self.mobile_account_missing:
            # Show same message as the warning box to block progression.
            raise UserError(self.mobile_account_warning or _("Please configure the required account for this payment method."))
        if require_liquidity and account.account_type != "asset_cash":
            label = _("Cash Account") if self.mobile_payment_method == "cash" else _("Cheque/Bank Account")
            raise UserError(
                _(
                    "%s must be a liquidity (cash/bank) account for Create Invoice Paid."
                )
                % label
            )
        return account

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

    def _register_mobile_payments(self, invoices, account):
        if not account:
            return
        invoices_to_pay = invoices.filtered(
            lambda move: move.state != "cancel" and move.is_invoice(True)
        )
        draft_moves = invoices_to_pay.filtered(lambda move: move.state == "draft")
        if draft_moves:
            draft_moves.action_post()
        posted_invoices = invoices_to_pay.filtered(lambda move: move.state == "posted")
        if not posted_invoices:
            return
        companies = posted_invoices.company_id
        if len(companies) > 1:
            raise UserError(
                _(
                    "Please invoice Mobile Warehouse orders for one company at a time when using the auto-payment button."
                )
            )
        if companies[:1] not in account.company_ids:
            raise UserError(
                _(
                    "The selected account '%s' does not belong to company '%s'. Please pick a matching account."
                )
                % (account.display_name, companies[:1].display_name)
            )
        journal = self._get_payment_journal_for_account(account, companies[:1])
        method_line = self._get_payment_method_line_for_account(journal, account)
        register = (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=posted_invoices.ids)
            .create({"journal_id": journal.id, "payment_method_line_id": method_line.id})
        )
        payments = register.action_create_payments()
        if isinstance(payments, dict):
            payments = self.env["account.payment"].browse(payments.get("res_id", []))
        to_post = payments.filtered(lambda p: p.state != "posted")
        if to_post:
            to_post.action_post()

    def _log_invoice_partner_lines(self, invoices, label):
        for inv in invoices:
            partner_lines = inv.line_ids.filtered(
                lambda l: l.account_id.account_type in ("asset_receivable", "liability_payable")
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
            lambda line: line.account_id.account_type in ("asset_receivable", "liability_payable")
        )
        partner_lines_filtered = partner_lines.filtered(lambda l: not l.date_maturity)
        if partner_lines_filtered:
            partner_lines_filtered.write({"date_maturity": maturity})
        non_partner = move.line_ids.filtered(
            lambda l: l.account_id.account_type not in ("asset_receivable", "liability_payable")
            and l.date_maturity
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

    def _get_payment_journal_for_account(self, account, company):
        journal = self.env["account.journal"].search(
            [
                ("company_id", "=", company.id),
                ("default_account_id", "=", account.id),
                ("type", "in", ("cash", "bank", "credit")),
            ],
            limit=1,
        )
        if not journal:
            raise UserError(
                _(
                    "No bank or cash journal using account '%s' was found for company '%s'. "
                    "Please link a journal to this account first."
                )
                % (account.display_name, company.display_name)
            )
        _logger.info(
            "Mobile payment journal selected: %s (account %s)",
            journal.display_name,
            account.display_name,
        )
        return journal

    def _get_payment_method_line_for_account(self, journal, account):
        """Pick a payment method line whose payment account matches our target account, fallback to first inbound."""
        self.ensure_one()
        domain = [
            ("journal_id", "=", journal.id),
            ("payment_type", "=", "inbound"),
            ("payment_account_id", "=", account.id),
        ]
        method_line = self.env["account.payment.method.line"].search(domain, limit=1)
        if not method_line:
            method_line = self.env["account.payment.method.line"].search(
                [("journal_id", "=", journal.id), ("payment_type", "=", "inbound")],
                limit=1,
            )
        if not method_line:
            raise UserError(
                _(
                    "No inbound payment method line found for journal '%s'. Please configure one (payment account %s)."
                )
                % (journal.display_name, account.display_name)
            )
        _logger.info(
            "Mobile payment method line selected: %s (account %s)",
            method_line.display_name,
            method_line.payment_account_id.display_name,
        )
        return method_line
