from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class VendorBillingNoteLine(models.Model):
    _name = "vendor.billing.note.line"
    _description = "Vendor Billing Note Line"

    billing_note_id = fields.Many2one(
        "vendor.billing.note",
        string="Billing Note Reference",
        required=True,
        ondelete="cascade",
        index=True,
        copy=False,
    )
    purchase_line_id = fields.Many2one(
        "purchase.order.line",
        string="Purchase Order Line",
        required=True,
        ondelete="restrict",
    )
    purchase_order_id = fields.Many2one(
        "purchase.order",
        related="purchase_line_id.order_id",
        string="Purchase Order",
        store=True,
        readonly=True,
    )
    picking_id = fields.Many2one(
        "stock.picking", 
        string="Receipt", 
        ondelete="restrict"
    )
    service_acceptance_id = fields.Many2one(
        "service.acceptance", 
        string="Service Acceptance", 
        ondelete="restrict"
    )

    product_id = fields.Many2one(
        "product.product",
        related="purchase_line_id.product_id",
        string="Product",
        readonly=True,
    )
    name = fields.Text(
        string="Description", 
        required=True)

    quantity = fields.Float(
        string="Quantity", 
        required=True, 
        digits="Product Unit of Measure"
    )
    price_unit = fields.Float(
        string="Unit Price", 
        required=True, 
        digits="Product Price"
    )
    tax_ids = fields.Many2many(
        "account.tax", 
        string="Taxes")

    currency_id = fields.Many2one(
        "res.currency",
        related="billing_note_id.currency_id",
        depends=["billing_note_id.currency_id"],
        store=True,
        string="Currency",
    )
    price_subtotal = fields.Monetary(
        compute="_compute_subtotal", 
        string="Subtotal", 
        currency_field="currency_id",
        store=True
    )

    @api.depends("quantity", "price_unit", "tax_ids")
    def _compute_subtotal(self):
        for line in self:
            taxes = line.tax_ids.compute_all(
                line.price_unit,
                line.currency_id,
                line.quantity,
                product=line.product_id,
                partner=line.billing_note_id.partner_id,
            )
            line.price_subtotal = taxes["total_excluded"]
            
    @api.constrains('quantity')
    def _check_quantity_over_received(self):
        for line in self:
            if line.purchase_line_id:
                # 1. หาผลรวมของจำนวนที่วางบิลไปแล้วทั้งหมดใน PO Line นี้ (ที่ไม่ถูก Cancel)
                # รวมรายการปัจจุบันที่กำลังบันทึกอยู่ด้วย
                valid_lines = line.purchase_line_id.billing_note_line_ids.filtered(
                    lambda l: l.billing_note_id.state != 'cancel'
                )
                total_billed = sum(valid_lines.mapped('quantity'))
                total_received = line.purchase_line_id.qty_received

                # 2. ใช้ float_compare ป้องกันปัญหาการเปรียบเทียบจุดทศนิยมของ Python
                # ถ้า total_billed > total_received จะทำการแจ้ง Error
                if float_compare(total_billed, total_received, precision_digits=2) > 0:
                    raise ValidationError(
                        _("ไม่อนุญาตให้วางบิลเกินจำนวนที่รับจริง!\n"
                          "สินค้า: %s\n"
                          "รับจริง: %.2f\n"
                          "พยายามวางบิลรวม: %.2f") % (
                            line.product_id.display_name, 
                            total_received, 
                            total_billed
                        )
                    )
