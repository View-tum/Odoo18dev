# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    tax_zero_line = fields.Boolean(string="Tax Zero Line")

    mps_bom_single_max_level = fields.Integer(
        string="Single-Level Explosion Depth",
        default=1,
        config_parameter="mrp_mps_bom_autoload.single_max_level",
        help="Maximum depth when Single Level mode is selected (0 = Unlimited).",
    )
    mps_bom_multi_max_level = fields.Integer(
        string="Multi-Level Explosion Depth",
        default=2,
        config_parameter="mrp_mps_bom_autoload.max_level",
        help="Maximum depth for Multi Level mode (0 = Unlimited).",
    )
    mps_bom_excluded_category_ids = fields.Many2many(
        related="company_id.mps_bom_excluded_category_ids",
        readonly=False,
        string="Excluded RM Categories",
        help="Products in these categories (and their child categories) "
        "will be ignored during BOM explosion.",
    )
