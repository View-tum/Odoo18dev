# -*- coding: utf-8 -*-
from odoo import fields, models


class MrpWorkcenter(models.Model):
    _inherit = "mrp.workcenter"

    is_mold = fields.Boolean(
        string="Is Mold?",
        default=False,
        help="If enabled, this workcenter represents a mold (tooling).",
    )
    mold_cost_hour = fields.Float(
        string="Mold Cost / Hour",
        default=0.0,
        help="Cost of using this mold per hour of operation.",
    )
