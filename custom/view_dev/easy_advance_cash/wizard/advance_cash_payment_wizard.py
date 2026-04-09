from odoo import api, fields, models


class AdvanceCashPaymentWizard(models.TransientModel):
    _name = "advance.cash.payment.wizard"
    _description = "Advance Cash Payment Wizard"

    advance_id = fields.Many2one(
        "advance.cash.log", string="Advance Record", required=True
    )
    transaction_type = fields.Selection(
        related="advance_id.transaction_type", string="Transaction Type"
    )
    amount = fields.Float(related="advance_id.amount", string="Amount")
    currency_id = fields.Many2one(related="advance_id.currency_id")

    # Payment Configuration
    payment_journal_id = fields.Many2one(
        "account.journal",
        string="Journal",
        required=True,
        domain="[('type', 'in', ['bank', 'cash']), ('id', '!=', parent_fund_journal_id)]",
        default=lambda self: self._default_payment_journal_id(),
    )

    parent_fund_journal_id = fields.Integer(
        compute="_compute_parent_fund_journal_id",
    )

    @api.depends("advance_id.journal_id")
    def _compute_parent_fund_journal_id(self):
        for rec in self:
            if rec.advance_id and rec.advance_id.transaction_type in [
                "payout",
                "return",
            ]:
                rec.parent_fund_journal_id = rec.advance_id.journal_id.id or 0
            else:
                rec.parent_fund_journal_id = 0

    def _find_default_payment_journal(self, company, exclude_journal=False):
        domain = [("type", "in", ["bank", "cash"]), ("company_id", "=", company.id)]
        if exclude_journal:
            domain.append(("id", "!=", exclude_journal.id))
        return self.env["account.journal"].search(domain, order="type desc, id", limit=1)

    def _default_payment_journal_id(self):
        active_id = self.env.context.get("default_advance_id") or self.env.context.get(
            "active_id"
        )
        if active_id:
            pc = self.env["advance.cash.log"].browse(active_id)
            if pc.transaction_type in ["payout", "return"]:
                return self._find_default_payment_journal(
                    pc.company_id, exclude_journal=pc.journal_id
                )
            if pc.journal_id.type in ["bank", "cash"]:
                return pc.journal_id
            return self._find_default_payment_journal(pc.company_id)
        return False

    # Payment Method & Cheque Support
    payment_type_filter = fields.Selection(
        [("outbound", "Outbound"), ("inbound", "Inbound")],
        string="Payment Type Filter",
        compute="_compute_payment_type_filter",
    )

    @api.depends("transaction_type")
    def _compute_payment_type_filter(self):
        for rec in self:
            if rec.transaction_type in ["payout", "expense"]:
                rec.payment_type_filter = "outbound"
            elif rec.transaction_type == "return":
                rec.payment_type_filter = "inbound"
            else:
                rec.payment_type_filter = False

    payment_method_line_id = fields.Many2one(
        "account.payment.method.line",
        string="Payment Method",
        domain="[('journal_id', '=', payment_journal_id), ('payment_type', '=', payment_type_filter)]",
        required=True,
    )

    @api.onchange("payment_journal_id", "payment_type_filter")
    def _onchange_payment_journal_id(self):
        self.payment_method_line_id = False
        if self.payment_journal_id and self.payment_type_filter:
            methods = self.env["account.payment.method.line"].search(
                [
                    ("journal_id", "=", self.payment_journal_id.id),
                    ("payment_type", "=", self.payment_type_filter),
                ],
                limit=1,
            )
            if methods:
                self.payment_method_line_id = methods.id

    is_cheque_method = fields.Boolean(
        string="Is Cheque Method", compute="_compute_is_cheque_method"
    )

    cheque_id = fields.Many2one(
        "cheque.book.lines",
        string="Cheque Book Line",
        domain="[('status', '=', 'draft')]",
        help="Select a cheque leaf from the book",
    )
    cheque_date = fields.Date(string="Cheque Date", default=fields.Date.context_today)

    payment_date = fields.Date(
        string="Payment Date", default=fields.Date.context_today, required=True
    )

    cheque_number_in = fields.Char(string="Cheque Number (In)")
    cheque_bank_in = fields.Many2one("res.bank", string="Issue Bank")
    cheque_branch_in = fields.Char(string="Branch")

    @api.depends("payment_method_line_id", "transaction_type")
    def _compute_is_cheque_method(self):
        for rec in self:
            is_cheque = False
            if rec.payment_method_line_id:
                if rec.transaction_type == "payout":
                    if hasattr(rec.payment_method_line_id, "is_cheque_outgoing_line"):
                        is_cheque = rec.payment_method_line_id.is_cheque_outgoing_line
                elif rec.transaction_type == "return":
                    if hasattr(rec.payment_method_line_id, "is_cheque_incoming_line"):
                        is_cheque = rec.payment_method_line_id.is_cheque_incoming_line
            rec.is_cheque_method = is_cheque

    def action_confirm_payment(self):
        """Pass data back to main model action_confirm"""
        self.ensure_one()
        payment_data = {
            "payment_journal_id": self.payment_journal_id,
            "payment_method_line_id": self.payment_method_line_id,
            "is_cheque_method": self.is_cheque_method,
            "cheque_id": self.cheque_id,
            "cheque_date": self.cheque_date,
            "cheque_number_in": self.cheque_number_in,
            "cheque_bank_in": self.cheque_bank_in,
            "cheque_branch_in": self.cheque_branch_in,
            "payment_date": self.payment_date,
        }
        # Call main model confirm with data
        if self.transaction_type == "expense":
            self.advance_id.action_pay_reimbursement(payment_data=payment_data)
        else:
            self.advance_id.action_confirm(payment_data=payment_data)
        return {"type": "ir.actions.act_window_close"}
