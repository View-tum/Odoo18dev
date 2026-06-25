from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    van_sale_location_id = fields.Many2one(
        "stock.location",
        string="Van Sales Source Location",
        domain="[('usage', '=', 'internal')]",
        help="Internal stock location used as the delivery source for this van sales user.",
    )
