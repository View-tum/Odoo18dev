from odoo import models, fields, api
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    total_before_discount = fields.Float('มูลค่าก่อนหักส่วนลด', digits='Product Price', compute='_compute_total_before_discount', store=True,
                                         readonly=True)
    discount_total_line = fields.Float('รวมส่วนลดรายการ', digits='Product Price', compute='_compute_discount_total_line', store=True,
                                       readonly=True)
    total_after_discount = fields.Float('มูลค่าหลังหักส่วนลดรายการ (เฉพาะสินค้าที่ไม่มีส่วนลดพิเศษ)', digits='Product Price',
                                        compute='_compute_total_after_discount', store=True, readonly=True)
    end_discount = fields.Float('สวนลดท้ายบิล', digits='Product Price', compute='_compute_end_discount', store=True, readonly=True)

    @api.depends('invoice_line_ids.total_before_discount_line')
    def _compute_total_before_discount(self):
        for order in self:
            order.total_before_discount = sum(order.invoice_line_ids.mapped('total_before_discount_line'))

    @api.depends('invoice_line_ids.discount_total')
    def _compute_discount_total_line(self):
        for order in self:
            order.discount_total_line = sum(order.invoice_line_ids.mapped('discount_total'))

    @api.depends('invoice_line_ids.price_subtotal', 'invoice_line_ids.product_id.product_tmpl_id.discount')
    def _compute_total_after_discount(self):
        for order in self:
            total = 0
            for line in order.invoice_line_ids:
                if line.product_id.product_tmpl_id.discount == False:
                    total += line.price_subtotal
            order.total_after_discount = total

    @api.depends('invoice_line_ids.price_subtotal', 'invoice_line_ids.product_id.product_tmpl_id.discount')
    def _compute_end_discount(self):
        for order in self:
            total = 0
            for line in order.invoice_line_ids:
                if line.product_id.product_tmpl_id.discount == True:
                    total += line.price_subtotal
            order.end_discount = abs(total)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    discount_per_unit = fields.Float('ส่วนลด/หน่วย', digits='Product Price', compute='_compute_discount_per_unit', store=True, readonly=True)
    discount_total = fields.Float('ส่วนลดรวม', digits='Product Price', compute='_compute_discount_total', store=True, readonly=True)
    total_before_discount_line = fields.Float('ราคาก่อนหักส่วนลด', digits='Product Price', compute='_compute_total_before_discount_line',
                                              store=True, readonly=True)

    discount_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('amount', 'Line Amount'),
        ('amount_per_unit', 'Unit Amount'),
    ], default='amount', string='Disc.Type')

    discount_value = fields.Float(
        string="Discount",
        digits='Product Price')

    @api.depends('price_unit', 'discount')
    def _compute_discount_per_unit(self):
        for line in self:
            if line.product_id.product_tmpl_id.discount == False:
                line.discount_per_unit = line.price_unit * (line.discount / 100)
            else:
                line.discount_per_unit = 0.0

    @api.depends('quantity', 'discount_per_unit')
    def _compute_discount_total(self):
        for line in self:
            if line.product_id.product_tmpl_id.discount == False:
                line.discount_total = line.discount_per_unit * line.quantity
            else:
                line.discount_total = 0.0

    @api.depends('quantity', 'price_unit')
    def _compute_total_before_discount_line(self):
        for line in self:
            if line.product_id.product_tmpl_id.discount == False:
                line.total_before_discount_line = line.quantity * line.price_unit
            else:
                line.total_before_discount_line = 0.0

    @api.onchange("discount_type")
    def _change_discount_type(self):
        for line in self:
            if (line.discount_type == 'percentage'
                    and line.product_id.product_tmpl_id.discount == False):
                line.discount = line.discount_value
            elif (line.discount_type == 'amount'
                  and line.quantity * line.price_unit != 0
                  and line.product_id.product_tmpl_id.discount == False):
                line.discount = (line.discount_value * 100) / (line.quantity * line.price_unit)
            elif (line.discount_type == 'amount_per_unit'
                  and line.quantity * line.price_unit != 0
                  and line.product_id.product_tmpl_id.discount == False):
                line.discount = (line.discount_value * line.quantity * 100) / (
                        line.quantity * line.price_unit)
            else:
                line.discount = 0
                line.discount_value = 0

    @api.onchange("discount_value")
    def _change_discount_value(self):
        for line in self:
            if (line.discount_type == 'percentage'
                    and line.product_id.product_tmpl_id.discount == False):
                line.discount = line.discount_value
            elif (line.discount_type == 'amount'
                  and line.quantity * line.price_unit != 0
                  and line.product_id.product_tmpl_id.discount == False):
                line.discount = (line.discount_value * 100) / (line.quantity * line.price_unit)
            elif (line.discount_type == 'amount_per_unit'
                  and line.quantity * line.price_unit != 0
                  and line.product_id.product_tmpl_id.discount == False):
                line.discount = (line.discount_value * line.quantity * 100) / (
                        line.quantity * line.price_unit)
            else:
                line.discount = 0
                line.discount_value = 0
