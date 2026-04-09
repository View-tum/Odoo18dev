from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = "product.template"

    manufacturing_type = fields.Selection(
        [
            ("plastic", "Plastic"),
            ("pharma", "Pharma"),
            ("packaging", "Packaging"),
        ],
        string="Manufacturing Type",
        help="Indicates whether this product is manufactured in the Plastic, Pharma, or Packaging factory.",
    )

    x_important_notify = fields.Boolean(
        string="Notify Production Important",
        help="If checked, a popup alert will be sent to the selected users "
        "when this product is part of an International Sales Order.",
    )

