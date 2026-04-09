from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    report_group_id = fields.Many2one(
        "product.report.group",
        string="Report Group",
        help="Reporting group used by the product movement dashboard.",
    )
