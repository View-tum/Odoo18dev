from odoo import fields, models

class StockMove(models.Model):
    _inherit = "stock.move"

    purchase_note = fields.Text(
        string="Purchase Note",
        related="purchase_line_id.order_id.purchase_note",
        store=True,
        readonly=True,
        help="(365 custom) Note from the related Purchase Order (readonly)."
    )
