from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    petty_cash_id = fields.Many2one(
        "petty.cash.log",
        string="Petty Cash Log",
        readonly=True,
        help="Link to the Petty Cash Log that initiated this payment (for replenishment).",
    )

    def action_post(self):
        """Override to update linked Petty Cash Log after posting."""
        res = super().action_post()

        for payment in self:
            if payment.petty_cash_id and payment.petty_cash_id.state == "approved":
                # Update the Petty Cash Log with the move_id and mark as posted
                payment.petty_cash_id.write(
                    {
                        "state": "posted",
                        "move_id": payment.move_id.id,
                    }
                )
                payment.petty_cash_id.message_post(
                    body=f"✅ Payment {payment.name} posted. Journal Entry: {payment.move_id.name}"
                )

        return res
