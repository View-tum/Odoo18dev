# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    mps_bom_excluded_category_ids = fields.Many2many(
        "product.category",
        "company_mps_bom_excluded_category_rel",
        "company_id",
        "category_id",
        string="MPS Excluded Categories",
        help="Products in these categories (including child categories) "
        "are not auto-added to MPS.",
    )
