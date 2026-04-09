from odoo import fields, models

class StockMove(models.Model):
    _inherit = "stock.move"

    sale_note = fields.Text(
        string="Note",
        related="sale_line_id.order_id.sale_note",
        store=True,
        readonly=True,
        help="(365 custom) Note carried over from the related Sales Order (technical field)."
    )