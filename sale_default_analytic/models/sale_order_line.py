from odoo import api, models

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('product_id', 'order_id.date_order', 'order_id.partner_id')
    def _compute_analytic_distribution(self):
        """
        Override to apply default analytic account from settings if no other distribution is found.
        """
        super()._compute_analytic_distribution()
        for line in self:
            # Only apply if no distribution is set by standard logic
            if not line.analytic_distribution and line.company_id.sale_default_analytic_account_id:
                line.analytic_distribution = {
                    str(line.company_id.sale_default_analytic_account_id.id): 100
                }
