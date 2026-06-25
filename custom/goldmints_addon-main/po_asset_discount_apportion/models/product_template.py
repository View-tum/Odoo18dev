# -*- coding: utf-8 -*-
from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_apportion_discount = fields.Boolean(
        string="Treat as Apportion Discount",
        default=False,
        help="If checked, this product will be treated as a global discount that can be apportioned into other lines on the Purchase Order."
    )
