# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PurchaseRequestLine(models.Model):
    _inherit = 'purchase.request.line'

    number = fields.Integer()
    sequence = fields.Integer(string='Sequence', default=10)


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    is_number_line = fields.Boolean(compute='get_number', store=True, compute_sudo=True)

    @api.depends('line_ids', 'line_ids.sequence')
    def get_number(self):
        for obj in self:
            number = 1
            for line in obj.line_ids.filtered(lambda x: x.product_id).sorted(lambda x: x.sequence):
                line.number = number
                number += 1
            obj.is_number_line = True