from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_scrap_cost = fields.Boolean(
        string="Is Scrap Cost Product", help="Used to absorb scrap cost via landed cost"
    )
