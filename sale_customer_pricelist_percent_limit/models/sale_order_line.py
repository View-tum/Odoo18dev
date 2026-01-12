# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    
    def _get_max_customer_discount(self):
        return self.env['product.pricelist.item'].search([
                ('pricelist_id', '=', self.order_id.pricelist_id.id),
                ('compute_price', '=', 'percentage')
            ], limit=1).percent_price

    
    @api.constrains('discount', 'product_id', 'product_uom_qty', 'order_id', 'order_id.pricelist_id')
    def _check_discount_not_exceed_customer_pricelist_percent(self):
        for line in self:
            max_disc = line._get_max_customer_discount()
            if max_disc is None:
                # No percentage rule on the CUSTOMER's pricelist -> do not cap.
                continue
            line_disc = line.discount or 0.0
            if line_disc > max_disc:
                raise ValidationError(
                    _(
                        "Discount (%.2f%%) on product '%s' exceeds the allowed %.2f%% "
                        "from the applied Percentage rule on the customer's pricelist '%s'."
                    ) % (
                        line_disc,
                        line.product_id.display_name,
                        max_disc,
                        line.order_id.pricelist_id.display_name,
                    )
                )

    @api.onchange('discount')
    def _onchange_discount_limit_from_customer_pricelist(self):
        for line in self:
            max_disc = line._get_max_customer_discount()
            if max_disc is None:
                continue
            if (line.discount or 0.0) > max_disc:
                line.discount = max_disc
                return {
                    'warning': {
                        'title': _("Too high discount"),
                        'message': _(
                            "Per the customer's pricelist (percentage rule), the maximum discount is %.2f%%. "
                            "Your discount was adjusted to %.2f%%."
                        ) % (max_disc, max_disc)
                    }
                }
