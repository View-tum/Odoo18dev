# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.tools import float_round

class MrpWorkorder(models.Model):
    _inherit = "mrp.workorder"

    mold_ids = fields.Many2many(
        "mrp.workcenter",
        string="Molds",
        compute="_compute_mold_ids",
        store=True,
        readonly=False,
        domain=[("is_mold", "=", True)],
        help="Molds used for this workorder. Defaults from the operation but can be modified per workorder.",
    )
    mold_cost = fields.Float(
        string="Mold Cost",
        compute="_compute_mold_cost",
        store=True,
        help="Mold cost based on workorder duration and mold cost/hour.",
    )
    mold_names = fields.Char(
        string="Molds",
        compute="_compute_mold_names",
        store=True,
        help="Helper text of mold names for planning/overview lists.",
    )

    @api.depends("operation_id", "workcenter_id")
    def _compute_mold_ids(self):
        for wo in self:
            if not wo.operation_id:
                wo.mold_ids = False
                continue

            # Check for specific mapping in BOM Operation
            mapping = wo.operation_id.mold_line_ids.filtered(
                lambda l: l.workcenter_id == wo.workcenter_id
            )
            if mapping:
                # If mapping exists for this workcenter, use it
                wo.mold_ids = mapping.mapped("mold_id")
            else:
                # Fallback to general molds defined on operation
                wo.mold_ids = wo.operation_id.mold_ids

    @api.depends("duration", "mold_ids")
    def _compute_mold_cost(self):
        currency = self.env.company.currency_id
        for wo in self:
            if not wo.mold_ids:
                wo.mold_cost = 0.0
                continue

            hours = (wo.duration or 0.0) / 60.0
            cost_per_hour = sum(wo.mold_ids.mapped("mold_cost_hour"))
            raw_cost = hours * cost_per_hour

            wo.mold_cost = float_round(raw_cost, precision_rounding=currency.rounding)

    @api.depends("mold_ids")
    def _compute_mold_names(self):
        for wo in self:
            wo.mold_names = ", ".join(wo.mold_ids.mapped("name")) if wo.mold_ids else ""

    # [NEW] Override display_name to show Mold info in Planning/Gantt
    @api.depends("name", "workcenter_id", "mold_names")
    def _compute_display_name(self):
        for wo in self:
            # Standard name format: Workcenter - Operation
            base = wo.name or ""
            if wo.workcenter_id and wo.workcenter_id.name:
                base = f"{wo.workcenter_id.name} - {base}"

            # Append Mold info
            if wo.mold_names:
                wo.display_name = f"{base} ({wo.mold_names})"
            else:
                wo.display_name = base
