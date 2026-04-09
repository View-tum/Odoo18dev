# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SalesOrderLine(models.Model):
    _inherit = 'sale.order.line'

    number = fields.Integer()


class SalesOrder(models.Model):
    _inherit = 'sale.order'

    is_number_line = fields.Boolean(compute='get_number', store=True, compute_sudo=True)

    @api.depends('order_line', 'order_line.sequence')
    def get_number(self):
        for obj in self:
            number = 1
            for line in obj.order_line.sorted(lambda x: x.sequence):
                if line.product_id:
                    line.number = number
                    number += 1
                else:
                    line.number = False  # หรือจะใช้ 0 หรือ None ตามที่ต้องการ
            obj.is_number_line = True
