


from math import floor

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    mpc_allowed_wc_ids = fields.Many2many(
        "mrp.workcenter",
        "mrp_production_mpc_wc_rel",
        "production_id",
        "workcenter_id",
        string="Allowed Parallel Workcenters",
        help=(
            "If set, only these workcenters will be used when creating parallel workorders. "
            "If empty, all workcenters defined on the BoM operations are used."
        ),
    )
    mpc_lock_parallel_wc = fields.Boolean(
        string="Lock Parallel Workcenters",
        help="When enabled, do not auto-create missing parallel workorders if no allowlist is set.",
    )

    # ---------------------------------------------------------
    # Hook: after linking workorders and moves
    # ---------------------------------------------------------
    def _link_workorders_and_moves(self):
        res = super()._link_workorders_and_moves()
        # Drop/cancel WOs on blocked (maintenance) workcenters before any split logic
        self._mpc_remove_blocked_workorders()
        # After standard linking, ensure parallel workorders exist and
        # distribute quantities across them.
        if not self.env.context.get('mpc_disable_auto_split'):
            self._mpc_auto_split_parallel_workorders(create_missing=True)
        # Fix dependencies for parallel workorders so that workorders
        # of the same parallel operation do not block each other and
        # can start at the same time.
        self._mpc_fix_parallel_dependencies()
        return res

    def _plan_workorders(self, replan=False):
        """Defer to core planner; parallel tweaks happen during linking."""
        res = super()._plan_workorders(replan=replan)
        # Ensure blocked (maintenance) workcenters are cleaned even on manual replan,
        # then rebuild/redistribute and recreate missing WOs if the machine is free again.
        self._mpc_remove_blocked_workorders()
        self._mpc_auto_split_parallel_workorders(create_missing=True)
        return res

    def write(self, vals):
        qty_changed = "product_qty" in vals
        previous_qty = {}
        if qty_changed:
            for mo in self:
                previous_qty[mo.id] = mo.product_qty

        res = super().write(vals)

        if qty_changed:
            for mo in self:
                old_qty = previous_qty.get(mo.id)
                if old_qty is None:
                    continue
                rounding = mo.product_uom_id.rounding or 0.0001
                if float_compare(old_qty, mo.product_qty, precision_rounding=rounding) == 0:
                    continue

                for wo in mo.workorder_ids:
                    op = wo.operation_id
                    if op and op.parallel_mode == "parallel":
                        continue
                    updates = {}
                    wo_rounding = (
                        wo.product_uom_id.rounding
                        if "product_uom_id" in wo._fields and wo.product_uom_id
                        else rounding
                    )
                    if not wo.planned_qty or float_compare(
                        wo.planned_qty, old_qty, precision_rounding=wo_rounding
                    ) == 0:
                        updates["planned_qty"] = mo.product_qty
                    if not wo.console_qty or float_compare(
                        wo.console_qty, old_qty, precision_rounding=wo_rounding
                    ) == 0:
                        updates["console_qty"] = mo.product_qty
                    if updates:
                        wo.write(updates)
        return res

    # ---------------------------------------------------------
    # Work Center Management Actions
    # ---------------------------------------------------------
    def action_delete_work_centers_wizard(self):
        """Open wizard to delete work centers."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Delete Work Centers',
            'res_model': 'mrp.work.center.delete.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_id': self.id}
        }

    def action_add_work_centers_wizard(self):
        """Open wizard to add work centers."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Add Work Centers',
            'res_model': 'mrp.work.center.add.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_id': self.id}
        }

    def action_adjust_planned_qty_wizard(self):
        """Open wizard to adjust planned quantities."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Adjust Planned Quantities',
            'res_model': 'mrp.work.center.adjust.qty.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_id': self.id}
        }


    def button_plan(self):
        """Plan MO using the standard workflow."""
        return super().button_plan()

    def _post_run_manufacture(self, post_production_values):
        """Ensure new MOs created from procurement split quantities correctly."""
        res = super()._post_run_manufacture(post_production_values)
        productions = self.filtered(lambda mo: mo.mpc_allowed_wc_ids)
        if productions:
            productions.mpc_lock_parallel_wc = False
            productions._mpc_auto_split_parallel_workorders(create_missing=True)
        return res

    def _mpc_cleanup_parallel_duplicates(self):
        """Deduplicate parallel workorders on the same operation/workcenter.

        Keeps the oldest (smallest id) and removes the rest. This avoids
        accidental duplication before splitting/creating workorders.
        """
        # Allow callers (e.g., Add Work Center wizard) to opt out of cleanup
        # so freshly created workorders are not removed in the same request.
        if self.env.context.get("mpc_skip_cleanup"):
            return

        Workorder = self.env["mrp.workorder"]
        for mo in self:
            dupe_map = {}
            for wo in mo.workorder_ids.filtered(
                lambda w: w.operation_id and w.operation_id.parallel_mode == "parallel" and w.state != "cancel"
            ):
                key = (wo.operation_id.id, wo.workcenter_id.id)
                dupe_map.setdefault(key, Workorder)
                dupe_map[key] |= wo
            to_remove = Workorder
            for group in dupe_map.values():
                if len(group) <= 1:
                    continue
                sorted_group = group.sorted("id")
                to_remove |= sorted_group[1:]
            if to_remove:
                # อย่าลบ record ทิ้งเพราะอาจถูกอ้างอิงอยู่ (เช่น MPS)
                # เปลี่ยนเป็น cancel เพื่อคงข้อมูลและหลีกเลี่ยง missing record
                to_remove.write({"state": "cancel"})
    def _mpc_auto_split_parallel_workorders(self, create_missing=False):
        """
        Auto split MO quantity across parallel workorders.

        IMPORTANT FIX:
        - Cleanup duplicates only if mpc_skip_cleanup=False
        - ALWAYS run:
            * _mpc_auto_split_one_mo()
            * _mpc_fix_parallel_dependencies()
            * invalidate workorder_ids
        This ensures new workorders added via wizard appear in console UI.
        """
        for mo in self:

            skip_cleanup = mo.env.context.get("mpc_skip_cleanup")

            # 1) cleanup duplicates only when allowed
            if not skip_cleanup:
                mo._mpc_cleanup_parallel_duplicates()

            # 1.1) cancel/remove workorders on blocked workcenters (maintenance)
            mo._mpc_remove_blocked_workorders()

            # 2) ALWAYS split qty (capacity-based distribution)
            mo._mpc_auto_split_one_mo(create_missing=create_missing)

            # 3) ALWAYS rebuild dependencies for parallel operations
            mo._mpc_fix_parallel_dependencies()

            # 4) IMPORTANT: reload workorder_ids so console sees new WOs
            mo.invalidate_recordset(["workorder_ids"])


    # ------------------------------------------------------------------
    # Maintenance / blocked workcenter helpers
    # ------------------------------------------------------------------
    def _mpc_is_wc_blocked(self, wc_id):
        wc = self.env["mrp.workcenter"].browse(wc_id)
        m_state = getattr(wc, "maintenance_state", False)
        if m_state and m_state not in ("normal", "available"):
            return True

        if "maintenance.request" in self.env.registry:
            maintenance_model = self.env["maintenance.request"].sudo()
            domain = [("workcenter_id", "=", wc_id)]
            if "state" in maintenance_model._fields:
                domain.append(("state", "not in", ["done", "cancel"]))
            elif "stage_id" in maintenance_model._fields:
                stage_field = maintenance_model._fields.get("stage_id")
                stage_model = getattr(stage_field, "comodel_name", False)
                if stage_model and "done" in self.env[stage_model]._fields:
                    domain.append(("stage_id.done", "=", False))
            if maintenance_model.search_count(domain):
                return True
        return False

    def _mpc_remove_blocked_workorders(self):
        """Cancel workorders assigned to blocked workcenters (maintenance)."""
        for mo in self:
            # Group by operation so we keep at least one WO when all machines are blocked.
            ops = {}
            for wo in mo.workorder_ids:
                if wo.state in ("done", "cancel") or not wo.operation_id:
                    continue
                ops.setdefault(wo.operation_id, self.env["mrp.workorder"])
                ops[wo.operation_id] |= wo

            for op, op_wos in ops.items():
                blocked = op_wos.filtered(lambda wo: self._mpc_is_wc_blocked(wo.workcenter_id.id))
                unblocked = op_wos - blocked
                # If everything is blocked, keep them (user will start after maintenance).
                if blocked and unblocked:
                    blocked.write(
                        {
                            "state": "cancel",
                            "planned_qty": 0.0,
                            "console_qty": 0.0,
                            "qty_production": 0.0,
                        }
                    )

    # ------------------------------------------------------------------
    # Capacity-based splitting helpers
    # ------------------------------------------------------------------
    def _mpc_get_wc_capacity_weight(self, wc):
        """Return capacity weight for a workcenter."""
        capacity = 1.0

        if "default_capacity" in wc._fields:
            capacity = wc.default_capacity or 1.0
        elif "capacity" in wc._fields:
            capacity = wc.capacity or 1.0

        eff = (wc.time_efficiency or 100.0) / 100.0
        if eff <= 0:
            eff = 1.0

        oee = wc.oee_target or 1.0
        if oee <= 0:
            oee = 1.0

        return float(capacity) * eff * oee

    def _mpc_split_qty_by_capacity(self, total_qty, workorders):
        """Split integer qty across workorders using capacity weights."""
        if not workorders or not total_qty:
            return []

        wo_list = list(workorders)
        weights = [
            self._mpc_get_wc_capacity_weight(wo.workcenter_id) for wo in wo_list
        ]
        total_weight = sum(weights)

        # Fallback: equal split if no usable weights
        if total_weight <= 0:
            n = len(wo_list)
            if n == 0:
                return []
            base = int(floor(total_qty / n))
            result = [(wo, base) for wo in wo_list]
            remainder = int(total_qty - base * n)
            for i in range(remainder):
                wo, qty = result[i]
                result[i] = (wo, qty + 1)
            return result

        ideal = [total_qty * w / total_weight for w in weights]
        base = [int(floor(x)) for x in ideal]
        assigned = sum(base)
        remainder = int(total_qty - assigned)

        fractions = [(ideal[i] - base[i], i) for i in range(len(wo_list))]
        fractions.sort(reverse=True)

        idx = 0
        while remainder > 0 and fractions:
            _, i = fractions[idx]
            base[i] += 1
            remainder -= 1
            idx = (idx + 1) % len(fractions)

        return [(wo_list[i], base[i]) for i in range(len(wo_list))]

    def _mpc_auto_split_one_mo(self, create_missing=False):
        """Distribute MO quantity across workorders (no fraction for parallel).

        Rules:
        - Optionally create missing workorders for parallel operations
          (one per configured workcenter).
        - For non-parallel operations:
          * If planned_qty is empty => set to full MO quantity.
        - For parallel operations (operation.parallel_mode = 'parallel'):
          * Group workorders by operation.
          * Use integer part of MO quantity for splitting.
          * Example: 101 / 4 => 26, 25, 25, 25.
          * First workorders in the group get +1 until remainder is exhausted.
        - If console_qty is empty, default = planned_qty.
        """
        self.ensure_one()

        # 0) When requested, ensure we have one workorder per configured
        #    parallel workcenter for each operation.
        if create_missing:
            self._mpc_create_parallel_workorders()

        mo_qty = self.product_qty or 0.0
        if mo_qty <= 0:
            return

        int_qty = int(round(mo_qty))

        parallel_groups = {}
        for wo in self.workorder_ids:
            if wo.state == "cancel":
                continue
            op = wo.operation_id
            if not op or op.parallel_mode != "parallel":
                # no parallel: ensure planned_qty is at least full MO qty
                if not wo.planned_qty:
                    wo.planned_qty = mo_qty
                    if not wo.console_qty:
                        wo.console_qty = mo_qty
                continue

            key = op.id
            parallel_groups.setdefault(key, self.env["mrp.workorder"])
            parallel_groups[key] |= wo

        base_qty = max(int_qty, 0)
        touched_wos = self.env["mrp.workorder"]
        for _op_id, wos in parallel_groups.items():
            wos = wos.sorted("id")
            machine_qty = len(wos)
            if machine_qty <= 0:
                continue

            splits = self._mpc_split_qty_by_capacity(base_qty, wos)
            if not splits:
                qty_per_machine = base_qty // machine_qty if machine_qty else 0
                remainder = base_qty % machine_qty if machine_qty else 0
                splits = [
                    (
                        wos[idx],
                        qty_per_machine + (1 if idx < remainder else 0),
                    )
                    for idx in range(machine_qty)
                ]

            for wo, split_qty in splits:
                wo.write(
                    {
                        "planned_qty": split_qty,
                        "console_qty": split_qty,
                    }
                )
                touched_wos |= wo

        if touched_wos:
            touched_wos._recompute_parallel_siblings()




    def _mpc_create_parallel_workorders(self):
        """Create missing parallel workorders per operation/workcenter.

        For each operation configured with parallel_mode = 'parallel',
        make sure there is one workorder per workcenter in:
            operation.workcenter_id + operation.parallel_workcenter_ids

        This is only called right after standard workorders are created,
        so we don't interfere with manual deletions later on.
        """
        self.ensure_one()
        Workorder = self.env["mrp.workorder"]

        # Group existing workorders by operation.
        wos_by_op = {}
        for wo in self.workorder_ids:
            if not wo.operation_id:
                continue
            if wo.state == "cancel":
                continue
            wos_by_op.setdefault(wo.operation_id, self.env["mrp.workorder"])
            wos_by_op[wo.operation_id] |= wo

        for op, wos in wos_by_op.items():
            if op.parallel_mode != "parallel":
                continue
            # Desired workcenters = main + configured parallel ones.
            desired_wc_ids = set(op.parallel_workcenter_ids.ids)
            if op.workcenter_id:
                desired_wc_ids.add(op.workcenter_id.id)
            if not desired_wc_ids:
                continue

            # Drop workcenters currently under maintenance and cancel existing WOs on them
            blocked_wc_ids = {wc_id for wc_id in desired_wc_ids if self._mpc_is_wc_blocked(wc_id)}
            if blocked_wc_ids:
                # If all desired are blocked, keep at least the original set so the op is not lost.
                if len(blocked_wc_ids) == len(desired_wc_ids):
                    # do not cancel everything; keep as-is so users can run after maintenance
                    blocked_wc_ids = set()
                else:
                    blocked_wos = wos.filtered(
                        lambda wo: wo.workcenter_id.id in blocked_wc_ids
                        and wo.state not in ("done", "cancel")
                    )
                    if blocked_wos:
                        blocked_wos.write({"state": "cancel"})

            desired_wc_ids = {wc_id for wc_id in desired_wc_ids if wc_id not in blocked_wc_ids}
            # If MO restricts allowed machines, keep only intersection.
            allowed_wc_ids = set(self.mpc_allowed_wc_ids.ids)
            if allowed_wc_ids:
                desired_wc_ids &= allowed_wc_ids
            elif self.mpc_lock_parallel_wc:
                # User explicitly locked machine selection: do not create
                # new workorders when no allowlist is set.
                continue
            if not desired_wc_ids:
                continue

            # Drop workorders whose workcenters are no longer desired.
            existing_wc_ids = set(wos.mapped("workcenter_id").ids)
            extra_wc_ids = existing_wc_ids - desired_wc_ids
            if extra_wc_ids and not self.env.context.get("mpc_skip_cleanup"):
                to_remove = wos.filtered(
                    lambda wo: wo.workcenter_id.id in extra_wc_ids
                )
                if to_remove:
                    # อย่าลบ workorder ทิ้งใน flow MPS ให้ cancel แทน
                    to_remove.write({"state": "cancel"})
                    wos -= to_remove
                    existing_wc_ids -= extra_wc_ids

            wos = wos.filtered(lambda wo: wo.exists())
            existing_wc_ids = set(wos.mapped("workcenter_id").ids)
            missing_wc_ids = desired_wc_ids - existing_wc_ids
            if not missing_wc_ids:
                continue

            template = wos[:1] or self.workorder_ids.filtered(
                lambda wo: wo.operation_id == op
            )[:1]
            if not template:
                continue
            template = template[0]

            for wc_id in missing_wc_ids:
                vals = {
                    "name": template.name,
                    "production_id": self.id,
                    "workcenter_id": wc_id,
                    "product_uom_id": template.product_uom_id.id,
                    "operation_id": op.id,
                    "state": template.state if template.state not in ("done", "cancel", "progress") else "ready",
                }
                Workorder.create(vals)

    def _mpc_fix_parallel_dependencies(self):
        """Adjust blocked_by dependencies for parallel workorders.

        For each operation configured in parallel mode, all workorders
        belonging to that operation should start together once their
        predecessors are done, and must not block each other.

        This method:
        - Collects all workorders for a parallel operation.
        - Computes the set of blockers outside that group.
        - Sets every workorder in the group to be blocked only by that
          external set (removing the default sequential chain).
        """
        for mo in self:
            wos = mo.workorder_ids
            if not wos:
                continue

            # Group workorders by operation for parallel operations.
            by_op = {}
            for wo in wos:
                op = wo.operation_id
                if not op or op.parallel_mode != "parallel":
                    continue
                by_op.setdefault(op.id, mo.env["mrp.workorder"])
                by_op[op.id] |= wo

            for _op_id, group in by_op.items():
                if not group:
                    continue
                # Blockers outside this parallel group.
                external_blockers = (group.mapped("blocked_by_workorder_ids") - group)
                external_ids = external_blockers.ids
                for wo in group:
                    wo.blocked_by_workorder_ids = [(6, 0, external_ids)]

class MrpWorkorder(models.Model):
    _inherit = "mrp.workorder"

    def _get_duration_expected(self, alternative_workcenter=False, ratio=1):
        """Use planned_qty for parallel ops to avoid inflated durations."""
        self.ensure_one()
        if (
            self.operation_id
            and self.operation_id.parallel_mode == "parallel"
            and self.planned_qty
        ):
            wc = alternative_workcenter or self.workcenter_id
            if not wc:
                return super()._get_duration_expected(
                    alternative_workcenter=alternative_workcenter, ratio=ratio
                )
            qty_production = self.production_id.product_uom_id._compute_quantity(
                self.planned_qty, self.production_id.product_id.uom_id
            )
            capacity = wc._get_capacity(self.product_id)
            if capacity <= 0:
                raise UserError(
                    _(
                        "Work center %s has no valid capacity. Please set a positive capacity/time efficiency."
                    )
                    % wc.display_name
                )
            cycle_number = float_round(
                qty_production / capacity, precision_digits=0, rounding_method="UP"
            )
            time_cycle = self.operation_id.time_cycle
            duration = cycle_number * time_cycle * 100.0 / wc.time_efficiency
            duration *= ratio
            return duration

        return super()._get_duration_expected(
            alternative_workcenter=alternative_workcenter, ratio=ratio
        )

    @api.depends(
        "qty_production",
        "qty_reported_from_previous_wo",
        "qty_produced",
        "production_id.product_uom_id",
        "planned_qty",
        "operation_id.parallel_mode",
    )
    def _compute_qty_remaining(self):
        # first, use standard computation
        super()._compute_qty_remaining()

        # then, adjust for parallel operations to use planned_qty
        # instead of the full MO quantity.
        for wo in self:
            op = wo.operation_id
            if not op or op.parallel_mode != "parallel":
                continue
            if not wo.production_id.product_uom_id:
                wo.qty_remaining = 0
                continue

            base_qty = wo.planned_qty or wo.qty_production
            rounding = wo.production_id.product_uom_id.rounding
            wo.qty_remaining = max(
                float_round(
                    base_qty - wo.qty_produced,
                    precision_rounding=rounding,
                ),
                0,
            )

    def unlink(self):
        """After deleting workorders, re-split the remaining parallel group."""
        productions = self.mapped("production_id")

        for mo in productions:
            remaining_wc_ids = (mo.workorder_ids - self).mapped("workcenter_id").ids
            mo.mpc_allowed_wc_ids = [(6, 0, remaining_wc_ids)]
            mo.mpc_lock_parallel_wc = True

        res = super().unlink()
        if productions:
            for mo in productions:
                # Always sync allowed machine list to the current set of
                # workcenters for this MO. This ensures that manual
                # deletions from the console or MO form become the new
                # "truth" for how many machines this MO should use.
                mo.mpc_allowed_wc_ids = [
                    (6, 0, mo.workorder_ids.mapped("workcenter_id").ids)
                ]
                mo.mpc_lock_parallel_wc = True
            # After manual deletions, only redistribute quantities across
            # remaining workorders; we don't recreate missing ones.
            productions._mpc_auto_split_parallel_workorders(create_missing=False)
        return res

    @api.model
    def create(self, vals_list):
        """Ensure quantities stay balanced when workorders are added manually.

        When users add workorders from the MO form (e.g. to add a new
        machine), we want the parallel split logic to redistribute the
        planned/console quantities across the new set of workorders.
        This mirrors what :meth:`unlink` already does after deletions.
        """
        # Support both single-dict and list-of-dicts creates.
        single = isinstance(vals_list, dict)
        if single:
            vals_list = [vals_list]



        def _clamp_quantities(vals):
            prod_id = vals.get("production_id")
            planned = vals.get("planned_qty")
            console = vals.get("console_qty")
            if not prod_id or planned is None:
                return
            production = self.env["mrp.production"].browse(prod_id)
            if not production or not production.exists():
                return
            mo_qty = production.product_qty or 0.0
            if mo_qty <= 0:
                return
            if planned > mo_qty:
                vals["planned_qty"] = mo_qty
            if console and console > mo_qty:
                vals["console_qty"] = mo_qty

        for vals in vals_list:
            _clamp_quantities(vals)

        workorders = super().create(vals_list)

        if not self.env.context.get("mpc_skip_autosplit"):
            productions = workorders.mapped("production_id")
            if productions:
                # Only sync the allowlist when the MO is already locked (e.g.
                # after users intentionally removed machines). Otherwise, keep
                # any explicit configuration coming from MPS or the MO itself.
                locked_mos = productions.filtered("mpc_lock_parallel_wc")
                for mo in locked_mos:
                    allowed_wc_ids = set(mo.mpc_allowed_wc_ids.ids)
                    allowed_wc_ids |= set(mo.workorder_ids.mapped("workcenter_id").ids)
                    mo.mpc_allowed_wc_ids = [(6, 0, list(allowed_wc_ids))]
                # Only redistribute across existing workorders; do not
                # recreate missing ones when lines are added manually.
                productions.with_context(mpc_skip_cleanup=True)._mpc_auto_split_parallel_workorders(
                    create_missing=False
                )

        # Safety: ensure non-parallel workorders carry planned_qty/console_qty
        # so expected duration is not zeroed out unintentionally.
        for wo in workorders:
            op = wo.operation_id
            if op and op.parallel_mode == "parallel":
                continue
            if wo.production_id and not wo.planned_qty and wo.production_id.product_qty:
                qty = wo.production_id.product_qty
                vals = {"planned_qty": qty}
                if not wo.console_qty:
                    vals["console_qty"] = qty
                if vals:
                    wo.write(vals)

        return workorders[0] if single else workorders

    def _mpc_cleanup_parallel_duplicates(self):
        """Deduplicate parallel workorders sharing the same operation/workcenter."""
        # Allow callers (e.g., Add Work Center wizard) to skip cleanup to avoid
        # deleting just-created workorders in the same request.
        if self.env.context.get("mpc_skip_cleanup"):
            return

        Workorder = self.env["mrp.workorder"]
        for mo in self:
            dupe_map = {}
            for wo in mo.workorder_ids.filtered(
                lambda w: w.operation_id and w.operation_id.parallel_mode == "parallel"
            ):
                key = (wo.operation_id.id, wo.workcenter_id.id)
                dupe_map.setdefault(key, Workorder)
                dupe_map[key] |= wo
            to_remove = Workorder
            for group in dupe_map.values():
                if len(group) <= 1:
                    continue
                # keep oldest (smallest id), remove the rest
                sorted_group = group.sorted("id")
                to_remove |= sorted_group[1:]
            if to_remove:
                # ห้ามลบ workorder ทิ้ง เพราะอาจถูกอ้างอิง (เช่น MPS)
                # เปลี่ยนเป็นยกเลิกสถานะ (cancel) แทนเพื่อไม่ให้ core พัง
                to_remove.write({"state": "cancel"})

    def button_plan(self):
        """Plan MO using core scheduling (parallel logic handled elsewhere)."""
        return super().button_plan()

    @api.constrains("planned_qty")
    def _check_planned_qty_reasonable(self):
        for wo in self:
            if (
                wo.operation_id
                and wo.operation_id.parallel_mode == "parallel"
                and wo.planned_qty
                and wo.production_id
                and wo.planned_qty > (wo.production_id.product_qty or 0.0)
            ):
                raise UserError(
                    _(
                        "Parallel bug: planned_qty (%(planned)s) exceeds MO quantity (%(mo)s)."
                    )
                    % {
                        "planned": wo.planned_qty,
                        "mo": wo.production_id.product_qty,
                    }
                )
