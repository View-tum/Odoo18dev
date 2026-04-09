from odoo import fields, models

class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    allow_edit_effective_date = fields.Boolean(
        string="Allow Edit Effective Date",
        help="If checked, users can edit the effective date on transfers of this type."
    )
    
    default_effective_date_offset = fields.Integer(
        string="Effective Date Offset (Days)",
        default=0,
        help="Number of days to add or subtract from today for the default effective date. E.g., -1 for Yesterday, 1 for Tomorrow."
    )
