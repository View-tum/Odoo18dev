# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    x_intl_notify = fields.Boolean(
        string="Notify Production for International Orders",
        help="If checked, an activity will be created on the Manufacturing Order "
        "when this product is sold via an International Sales Order.",
    )
