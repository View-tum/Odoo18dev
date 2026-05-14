from odoo import models, fields


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    require_description = fields.Boolean(
        string="Require Description",
        default=False,
        help="If enabled, a description will be required on all picking of this type before validation."
    )
