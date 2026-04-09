from odoo import fields, models


class PurchaseReceiptMigrationPOLine(models.Model):
    _name = "purchase.receipt.migration.po.line"
    _description = "PO Migration Line"
    _order = "source_row_no, id"

    batch_id = fields.Many2one("purchase.receipt.migration.batch", required=True, ondelete="cascade")
    company_id = fields.Many2one(related="batch_id.company_id", store=True, readonly=True)
    source_row_no = fields.Integer(readonly=True)
    po_line_ref = fields.Char(readonly=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("mapped", "Mapped"),
            ("error", "Error"),
            ("created", "Created"),
        ],
        default="draft",
        readonly=True,
    )
    error_message = fields.Text(readonly=True)

    po_number = fields.Char(required=True)
    vendor_code = fields.Char(required=True)
    vendor_name = fields.Char()
    order_date = fields.Date()
    planned_date = fields.Date()
    currency_code = fields.Char(required=True)
    payment_term_code = fields.Char()
    product_code = fields.Char(required=True)
    product_name = fields.Char()
    uom_name = fields.Char()
    order_qty = fields.Float(required=True)
    unit_price = fields.Float(required=True)
    line_note = fields.Char()
    receipt_operation_name = fields.Char()

    partner_id = fields.Many2one("res.partner", readonly=True)
    product_id = fields.Many2one("product.product", readonly=True)
    uom_id = fields.Many2one("uom.uom", readonly=True)
    currency_id = fields.Many2one("res.currency", readonly=True)
    payment_term_id = fields.Many2one("account.payment.term", readonly=True)
    picking_type_id = fields.Many2one("stock.picking.type", readonly=True)
    purchase_order_id = fields.Many2one("purchase.order", readonly=True)
    purchase_line_id = fields.Many2one("purchase.order.line", readonly=True)
