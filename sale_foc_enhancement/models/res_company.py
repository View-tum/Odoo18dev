from odoo import models, fields

class ResCompany(models.Model):
    _inherit = "res.company"

    
    foc_cogs_adjust_account_id = fields.Many2one(
        "account.account",
        string="FOC COGS Adjustment Account",
        domain=[("deprecated", "=", False)],
        help="Offset account (typically COGS adjustment) for the valuation of Free of Charge (FOC) items.",
    )
