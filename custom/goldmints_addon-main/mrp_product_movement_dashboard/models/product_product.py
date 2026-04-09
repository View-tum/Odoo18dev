from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    report_group_id = fields.Many2one(
        "product.report.group",
        string="Report Group",
        related="product_tmpl_id.report_group_id",
        store=True,
        readonly=False,
    )
