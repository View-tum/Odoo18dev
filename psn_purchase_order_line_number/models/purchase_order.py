# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    number = fields.Integer(string="Number")


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    is_number_line = fields.Boolean(compute='get_number', store=True, compute_sudo=True)

    @api.depends('order_line', 'order_line.sequence', 'order_line.product_id')
    def get_number(self):
        for obj in self:
            number = 1
            for line in obj.order_line.sorted(lambda x: x.sequence):
                if line.product_id:
                    line.number = number
                    number += 1
                else:
                    line.number = False  # หรือใช้ None หรือ 0 ตามต้องการ
            obj.is_number_line = True
