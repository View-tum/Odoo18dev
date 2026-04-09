from odoo import fields, models


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    mps_week_name = fields.Char(
        string="MPS Week",
        index=True,
        copy=False,
        help="The MPS period name when this MO was created via MPS replenishment.",
    )
