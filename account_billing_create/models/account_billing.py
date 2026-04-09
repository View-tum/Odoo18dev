from odoo import models, fields, api


class AccountBilling(models.Model):
    _inherit = "account.billing"
    _description = "Account Billing (with Start Date Filter)"

    start_date = fields.Date(
        string="Start Date",
        readonly=True,
        help="(365 custom) Start date to filter the moves to be billed.",
    )
    billing_mode = fields.Selection(
        selection=[
            ("out_invoice", "Customer Invoice (ลูกหนี้)"),
            ("in_invoice", "Vendor Bill (เจ้าหนี้)"),
            ("netting", "Netting (หักกลบหนี้)"),
        ],
        string="Billing Mode",
        default="out_invoice",
        help="(365 custom) Select the type of billing to create.",
    )

    def compute_lines(self):
        super(AccountBilling, self).compute_lines()

        for billing in self.filtered(lambda b: b.billing_mode == "netting"):
            negative_types = ["in_invoice", "out_refund"]
            negative_lines = billing.billing_line_ids.filtered(
                lambda l: l.move_id.move_type in negative_types
            )
            for line in negative_lines:
                line.amount_total = -abs(line.amount_total)
                line.amount_residual = -abs(line.amount_residual)

            positive_types = ["out_invoice", "in_refund"]
            positive_lines = billing.billing_line_ids.filtered(
                lambda l: l.move_id.move_type in positive_types
            )
            for line in positive_lines:
                line.amount_total = abs(line.amount_total)
                line.amount_residual = abs(line.amount_residual)

    def _get_payable_moves(self, moves):
        """Keep only moves that still have receivable/payable residuals."""
        valid_accounts = self.env["account.payment"]._get_valid_payment_account_types()

        def line_has_residual(line):
            if line.currency_id:
                return not line.currency_id.is_zero(line.amount_residual_currency)
            return not line.company_currency_id.is_zero(line.amount_residual)

        payable_moves = self.env["account.move"]
        for move in moves:
            lines = move.line_ids.filtered(lambda l: l.account_type in valid_accounts)
            if any(line_has_residual(line) for line in lines):
                payable_moves |= move
        return payable_moves

    def _create_payments_for_moves(self, moves):
        """Create payments (in payment) for the given moves using the payment wizard logic."""
        payable_moves = self._get_payable_moves(moves)
        if not payable_moves:
            return

        ctx = {
            "active_model": "account.move",
            "active_ids": payable_moves.ids,
            "dont_redirect_to_payments": True,
        }
        wizard = self.env["account.payment.register"].with_context(ctx).create({})
        wizard.action_create_payments()

    def action_register_payment(self):
        """
        Netting: open one wizard, then create payments for all directions
        (customer and vendor) using that flow. Non-netting keeps the default.
        """
        self.ensure_one()
        if self.billing_mode != "netting":
            return super().action_register_payment()

        ar_moves = self._get_payable_moves(
            self.billing_line_ids.move_id.filtered(
                lambda m: m.move_type in ("out_invoice", "out_refund")
            )
        )
        ap_moves = self._get_payable_moves(
            self.billing_line_ids.move_id.filtered(
                lambda m: m.move_type in ("in_invoice", "in_refund")
            )
        )

        if not (ar_moves or ap_moves):
            return True

        target_moves = ar_moves or ap_moves
        follow_moves = ap_moves if ar_moves else self.env["account.move"]

        action = target_moves.action_register_payment()
        if action and action.get("type") == "ir.actions.act_window":
            ctx = dict(action.get("context", {}))
            ctx.setdefault("dont_redirect_to_payments", True)
            if follow_moves:
                ctx["netting_follow_up_move_ids"] = follow_moves.ids
            action["context"] = ctx
        return action or True

    def _get_moves(self, date=False, types=False):
        if not self.start_date:
            return super(AccountBilling, self)._get_moves(date=date, types=types)

        query = """
            SELECT DISTINCT line.move_id
            FROM account_billing_line line
            JOIN account_billing bill ON line.billing_id = bill.id
            WHERE bill.state = 'billed'
        """
        self.env.cr.execute(query)
        billed_move_ids = [row[0] for row in self.env.cr.fetchall()]

        target_types = []

        if self.billing_mode == "netting":
            target_types = ["out_invoice", "out_refund", "in_invoice", "in_refund"]
        elif self.billing_mode == "in_invoice":
            target_types = ["in_invoice", "in_refund"]
        else:
            target_types = ["out_invoice", "out_refund"]
        domain = [
            ("partner_id", "=", self.partner_id.id),
            ("state", "=", "posted"),
            ("currency_id", "=", self.currency_id.id),
            ("invoice_date", "<=", self.threshold_date),
            ("move_type", "in", target_types),
            ("payment_state", "in", ["not_paid", "partial"]),
            ("id", "not in", billed_move_ids),
        ]

        return self.env["account.move"].search(domain)
