# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class MrpMpsSelectMachinesWizard(models.TransientModel):
    _name = "mrp.mps.select.machines.wizard"
    _description = "Select Parallel Machines for MPS Line"

    schedule_id = fields.Many2one(
        "mrp.production.schedule",
        string="MPS Line",
        required=True,
        readonly=True,
    )
    product_id = fields.Many2one(
        "product.product",
        string="Product",
        readonly=True,
    )
    mpc_machine_ids = fields.Many2many(
        "mrp.workcenter",
        "mrp_mps_select_machines_rel",
        "wizard_id",
        "workcenter_id",
        string="Parallel Machines",
        help="Workcenters to use when creating MOs from this MPS line.",
    )
    mpc_mold_warning = fields.Char(
        string="Mold Warning",
        readonly=True,
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        schedule = False
        if self.env.context.get("default_schedule_id"):
            schedule = self.env["mrp.production.schedule"].browse(
                self.env.context["default_schedule_id"]
            )
        if schedule:
            res["schedule_id"] = schedule.id
            res["product_id"] = schedule.product_id.id

        # Prefill machines:
        # 1) Use existing selection
        # 2) Fetch from BoM
        machines = self.env["mrp.workcenter"]
        if schedule and schedule.mpc_machine_ids:
            machines = schedule.mpc_machine_ids
        else:
            bom = False
            if schedule:
                bom = schedule.bom_id
                if not bom and schedule.product_id:
                    bom_map = (
                        self.env["mrp.bom"]
                        .sudo()
                        ._bom_find(
                            products=schedule.product_id,
                            company_id=schedule.company_id.id,
                        )
                        or {}
                    )
                    bom = (
                        bom_map.get(schedule.product_id)
                        if isinstance(bom_map, dict)
                        else False
                    )
            if bom:
                for op in bom.operation_ids.filtered(
                    lambda op_rec: op_rec.parallel_mode == "parallel"
                ):
                    if op.workcenter_id:
                        machines |= op.workcenter_id
                    machines |= op.parallel_workcenter_ids

        if machines:
            res["mpc_machine_ids"] = [(6, 0, machines.ids)]

        # Smart Matching (Matrix-Based): Suggest machines via compatibility matrix
        if schedule and schedule.product_id and self.env['mrp.workcenter'].is_mold_management_enabled():
            # 1. Query the Compatibility Matrix View
            matrix_lines = self.env["mrp.mold.matrix.report"].search([
                ("product_id", "=", schedule.product_id.id)
            ])

            if matrix_lines:
                # 2. Extract machines and molds from the matrix
                comp_machines = matrix_lines.mapped("machine_id")
                available_molds = matrix_lines.mapped("mold_id")

                if comp_machines:
                    # Update suggested selection
                    res["mpc_machine_ids"] = [(6, 0, comp_machines.ids)]

                # Check status for warnings (from any mold producing this product)
                critical_molds = available_molds.filtered(lambda m: getattr(m, 'mold_state', 'normal') in ('warning', 'full'))
                if critical_molds:
                    warnings = []
                    for mold in critical_molds:
                        status = "REACHED LIMIT" if mold.mold_state == 'full' else "nearing limit"
                        warnings.append(f"{mold.name} ({status}: {mold.mold_life_current}/{mold.mold_life_limit})")
                    res["mpc_mold_warning"] = _("WARNING: %s") % ", ".join(warnings)

            # 3. Fallback to general BoM recommendation ONLY if Matrix has no products defined
            elif not available_molds:
                # We basically don't have a fallback anymore because the Matrix is the Single Source of Truth.
                # However, we can still suggest the machine defined in the BoM as a neutral default.
                bom = schedule.bom_id or self.env["mrp.bom"]._bom_find(products=schedule.product_id, company_id=schedule.company_id.id).get(schedule.product_id)
                if bom:
                    comp_machines = self.env["mrp.workcenter"]
                    for op in bom.operation_ids:
                        comp_machines |= op.workcenter_id
                        comp_machines |= op.parallel_workcenter_ids

                    if comp_machines:
                        res["mpc_machine_ids"] = [(6, 0, comp_machines.ids)]

        return res

    def action_confirm(self):
        self.ensure_one()
        if not self.schedule_id:
            return {"type": "ir.actions.act_window_close"}

        # Save selected machines to MPS line
        self.schedule_id.mpc_machine_ids = [(6, 0, self.mpc_machine_ids.ids)]
        return {"type": "ir.actions.act_window_close"}


class MrpProductionSchedule(models.Model):
    _inherit = "mrp.production.schedule"

    mpc_machine_ids = fields.Many2many(
        "mrp.workcenter",
        "mrp_mps_mpc_wc_rel",
        "schedule_id",
        "workcenter_id",
        string="Parallel Machines",
        help="Workcenters to use when creating MOs from this MPS line.",
    )
    mpc_has_parallel_ops = fields.Boolean(
        string="Has Parallel Operations",
        compute="_compute_mpc_has_parallel_ops",
        store=False,
    )
    mpc_suggested_mold_id = fields.Many2one(
        "mrp.workcenter",
        string="Suggested Mold",
        compute="_compute_mpc_suggested_mold",
        help="The primary mold recommended for this product based on the compatibility matrix.",
    )

    def _compute_mpc_suggested_mold(self):
        if not self.env['mrp.workcenter'].is_mold_management_enabled():
            self.mpc_suggested_mold_id = False
            return

        for sched in self:
            # Use the matrix view to find the primary suggested mold
            matrix_line = self.env["mrp.mold.matrix.report"].search([
                ("product_id", "=", sched.product_id.id)
            ], limit=1)
            sched.mpc_suggested_mold_id = matrix_line.mold_id

    def _compute_mpc_has_parallel_ops(self):
        for sched in self:
            bom = sched.bom_id
            # fallback: ถ้าไม่ได้เลือก BoM บน MPS ให้ลองหา BoM จาก product
            if not bom and sched.product_id:
                bom_map = (
                    sched.env["mrp.bom"]
                    .sudo()
                    ._bom_find(
                        products=sched.product_id,
                        company_id=sched.company_id.id,
                    )
                    or {}
                )
                bom = (
                    bom_map.get(sched.product_id)
                    if isinstance(bom_map, dict)
                    else False
                )
            sched.mpc_has_parallel_ops = bool(
                bom
                and bom.operation_ids.filtered(
                    lambda op_rec: op_rec.parallel_mode == "parallel"
                )
            )

    def _get_procurement_extra_values(self, forecast_values):
        """ส่ง mps_schedule_id ไปให้ stock.rule เวลาสร้าง MO จาก MPS."""
        values = super()._get_procurement_extra_values(forecast_values)
        values["mps_schedule_id"] = self.id
        return values

    def get_procurement_values(self, forecast_values):
        """Ensure batch procurements also carry the MPS link."""
        res = super().get_procurement_values(forecast_values)
        if isinstance(res, list):
            for vals in res:
                vals.setdefault("mps_schedule_id", self.id)
        elif isinstance(res, dict):
            res.setdefault("mps_schedule_id", self.id)
        return res

    def _mpc_prefill_machines_from_bom(self):
        if self.mpc_machine_ids:
            return
        bom = self.bom_id
        if not bom and self.product_id:
            bom_map = (
                self.env["mrp.bom"]
                .sudo()
                ._bom_find(
                    products=self.product_id,
                    company_id=self.company_id.id,
                )
                or {}
            )
            bom = bom_map.get(self.product_id) if isinstance(bom_map, dict) else False
        if not bom:
            return
        machines = self.env["mrp.workcenter"]
        for op in bom.operation_ids.filtered(lambda op_rec: op_rec.parallel_mode == "parallel"):
            if op.workcenter_id:
                machines |= op.workcenter_id
            machines |= op.parallel_workcenter_ids
        if machines:
            self.mpc_machine_ids = [(6, 0, machines.ids)]

    def _mpc_smart_allocate_machines(self, allocated_machine_ids=None, matrix_lines=None, load_map=None):
        if self.mpc_machine_ids:
            return
        if not self.env['mrp.workcenter'].is_mold_management_enabled():
            self._mpc_prefill_machines_from_bom()
            return

        if allocated_machine_ids is None:
            allocated_machine_ids = set()

        bom = self.bom_id
        if not bom and self.product_id:
            bom_map = (
                self.env["mrp.bom"]
                .sudo()
                ._bom_find(
                    products=self.product_id,
                    company_id=self.company_id.id,
                )
                or {}
            )
            bom = bom_map.get(self.product_id) if isinstance(bom_map, dict) else False

        is_parallel = bool(
            bom
            and bom.operation_ids.filtered(
                lambda op_rec: op_rec.parallel_mode == "parallel"
            )
        )

        if matrix_lines is None:
            matrix_lines = self.env["mrp.mold.matrix.report"].search([
                ("product_id", "=", self.product_id.id),
            ])
        else:
            matrix_lines = matrix_lines.filtered(lambda m: m.product_id.id == self.product_id.id)

        if not matrix_lines:
            self._mpc_prefill_machines_from_bom()
            return

        if is_parallel:
            machines = matrix_lines.mapped("machine_id")
            if machines:
                self.mpc_machine_ids = [(6, 0, machines.ids)]
                allocated_machine_ids.update(machines.ids)
            return

        healthy = matrix_lines.filtered(lambda ml: ml.mold_state != 'full')
        candidates = healthy or matrix_lines

        normal = candidates.filtered(lambda ml: ml.mold_state == 'normal')
        if normal:
            candidates = normal

        if load_map is None:
            machine_ids = candidates.mapped("machine_id").ids
            wo_counts = self.env["mrp.workorder"].read_group(
                [("workcenter_id", "in", machine_ids), ("state", "not in", ("done", "cancel"))],
                ["workcenter_id"],
                ["workcenter_id"]
            )
            load_map = {res["workcenter_id"][0]: res["workcenter_id_count"] for res in wo_counts}

        def _rank(line):
            # Prefer machines not yet picked in this batch, then those with lower current load, then highest speed.
            busy_in_batch = 1 if line.machine_id.id in allocated_machine_ids else 0
            current_load = load_map.get(line.machine_id.id, 0)
            return (busy_in_batch, current_load, -line.units_per_hour)

        best = min(candidates, key=_rank)
        self.mpc_machine_ids = [(6, 0, [best.machine_id.id])]
        allocated_machine_ids.add(best.machine_id.id)

    def _get_forecast_demand_map(self):
        result = {sched.id: 0 for sched in self}
        try:
            states = self.get_production_schedule_view_state()
            if states and isinstance(states, list):
                for s in states:
                    sid = s.get("id")
                    if sid not in result:
                        continue
                    for row in s.get("forecast_ids", []):
                        qty = row.get("replenish_qty", 0) or row.get("forecast_qty", 0)
                        if qty > 0:
                            result[sid] = qty
                            break
        except Exception:
            _logger.warning("Failed to retrieve forecast demand for MPS priority sorting", exc_info=True)
        return result

    def _mpc_prefetch_allocation_data(self, scheds):
        matrix_lines = self.env["mrp.mold.matrix.report"].search([
            ("product_id", "in", scheds.mapped('product_id').ids)
        ])
        if not matrix_lines:
            return matrix_lines, {}
            
        machine_ids = matrix_lines.mapped("machine_id").ids
        wo_counts = self.env["mrp.workorder"].read_group(
            [("workcenter_id", "in", machine_ids), ("state", "not in", ("done", "cancel"))],
            ["workcenter_id"],
            ["workcenter_id"]
        )
        load_map = {res["workcenter_id"][0]: res["workcenter_id_count"] for res in wo_counts}
        return matrix_lines, load_map

    def action_replenish(self, based_on_lead_time=False, **kwargs):
        batch_id = self.env.context.get("mps_active_batch_id")
        if not batch_id and len(self) > 0:
            batch = self.env["mrp.mps.batch"].create({
                "note": "Created from MPS Parallel Replenish",
            })
            batch_id = batch.id
            self = self.with_context(mps_active_batch_id=batch_id)

        sorted_scheds = self
        try:
            if len(self) > 1 and self.env['mrp.workcenter'].is_mold_management_enabled():
                demand_map = self._get_forecast_demand_map()

                max_demand = max(demand_map.values()) if demand_map else 0
                min_demand = min(demand_map.values()) if demand_map else 0
                threshold = max_demand * 0.1

                if max_demand > 0 and (max_demand - min_demand) > threshold:
                    sorted_scheds = self.sorted(
                        key=lambda s: demand_map.get(s.id, 0), reverse=True
                    )
                    _logger.info(
                        "MPS Forecast Priority: %s",
                        [(s.product_id.display_name, demand_map.get(s.id, 0)) for s in sorted_scheds],
                    )
        except Exception:
            _logger.warning("Forecast priority sorting failed, using default order", exc_info=True)
            sorted_scheds = self

        allocated_machine_ids = set()
        
        # 1. Pre-fetch matrix lines and load map for all items in this batch to avoid N+1 queries
        matrix_cache, load_map = None, None
        if len(sorted_scheds) > 0 and self.env['mrp.workcenter'].is_mold_management_enabled():
            try:
                matrix_cache, load_map = self._mpc_prefetch_allocation_data(sorted_scheds)
            except Exception:
                pass
                
        # 2. Compute allocations in memory
        for sched in sorted_scheds:
            try:
                sched._mpc_smart_allocate_machines(allocated_machine_ids, matrix_lines=matrix_cache, load_map=load_map)
            except Exception:
                _logger.warning("Smart allocation failed for %s, falling back to BOM", sched.display_name, exc_info=True)
                try:
                    sched._mpc_prefill_machines_from_bom()
                except Exception:
                    pass
        
        # 3. Create Procurements / Call Standard action_replenish
        actions = []
        for sched in sorted_scheds:
            with self.env.cr.savepoint():
                try:
                    actions.append(
                        super(MrpProductionSchedule, sched.with_context(mps_active_batch_id=batch_id)).action_replenish(
                            based_on_lead_time=based_on_lead_time, **kwargs
                        )
                    )
                except Exception:
                    _logger.exception(
                        "MPS replenish failed for line %s (%s)",
                        sched.id,
                        sched.display_name,
                    )
                    raise
        return actions[-1] if actions else None




    def get_production_schedule_view_state(self, period_scale=False):
        """Inject flag mpc_has_parallel_ops เข้าไปใน state ที่ JS ใช้."""
        states = super().get_production_schedule_view_state(period_scale)
        flag_map = {sched.id: sched.mpc_has_parallel_ops for sched in self}
        for state in states:
            state["mpc_has_parallel_ops"] = flag_map.get(state["id"], False)
        return states

    def action_open_mpc_machines_wizard(self):
        """เปิด wizard เลือกเครื่องจาก MPS line."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Select Machines",
            "res_model": "mrp.mps.select.machines.wizard",
            "view_mode": "form",
            "views": [
                (
                    self.env.ref(
                        "mrp_parallel_console.view_mrp_mps_select_machines_wizard"
                    ).id,
                    "form",
                )
            ],
            "view_id": self.env.ref(
                "mrp_parallel_console.view_mrp_mps_select_machines_wizard"
            ).id,
            "target": "new",
            "context": {
                "default_schedule_id": self.id,
                "default_product_id": self.product_id.id,
            },
        }


class StockRule(models.Model):
    _inherit = "stock.rule"

    def _prepare_mo_vals(
        self,
        product_id,
        product_qty,
        product_uom,
        location_dest_id,
        name,
        origin,
        company_id,
        values,
        bom,
    ):
        vals = super()._prepare_mo_vals(
            product_id,
            product_qty,
            product_uom,
            location_dest_id,
            name,
            origin,
            company_id,
            values,
            bom,
        )
        schedule_id = values.get("mps_schedule_id")
        _logger.debug("MPS -> MO: schedule_id=%s, origin=%s", schedule_id, origin)

        schedule = self.env["mrp.production.schedule"]
        if schedule_id:
            schedule = schedule.browse(schedule_id)

        # Fallback: ถ้าไม่เจอ schedule_id (เช่น กด Order All แล้ว values หลุด)
        # ให้ลองหา Schedule ของสินค้านั้นๆ แทน
        if not schedule:
            if not hasattr(self.env.registry, '__mpc_schedule_cache'):
                self.env.registry.__mpc_schedule_cache = {}
            cache_key = (product_id.id, company_id.id)
            if cache_key not in self.env.registry.__mpc_schedule_cache:
                sched = self.env["mrp.production.schedule"].search([
                    ("product_id", "=", product_id.id),
                    ("company_id", "=", company_id.id),
                ], limit=1)
                self.env.registry.__mpc_schedule_cache[cache_key] = sched.id if sched else False
            
            s_id = self.env.registry.__mpc_schedule_cache[cache_key]
            if s_id:
                schedule = self.env["mrp.production.schedule"].browse(s_id)

        if schedule and schedule.exists() and schedule.mpc_machine_ids:
            machine_ids = schedule.mpc_machine_ids.ids
            vals["mpc_allowed_wc_ids"] = [(6, 0, machine_ids)]
            # เปิดให้ logic parallel split ทำงานเต็มที่
            vals["mpc_lock_parallel_wc"] = False
            _logger.debug("Setting MO machines from MPS: %s", machine_ids)
        else:
            _logger.debug("No machines found in schedule")
        return vals
