import os
import re

file_path = r'c:\365_project\TheCool18e\Dev\custom\goldmints_addon-main\mrp_parallel_console\models\mrp_mps_parallel_machines.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace StockRule
old_stock_rule = '''        # Fallback: ????????? schedule_id (???? ?? Order All ???? values ????)
        # ???????? Schedule ?????????????? ???
        if not schedule:
            schedule = self.env["mrp.production.schedule"].search([
                ("product_id", "=", product_id.id),
                ("company_id", "=", company_id.id),
            ], limit=1)'''

new_stock_rule = '''        # Fallback: ????????? schedule_id (???? ?? Order All ???? values ????)
        # ???????? Schedule ?????????????? ???
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
                schedule = self.env["mrp.production.schedule"].browse(s_id)'''

if old_stock_rule in content:
    content = content.replace(old_stock_rule, new_stock_rule)
    print("Patched StockRule")
else:
    print("Failed to patch StockRule")

# Replace _mpc_smart_allocate_machines and action_replenish
old_allocate = '''    def _mpc_smart_allocate_machines(self, allocated_machine_ids=None):
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

        matrix_lines = self.env["mrp.mold.matrix.report"].search([
            ("product_id", "=", self.product_id.id),
        ])

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

        # Get current load for all candidate machines
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
        allocated_machine_ids.add(best.machine_id.id)'''

new_allocate = '''    def _mpc_smart_allocate_machines(self, allocated_machine_ids=None, matrix_lines=None, load_map=None):
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
        allocated_machine_ids.add(best.machine_id.id)'''

if old_allocate in content:
    content = content.replace(old_allocate, new_allocate)
    print("Patched allocate")
else:
    print("Failed to patch allocate")

old_replenish = '''    def action_replenish(self, based_on_lead_time=False, **kwargs):
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
        actions = []
        for sched in sorted_scheds:
            try:
                sched._mpc_smart_allocate_machines(allocated_machine_ids)
            except Exception:
                _logger.warning("Smart allocation failed for %s, falling back to BOM", sched.display_name, exc_info=True)
                try:
                    sched._mpc_prefill_machines_from_bom()
                except Exception:
                    pass
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
        return actions[-1] if actions else None'''

new_replenish = '''    def _mpc_prefetch_allocation_data(self, scheds):
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
        return actions[-1] if actions else None'''

if old_replenish in content:
    content = content.replace(old_replenish, new_replenish)
    print("Patched replenish")
else:
    print("Failed to patch replenish")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Done patching mrp_mps_parallel_machines.py")
