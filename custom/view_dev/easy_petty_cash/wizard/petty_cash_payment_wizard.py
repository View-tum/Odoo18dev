from odoo import api, fields, models


class PettyCashPaymentWizard(models.TransientModel):
    _name = "petty.cash.payment.wizard"
    _description = "Petty Cash Payment Wizard"

    petty_cash_id = fields.Many2one(
        "petty.cash.log", string="Petty Cash Record", required=True
    )
    transaction_type = fields.Selection(
        related="petty_cash_id.transaction_type", string="Transaction Type"
    )
    amount = fields.Float(related="petty_cash_id.amount", string="Amount")
    currency_id = fields.Many2one(related="petty_cash_id.currency_id")

    # Payment Configuration (Source/Target)
    payment_journal_id = fields.Many2one(
        "account.journal",
        string="Journal",
        required=True,
        domain="[('type', 'in', ['bank', 'cash']), ('id', '!=', parent_fund_journal_id)]",
        help="Replenish: Select Source Bank. Deposit: Select Target Bank.",
        default=lambda self: self._default_payment_journal_id(),
    )

    parent_fund_journal_id = fields.Integer(
        compute="_compute_parent_fund_journal_id",
        help="Technical field: the fund journal ID to exclude from domain",
    )

    @api.depends("petty_cash_id.journal_id")
    def _compute_parent_fund_journal_id(self):
        for rec in self:
            # For Replenish (in) and Deposit (deposit), we interact with Bank,
            # so we must exclude the Petty Cash journal itself to avoid self-transfer.
            if rec.petty_cash_id and rec.petty_cash_id.transaction_type in [
                "in",
                "deposit",
            ]:
                rec.parent_fund_journal_id = rec.petty_cash_id.journal_id.id or 0
            else:
                rec.parent_fund_journal_id = (
                    0  # No exclusion for Out transactions (Expenses)
                )

    def _default_payment_journal_id(self):
        active_id = self.env.context.get(
            "default_petty_cash_id"
        ) or self.env.context.get("active_id")
        if active_id:
            pc = self.env["petty.cash.log"].browse(active_id)
            # If Expense (out), default to the Petty Cash Journal itself
            if pc.transaction_type == "out":
                return pc.journal_id
            # If Replenish (in) OR Deposit (deposit), find a DIFFERENT Bank journal
            else:
                return self.env["account.journal"].search(
                    [
                        ("type", "=", "bank"),  # Prefer Bank over Cash
                        ("company_id", "=", pc.company_id.id),
                        ("id", "!=", pc.journal_id.id),  # Exclude the fund journal
                    ],
                    limit=1,
                )
        return False

    # Payment Method & Cheque Support
    payment_method_line_id = fields.Many2one(
        "account.payment.method.line",
        string="Payment Method",
        domain="[('journal_id', '=', payment_journal_id), ('payment_type', '=', 'outbound')]",
        required=True,
    )

    @api.onchange("payment_journal_id")
    def _onchange_payment_journal_id(self):
        if self.payment_journal_id:
            # Auto-select the first outbound payment method (usually Manual)
            methods = self.env["account.payment.method.line"].search(
                [
                    ("journal_id", "=", self.payment_journal_id.id),
                    ("payment_type", "=", "outbound"),
                ],
                limit=1,
            )
            if methods:
                self.payment_method_line_id = methods.id

    is_cheque_method = fields.Boolean(
        string="Is Cheque Method", compute="_compute_is_cheque_method"
    )

    # Cheque Fields (Outbound - Payout)
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

    @api.depends("payment_method_line_id")
    def _compute_is_cheque_method(self):
        for rec in self:
            is_cheque = False
            if rec.payment_method_line_id:
                if hasattr(rec.payment_method_line_id, "is_cheque_outgoing_line"):
                    is_cheque = rec.payment_method_line_id.is_cheque_outgoing_line
            rec.is_cheque_method = is_cheque

    def action_confirm_payment(self):
        """Pass data back to main model action_confirm"""
        self.ensure_one()

        # Validate: For replenishment/deposit, journal must be different
        if self.petty_cash_id.transaction_type in ["in", "deposit"]:
            if self.payment_journal_id.id == self.petty_cash_id.journal_id.id:
                from odoo.exceptions import UserError

                raise UserError(
                    "สำหรับการเติมเงิน (Replenish) หรือฝากเงินคืน (Deposit) กรุณาเลือก Journal ที่แตกต่างจาก Petty Cash Fund\n\n"
                    "Please select a Journal that is DIFFERENT from the Petty Cash Fund journal."
                )

        payment_data = {
            "payment_journal_id": self.payment_journal_id,
            "payment_method_line_id": self.payment_method_line_id,
            "is_cheque_method": self.is_cheque_method,
            "cheque_id": self.cheque_id,
            "cheque_date": self.cheque_date,
            "payment_date": self.payment_date,
        }
        # Call main model confirm with data
        self.petty_cash_id.action_confirm(payment_data=payment_data)
        return {"type": "ir.actions.act_window_close"}
