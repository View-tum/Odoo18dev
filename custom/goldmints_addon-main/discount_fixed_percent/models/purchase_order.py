# -*- coding: utf-8 -*-

from odoo import api, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.onchange("purchase_manual_currency_rate_active", "purchase_manual_currency_rate")
    def _onchange_manual_rate_update_line_discounts(self):
        for order in self:
            for line in order.order_line:
                if line.percent_discount:
                    line.fixed_discount = 0.0
                elif line.fixed_discount and line.discount:
                    total_price = line.price_unit * line.product_qty
                    if total_price:
                        line.fixed_discount = (total_price * line.discount) / 100

