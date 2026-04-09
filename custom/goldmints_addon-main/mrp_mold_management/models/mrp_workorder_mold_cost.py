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
    mold_shots_posted = fields.Integer(
        string="Posted Mold Shots",
        readonly=True,
        copy=False,
        default=0,
        help="Tracks how many mold shots were already posted to avoid duplicate mold life increments.",
    )

    @api.depends("operation_id", "workcenter_id", "product_id")
    def _compute_mold_ids(self):
        # Global Kill Switch
        if not self.env['mrp.workcenter'].is_mold_management_enabled():
            for wo in self:
                wo.mold_ids = False
            return

        for wo in self:
            # 1. Try Matrix Matching via SQL View
            if wo.workcenter_id and wo.product_id:
                matrix_line = self.env["mrp.mold.matrix.report"].search([
                    ("machine_id", "=", wo.workcenter_id.id),
                    ("product_id", "=", wo.product_id.id)
                ], limit=1)

                if matrix_line:
                    wo.mold_ids = matrix_line.mold_id

                    # [NEW] Adjust Expected Duration based on Mold Speed
                    # If matrix has a cycle time, use it: Duration = (Qty * Cycle Time) / 60
                    if matrix_line.cycle_time > 0:
                        # We use qty_production (planned) to update duration_expected
                        # Divide by cavities is already handled in cycle_time logic if we assume
                        # cycle_time is per SHOT and cavities produce multiple units.
                        # Wait, Odoo's duration is in MINUTES.
                        # shots = Qty / Cavities
                        # time = shots * CycleTime (seconds) / 60 (minutes)
                        shots = -(-wo.qty_production // wo.mold_ids.mold_cavities) if wo.mold_ids.mold_cavities else wo.qty_production
                        expected_minutes = (shots * matrix_line.cycle_time) / 60.0
                        wo.duration_expected = expected_minutes

                    continue

            if not wo.operation_id:
                wo.mold_ids = False
                continue

            # LEGACY: Fallback to BoM fields removed.
            # The system now relies on the Compatibility Matrix (Step 1 above).
            # If no Matrix match, we default to False unless manually assigned.
            wo.mold_ids = False

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

    def _on_finish_calculate_mold_shots(self):
        """Calculate and update shots for linked molds upon finishing."""
        if not self.env['mrp.workcenter'].is_mold_management_enabled():
            return

        for wo in self:
            if not wo.mold_ids:
                continue

            max_cavities = max(wo.mold_ids.mapped("mold_cavities") or [1])
            qty_logs = self.env["mrp.workorder.qty.log"].search([("workorder_id", "=", wo.id)])
            produced_qty = (
                sum(qty_logs.mapped("qty"))
                or wo.qty_produced
                or getattr(wo, "console_qty", 0.0)
                or getattr(wo, "qty_producing", 0.0)
                or 0.0
            )
            if produced_qty <= 0:
                continue
            shots = -(-produced_qty // max_cavities) if max_cavities else 0
            shots = int(shots or 0)
            delta_shots = shots - (wo.mold_shots_posted or 0)
            if delta_shots <= 0:
                continue

            for mold in wo.mold_ids:
                mold.sudo().mold_life_current += delta_shots
            wo.mold_shots_posted = shots

    def button_finish(self):
        res = super(MrpWorkorder, self).button_finish()
        self._on_finish_calculate_mold_shots()
        return res
