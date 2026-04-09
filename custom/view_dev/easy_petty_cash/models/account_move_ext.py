from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    petty_cash_id = fields.Many2one(
        "petty.cash.log",
        string="Petty Cash Log",
        ondelete="set null",
        help="Link to the petty cash log that generated this entry",
    )

    def action_post(self):
        """Override action_post to update the petty cash log state if linked."""
        res = super(AccountMove, self).action_post()
        for move in self:
            if move.petty_cash_id and move.petty_cash_id.state == "approved":
                # Update the log state to posted and link it
                move.petty_cash_id.write(
                    {
                        "state": "posted",
                        "move_id": move.id,
                    }
                )
                # Add a message to the log
                move.petty_cash_id.message_post(
                    body=f"Journal Entry posted: {move.name}"
                )
        return res
