from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = "sale.order"

    total_before_discount = fields.Float('มูลค่าก่อนหักส่วนลด', compute='_compute_total_before_discount', store=True, readonly=True)
    discount_total_line = fields.Float('รวมส่วนลดรายการ', compute='_compute_discount_total_line', store=True, readonly=True)
    total_after_discount = fields.Float('มูลค่าหลังหักส่วนลดรายการ (เฉพาะสินค้าที่ไม่มีส่วนลดพิเศษ)', compute='_compute_total_after_discount', store=True, readonly=True)
    end_discount = fields.Float('สวนลดท้ายบิล', compute='_compute_end_discount', store=True, readonly=True)

    @api.depends('order_line.total_before_discount_line')
    def _compute_total_before_discount(self):
        for order in self:
            order.total_before_discount = sum(order.order_line.mapped('total_before_discount_line'))

    @api.depends('order_line.discount_total')
    def _compute_discount_total_line(self):
        for order in self:
            order.discount_total_line = sum(order.order_line.mapped('discount_total'))

    @api.depends('order_line.price_subtotal', 'order_line.product_id.product_tmpl_id.discount')
    def _compute_total_after_discount(self):
        for order in self:
            total = 0
            for line in order.order_line:
                if line.product_id.product_tmpl_id.discount == False:
                    total += line.price_subtotal
            order.total_after_discount = total

    @api.depends('order_line.price_subtotal', 'order_line.product_id.product_tmpl_id.discount')
    def _compute_end_discount(self):
        for order in self:
            total = 0
            for line in order.order_line:
                if line.product_id.product_tmpl_id.discount == True:
                    total += line.price_subtotal
            order.end_discount = abs(total)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    discount_per_unit = fields.Float('ส่วนลด/หน่วย', compute='_compute_discount_per_unit', store=True, readonly=True)
    discount_total = fields.Float('ส่วนลดรวม', compute='_compute_discount_total', store=True, readonly=True)
    total_before_discount_line = fields.Float('ราคาก่อนหักส่วนลด', compute='_compute_total_before_discount_line', store=True, readonly=True)

    @api.depends('price_unit', 'discount')
    def _compute_discount_per_unit(self):
        for line in self:
            if line.product_id.product_tmpl_id.discount == False:
                line.discount_per_unit = line.price_unit * (line.discount / 100)
            else:
                line.discount_per_unit = 0.0

    @api.depends('product_uom_qty', 'discount_per_unit')
    def _compute_discount_total(self):
        for line in self:
            if line.product_id.product_tmpl_id.discount == False:
                line.discount_total = line.discount_per_unit * line.product_uom_qty
            else:
                line.discount_total = 0.0

    @api.depends('product_uom_qty', 'price_unit')
    def _compute_total_before_discount_line(self):
        for line in self:
            if line.product_id.product_tmpl_id.discount == False:
                line.total_before_discount_line = line.product_uom_qty * line.price_unit
            else:
                line.total_before_discount_line = 0.0

