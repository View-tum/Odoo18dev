# -*- coding: utf-8 -*-
from odoo import fields, models, api


class MrpRoutingWorkcenter(models.Model):
    _inherit = "mrp.routing.workcenter"

    mold_ids = fields.Many2many(
        "mrp.workcenter",
        string="Molds",
        domain=[("is_mold", "=", True)],
        help="Molds used together with this operation.",
    )

    mold_line_ids = fields.One2many(
        "mrp.routing.workcenter.mold.line",
        "routing_id",
        string="Mold Mapping",
        help="Specific mold assignment per workcenter (for parallel operations).",
    )

    is_parallel_active = fields.Boolean(
        string="Is Parallel Active",
        compute="_compute_is_parallel_active",
        help="Technical field to check if parallel mode is active safely.",
    )

    def _compute_is_parallel_active(self):
        for record in self:
            # Safely check if parallel_mode exists and is set to 'parallel'
            record.is_parallel_active = getattr(record, "parallel_mode", "single") == "parallel"

    @api.onchange("parallel_workcenter_ids", "parallel_mode")
    def _onchange_parallel_workcenters(self):
        # Safely check if parallel mode is active
        is_parallel = getattr(self, "parallel_mode", "single") == "parallel"
        if not is_parallel:
            return

        # Get selected parallel workcenters
        parallel_wcs = getattr(self, "parallel_workcenter_ids", self.env["mrp.workcenter"])

        # Get currently mapped workcenters
        existing_wcs = self.mold_line_ids.mapped("workcenter_id")

        # Find workcenters that are in parallel_wcs but not in mold_line_ids
        wcs_to_add = parallel_wcs - existing_wcs

        lines = []
        for wc in wcs_to_add:
            lines.append((0, 0, {
                "workcenter_id": wc.id,
            }))

        if lines:
            self.mold_line_ids = lines

    def write(self, vals):
        res = super(MrpRoutingWorkcenter, self).write(vals)
        for record in self:
            # Auto-populate mold mapping if parallel mode is active
            if record.is_parallel_active:
                parallel_wcs = getattr(record, "parallel_workcenter_ids", self.env["mrp.workcenter"])
                existing_wcs = record.mold_line_ids.mapped("workcenter_id")
                missing_wcs = parallel_wcs - existing_wcs

                if missing_wcs:
                    lines = []
                    for wc in missing_wcs:
                        lines.append((0, 0, {
                            "workcenter_id": wc.id,
                        }))
                    record.mold_line_ids = lines
        return res

    @api.model_create_multi
    def create(self, vals_list):
        records = super(MrpRoutingWorkcenter, self).create(vals_list)
        for record in records:
            if record.is_parallel_active:
                parallel_wcs = getattr(record, "parallel_workcenter_ids", self.env["mrp.workcenter"])
                if parallel_wcs:
                    lines = []
                    for wc in parallel_wcs:
                        lines.append((0, 0, {
                            "workcenter_id": wc.id,
                        }))
                    record.mold_line_ids = lines
        return records


class MrpRoutingWorkcenterMoldLine(models.Model):
    _name = "mrp.routing.workcenter.mold.line"
    _description = "Mold Mapping Line"

    routing_id = fields.Many2one(
        "mrp.routing.workcenter",
        string="Operation",
        required=True,
        ondelete="cascade",
    )
    workcenter_id = fields.Many2one(
        "mrp.workcenter",
        string="Workcenter",
        required=True,
        domain=[("is_mold", "=", False)],
        help="The machine/workcenter where this mold is used.",
    )
    mold_id = fields.Many2one(
        "mrp.workcenter",
        string="Mold",
        domain=[("is_mold", "=", True)],
        help="The mold to use on this workcenter.",
    )

