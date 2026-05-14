from odoo import api, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model_create_multi
    def create(self, vals_list):
        products = super().create(vals_list)
        if not self.env.context.get("skip_sm_pharma_policy"):
            products.product_tmpl_id._apply_sm_pharma_policy()
        return products

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get("skip_sm_pharma_policy") and "default_code" in vals:
            self.product_tmpl_id._apply_sm_pharma_policy()
        return res
