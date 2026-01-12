from odoo import models


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    def _moves_with_residuals(self, moves):
        """Keep moves that still have receivable/payable residuals."""
        valid_accounts = self.env["account.payment"]._get_valid_payment_account_types()

        def has_residual(move):
            for line in move.line_ids.filtered(lambda l: l.account_type in valid_accounts):
                if line.currency_id:
                    if not line.currency_id.is_zero(line.amount_residual_currency):
                        return True
                elif not line.company_currency_id.is_zero(line.amount_residual):
                    return True
            return False

        return moves.filtered(has_residual)

    def action_create_payments(self):
        # Run the normal flow first (opens/creates payments for the first batch).
        res = super().action_create_payments()

        # Netting: if there is an opposite direction, open a second wizard right after
        # the first completes (so the user still sees a wizard, same as default).
        if (
            self._context.get("netting_follow_up_move_ids")
            and not self._context.get("netting_follow_up_processed")
        ):
            follow_moves = self._moves_with_residuals(
                self.env["account.move"].browse(
                    self._context.get("netting_follow_up_move_ids")
                )
            )
            if follow_moves:
                action = follow_moves.action_register_payment()
                if action and action.get("type") == "ir.actions.act_window":
                    ctx = dict(action.get("context", {}))
                    ctx.setdefault("dont_redirect_to_payments", True)
                    ctx["netting_follow_up_processed"] = True
                    action["context"] = ctx
                    return action

        return res
