from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    currency_rate_display = fields.Char(
        string="Rate Display",
        compute="_compute_currency_rate_display",
        store=False,
    )
    show_currency_rate = fields.Boolean(
        compute="_compute_currency_rate_display",
        store=False,
    )

    @api.depends('currency_id', 'company_id', 'date_order')
    def _compute_currency_rate_display(self):
        for order in self:
            is_foreign = order.currency_id and order.company_id and order.currency_id != order.company_id.currency_id
            order.show_currency_rate = is_foreign
            if is_foreign:
                rate = order.currency_id.with_context(date=order.date_order).rate
                if rate:
                    order.currency_rate_display = f"1 {order.company_id.currency_id.name} = {rate:.4f}"
                else:
                    order.currency_rate_display = False
            else:
                order.currency_rate_display = False
