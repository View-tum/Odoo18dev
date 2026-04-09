from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _compute_mrp_production_ids(self):
        super()._compute_mrp_production_ids()
        for sale in self:
            # Optimized search using the new stored Many2one field from mrp_auto_merge
            domain = [('source_sale_order_id', '=', sale.id)]
            all_mos = self.env['mrp.production'].search(domain)

            sale.mrp_production_ids = all_mos
            sale.mrp_production_count = len(all_mos)
