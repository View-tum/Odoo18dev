# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MrpRoutingWorkcenter(models.Model):
    _inherit = "mrp.routing.workcenter"

    parallel_mode = fields.Selection(
        [
            ("single", "Single Workcenter"),
            ("parallel", "Parallel Workcenters"),
        ],
        string="Parallel Mode",
        default="single",
        help="Define whether this operation runs on a single workcenter or "
             "on multiple workcenters in parallel.",
    )
    parallel_workcenter_ids = fields.Many2many(
        "mrp.workcenter",
        "mrp_routing_wc_parallel_rel",
        "routing_wc_id",
        "workcenter_id",
        string="Parallel Workcenters",
        help="Additional workcenters that will run this opFeration in parallel "
             "and share the manufacturing quantity.",
    )
