# -*- coding: utf-8 -*-
from odoo import fields, models


class MrpRoutingWorkcenter(models.Model):
    _inherit = "mrp.routing.workcenter"

    # REDUNDANT: These were used for BoM-based legacy mapping.
    # Compatibility is now managed via the Matrix on the Workcenter.
    # Keeping is_parallel_active for UI logic if needed by core/other modules.

    is_parallel_active = fields.Boolean(
        string="Is Parallel Active",
        compute="_compute_is_parallel_active",
        help="Technical field to check if parallel mode is active safely.",
    )

    # [TEMPORARY] Restore to fix ParseError in mrp_parallel_console
    mold_ids = fields.Many2many(
        "mrp.workcenter",
        "mrp_routing_workcenter_mold_rel",
        "routing_wc_id",
        "mold_id",
        string="Molds (Legacy)",
        domain=[("is_mold", "=", True)],
    )

    def _compute_is_parallel_active(self):
        for record in self:
            record.is_parallel_active = getattr(record, "parallel_mode", "single") == "parallel"
