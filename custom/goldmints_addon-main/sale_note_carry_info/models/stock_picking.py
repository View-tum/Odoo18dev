from odoo import api, fields, models

class StockPicking(models.Model):
    _inherit = "stock.picking"

    sale_note = fields.Text(
        string="Note",
        compute="_compute_note",
        store=True,
        readonly=False,
        help="(365 custom) Note carried over from the related Sales Order."
    )
    
    sequence_code = fields.Char(
        related='picking_type_id.sequence_code',
        help="(365 custom) Sequence code of the operation type (technical field)."
    )

    @api.depends("move_ids", "move_ids.sale_line_id", "move_ids.sale_line_id.order_id", "move_ids.sale_line_id.order_id.sale_note")
    def _compute_note(self):
        for picking in self:
            sale_orders = picking.move_ids.mapped("sale_line_id.order_id")
            picking.sale_note = sale_orders[:1].sale_note if sale_orders else False