# -*- coding: utf-8 -*-
from odoo import api, models


class MrpWorkorder(models.Model):
    _inherit = "mrp.workorder"

    def _recompute_duration_expected_parallel(self):
        """Reapply duration logic (planned qty / capacity) on parallel groups."""
        parallel_wos = self.filtered(
            lambda wo: wo.operation_id and wo.operation_id.parallel_mode == "parallel"
        )
        for wo in parallel_wos:
            # Use the current implementation of _get_duration_expected
            duration = wo._get_duration_expected()
            wo.write({"duration_expected": duration})

    def _recompute_parallel_siblings(self):
        """Recompute duration for all workorders of the same MO/operation."""
        grouped = {}
        for wo in self:
            if (
                not wo.production_id
                or not wo.operation_id
                or wo.operation_id.parallel_mode != "parallel"
            ):
                continue
            grouped.setdefault(
                (wo.production_id.id, wo.operation_id.id), self.env["mrp.workorder"]
            )
            grouped[(wo.production_id.id, wo.operation_id.id)] |= wo

        for siblings in grouped.values():
            siblings._recompute_duration_expected_parallel()

    @api.model
    def create(self, vals):
        records = super().create(vals)
        records._recompute_parallel_siblings()
        return records

    def unlink(self):
        affected = self.filtered(
            lambda wo: wo.operation_id and wo.operation_id.parallel_mode == "parallel"
        )
        ops = affected.mapped("operation_id")
        mos = affected.mapped("production_id")
        res = super(MrpWorkorder, self.with_context(mpc_disable_auto_split=True)).unlink()
        if ops and mos:
            siblings = self.env["mrp.workorder"].search(
                [
                    ("operation_id", "in", ops.ids),
                    ("production_id", "in", mos.ids),
                    ("state", "not in", ["done", "cancel"]),
                ]
            )
            if siblings:
                siblings._recompute_duration_expected_parallel()
        return res


class MrpRoutingWorkcenter(models.Model):
    _inherit = "mrp.routing.workcenter"

    def write(self, vals):
        tracked = {"parallel_mode", "parallel_workcenter_ids"}
        res = super().write(vals)
        if tracked.intersection(vals.keys()):
            workorders = self.env["mrp.workorder"].search(
                [
                    ("operation_id", "in", self.ids),
                    ("state", "not in", ["done", "cancel"]),
                ]
            )
            if workorders:
                workorders._recompute_parallel_siblings()
        return res


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    def write(self, vals):
        recompute = "product_qty" in vals
        res = super().write(vals)
        if recompute:
            workorders = self.mapped("workorder_ids").filtered(
                lambda wo: wo.operation_id and wo.operation_id.parallel_mode == "parallel"
            )
            # Re-split quantities across parallel workorders
            self._mpc_auto_split_parallel_workorders(create_missing=False)
        return res
