from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = "product.template"

    manufacturing_type = fields.Selection(
        [
            ("plastic", "Plastic"),
            ("pharma", "Pharma"),
        ],
        string="Manufacturing Type",
        help="Indicates whether this product is manufactured in the Plastic or Pharma factory.",
    )
