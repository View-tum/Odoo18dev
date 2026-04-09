# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AmountToBilling(models.Model):
    _inherit = 'account.billing'

    amount_total = fields.Float(string="Amount Total", compute='_compute_amount_total', store=True)

    @api.depends('billing_line_ids.amount_total')  # เปลี่ยนจาก 'total' เป็น 'amount_total'
    def _compute_amount_total(self):
        for billing in self:
            amount_total = sum(billing.billing_line_ids.mapped('amount_total'))
            billing.amount_total = amount_total


