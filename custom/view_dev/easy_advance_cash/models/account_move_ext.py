from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    advance_id = fields.Many2one(
        "advance.cash.log",
        string="Advance Cash Log",
        ondelete="set null",
        help="Link to the advance cash log that generated this entry",
    )
