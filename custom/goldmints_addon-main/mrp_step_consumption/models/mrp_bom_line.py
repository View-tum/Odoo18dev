# -*- coding: utf-8 -*-
from odoo import fields, models


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    step_coverage_qty = fields.Float(
        string="Step Coverage (Units)",
        digits='Product Unit of Measure',
        help="The quantity of Finished Goods that one 'Step Batch' can cover.\n"
             "E.g., if 1 Bag covers 100,000 units, enter 100,000."
    )

    step_batch_qty = fields.Float(
        string="Step Batch Size",
        digits='Product Unit of Measure',
        help="The quantity of Component to consume per step.\n"
             "E.g., if you must open a full bag of 750g, enter 750."
    )
