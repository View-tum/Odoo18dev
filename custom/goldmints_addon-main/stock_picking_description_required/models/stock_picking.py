from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    picking_description = fields.Char(
        string="Description",
        copy=False,
        help="Mandatory description if required by the operation type."
    )

    require_description = fields.Boolean(
        related="picking_type_id.require_description",
        readonly=True
    )

    # Removed button_validate override as per user request: Description is not mandatory.

