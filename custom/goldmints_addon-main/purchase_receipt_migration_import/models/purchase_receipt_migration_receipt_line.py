from odoo import fields, models


class PurchaseReceiptMigrationReceiptLine(models.Model):
    _name = "purchase.receipt.migration.receipt.line"
    _description = "Receipt Migration Line"
    _order = "receipt_date, source_row_no, id"

    batch_id = fields.Many2one("purchase.receipt.migration.batch", required=True, ondelete="cascade")
    company_id = fields.Many2one(related="batch_id.company_id", store=True, readonly=True)
    source_row_no = fields.Integer(readonly=True)
    po_line_ref = fields.Char()
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("mapped", "Mapped"),
            ("error", "Error"),
            ("done", "Done"),
        ],
        default="draft",
        readonly=True,
    )
    error_message = fields.Text(readonly=True)

    po_number = fields.Char(required=True)
    po_source_row_no = fields.Integer()
    vendor_code = fields.Char()
    vendor_name = fields.Char()
    product_code = fields.Char(required=True)
    qty_done = fields.Float(required=True)
    receipt_date = fields.Datetime(required=True)
    lot_name = fields.Char()
    dest_location_complete_name = fields.Char(required=True)
    invoice_reference = fields.Char()
    invoice_date = fields.Date()
    manufacturing_date = fields.Datetime()
    line_note = fields.Char()

    partner_id = fields.Many2one("res.partner", readonly=True)
    product_id = fields.Many2one("product.product", readonly=True)
    purchase_order_id = fields.Many2one("purchase.order", readonly=True)
    purchase_line_id = fields.Many2one("purchase.order.line", readonly=True)
    dest_location_id = fields.Many2one("stock.location", readonly=True)
    picking_id = fields.Many2one("stock.picking", readonly=True)
    move_line_id = fields.Many2one("stock.move.line", readonly=True)
    lot_id = fields.Many2one("stock.lot", readonly=True)
    tracking = fields.Selection(related="product_id.tracking", readonly=True)
