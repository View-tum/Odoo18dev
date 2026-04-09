# -*- coding: utf-8 -*-
from odoo import models
from odoo.tools import float_compare


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    def _mpc_matrix_candidates_for_workorder(self, workorder):
        Matrix = self.env["mrp.mold.matrix.report"]
        if not workorder.product_id:
            return Matrix

        machine_ids = set()
        if workorder.workcenter_id:
            machine_ids.add(workorder.workcenter_id.id)
        if workorder.operation_id:
            machine_ids.update(workorder.operation_id.parallel_workcenter_ids.ids)
            if workorder.operation_id.workcenter_id:
                machine_ids.add(workorder.operation_id.workcenter_id.id)
        if not machine_ids:
            machine_ids = set(workorder.production_id.workorder_ids.mapped("workcenter_id").ids)

        candidates = Matrix.search(
            [
                ("product_id", "=", workorder.product_id.id),
                ("machine_id", "in", list(machine_ids)),
            ]
        )
        healthy = candidates.filtered(lambda line: line.mold_state != "full")
        candidates = healthy or candidates
        normal = candidates.filtered(lambda line: line.mold_state == "normal")
        candidates = normal or candidates
        preferred_machine_id = workorder.workcenter_id.id
        return candidates.sorted(
            key=lambda line: (
                0 if line.machine_id.id == preferred_machine_id else 1,
                -(line.units_per_hour or 0.0),
                line.machine_id.id,
                line.mold_id.id,
                line.id,
            )
        )

    def _mpc_apply_matrix_candidate(self, workorder, matrix_line):
        desired_mold_ids = [matrix_line.mold_id.id] if matrix_line.mold_id else []
        updates = {}

        if workorder.workcenter_id.id != matrix_line.machine_id.id:
            updates["workcenter_id"] = matrix_line.machine_id.id
        if set(workorder.mold_ids.ids) != set(desired_mold_ids):
            updates["mold_ids"] = [(6, 0, desired_mold_ids)]

        if matrix_line.cycle_time > 0:
            cavities = matrix_line.mold_id.mold_cavities or 1
            planned_qty = (
                workorder.planned_qty
                or workorder.qty_production
                or workorder.production_id.product_qty
                or 0.0
            )
            shots = -(-planned_qty // cavities) if cavities else planned_qty
            expected_minutes = (shots * matrix_line.cycle_time) / 60.0
            if float_compare(
                workorder.duration_expected or 0.0,
                expected_minutes,
                precision_rounding=0.0001,
            ) != 0:
                updates["duration_expected"] = expected_minutes

        if updates:
            workorder.with_context(mpc_skip_autosplit=True).write(updates)

    def _mpc_enforce_unique_parallel_molds(self):
        if not self.env["mrp.workcenter"].is_mold_management_enabled():
            return False

        Workorder = self.env["mrp.workorder"]
        adjusted = False

        for production in self:
            groups = {}
            for workorder in production.workorder_ids.filtered(
                lambda wo: (
                    wo.state not in ("done", "cancel")
                    and wo.operation_id
                    and wo.operation_id.parallel_mode == "parallel"
                    and wo.product_id
                )
            ):
                groups.setdefault(workorder.operation_id.id, Workorder)
                groups[workorder.operation_id.id] |= workorder

            for group in groups.values():
                used_mold_ids = set()
                assigned = Workorder
                to_cancel = Workorder
                group_adjusted = False

                for workorder in group.sorted("id"):
                    candidates = self._mpc_matrix_candidates_for_workorder(workorder)
                    current = workorder.mold_ids[:1]
                    chosen = candidates.filtered(
                        lambda line: current and line.mold_id == current and line.mold_id.id not in used_mold_ids
                    )[:1]
                    if not chosen:
                        chosen = candidates.filtered(
                            lambda line: line.mold_id.id not in used_mold_ids
                        )[:1]

                    if chosen:
                        chosen = chosen[0]
                        previous_machine_id = workorder.workcenter_id.id
                        previous_mold_ids = set(workorder.mold_ids.ids)
                        self._mpc_apply_matrix_candidate(workorder, chosen)
                        assigned |= workorder
                        used_mold_ids.add(chosen.mold_id.id)
                        if (
                            previous_machine_id != chosen.machine_id.id
                            or previous_mold_ids != {chosen.mold_id.id}
                        ):
                            group_adjusted = True
                        continue

                    if workorder.mold_ids:
                        workorder.with_context(mpc_skip_autosplit=True).write(
                            {"mold_ids": [(5, 0, 0)]}
                        )
                        group_adjusted = True
                    if len(group) > 1 and assigned and workorder.state in (
                        "waiting",
                        "ready",
                        "pending",
                        "confirmed",
                    ):
                        to_cancel |= workorder

                if to_cancel and assigned:
                    to_cancel.write(
                        {
                            "state": "cancel",
                            "planned_qty": 0.0,
                            "console_qty": 0.0,
                            "qty_production": 0.0,
                        }
                    )
                    group_adjusted = True

                if group_adjusted:
                    active = (group - to_cancel).filtered(lambda wo: wo.state != "cancel")
                    if active:
                        production.write(
                            {
                                "mpc_allowed_wc_ids": [(6, 0, active.mapped("workcenter_id").ids)],
                                "mpc_lock_parallel_wc": True,
                            }
                        )
                    adjusted = True

        return adjusted

    def _mpc_auto_split_parallel_workorders(self, create_missing=False):
        res = super()._mpc_auto_split_parallel_workorders(create_missing=create_missing)
        if self.env.context.get("mpc_skip_unique_mold_guard"):
            return res
        if self._mpc_enforce_unique_parallel_molds():
            self.with_context(
                mpc_skip_unique_mold_guard=True,
                mpc_skip_cleanup=True,
            )._mpc_auto_split_parallel_workorders(create_missing=False)
        return res

    def action_suggest_machine_mold(self):
        res = super().action_suggest_machine_mold()
        if self.env.context.get("mpc_skip_unique_mold_guard"):
            return res
        if self._mpc_enforce_unique_parallel_molds():
            self.with_context(
                mpc_skip_unique_mold_guard=True,
                mpc_skip_cleanup=True,
            )._mpc_auto_split_parallel_workorders(create_missing=False)
        return res
