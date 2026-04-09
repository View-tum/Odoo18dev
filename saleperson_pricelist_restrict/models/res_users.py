from odoo import models, fields

class ResUsers(models.Model):
    _inherit = "res.users"

    sale_admin = fields.Boolean(
        string="Sale Admin User",
        help="(365 custom) If checked, this user can change the Pricelist on Sale Orders."
    )
