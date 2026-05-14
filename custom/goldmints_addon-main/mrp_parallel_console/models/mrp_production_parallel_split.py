from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero, float_round


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
        ready_mos = self.filtered(lambda mo: mo.state != "draft")
        ready_mos._mpc_remove_blocked_workorders()
        # After standard linking, ensure parallel workorders exist and
        # distribute quantities across them.
        #
        # During mrp.production.action_confirm(), core calls this method while
        # the MO can still be draft. Creating extra workorders at that point can
        # force a recompute of finished moves and Odoo may try to delete linked
        # MTO moves, which is blocked by standard stock constraints.
        if ready_mos and not self.env.context.get("mpc_disable_auto_split"):
            ready_mos._mpc_auto_split_parallel_workorders(create_missing=True)
        # Fix dependencies for parallel workorders so that workorders
        # of the same parallel operation do not block each other and
        # can start at the same time.
        ready_mos._mpc_fix_parallel_dependencies()
        return res

    def action_confirm(self):
        res = super().action_confirm()
        if not self.env.context.get("mpc_disable_auto_split"):
            ready_mos = self.filtered(lambda mo: mo.state in ("confirmed", "progress", "to_close"))
            ready_mos._mpc_remove_blocked_workorders()
            ready_mos._mpc_auto_split_parallel_workorders(create_missing=True)
            ready_mos._mpc_fix_parallel_dependencies()
        return res

    def _plan_workorders(self, replan=False):
        """Defer to core planner; parallel tweaks happen during linking."""
        res = super()._plan_workorders(replan=replan)
        # Ensure blocked (maintenance) workcenters are cleaned even on manual replan,
        # then rebuild/redistribute and recreate missing WOs if the machine is free again.
        ready_mos = self.filtered(lambda mo: mo.state != "draft")
        ready_mos._mpc_remove_blocked_workorders()
        ready_mos._mpc_auto_split_parallel_workorders(create_missing=True)
        return res

    def write(self, vals):
        qty_changed = "product_qty" in vals
        previous_qty = {}
        if qty_changed:
            for mo in self:
                previous_qty[mo.id] = mo.product_qty

        res = super().write(vals)

        if qty_changed:
            mos_to_rebuild = self.env["mrp.production"]
            for mo in self:
                old_qty = previous_qty.get(mo.id)
                if old_qty is None:
                    continue
                rounding = mo.product_uom_id.rounding or 0.000001
                if float_compare(old_qty, mo.product_qty, precision_rounding=rounding) == 0:
                    continue

                mos_to_rebuild |= mo
                # Update non-parallel (sequential) workorders that were covering the full MO qty
                for wo in mo.workorder_ids:
                    if wo.state in ("done", "cancel"):
                        continue
                    op = wo.operation_id
                    if op and op.parallel_mode == "parallel":
                        continue

                    wo_rounding = (
                        wo.product_uom_id.rounding
                        if "product_uom_id" in wo._fields and wo.product_uom_id
                        else rounding
                    )
                    if not wo.planned_qty or float_compare(
                        wo.planned_qty, old_qty, precision_rounding=wo_rounding
                    ) == 0:
                        wo.write({"planned_qty": mo.product_qty})

            if mos_to_rebuild:
                mos_to_rebuild._mpc_auto_split_parallel_workorders(create_missing=False)

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
        # Split if we have explicit allowed machines OR if the BoM has parallel operations
        productions = self.filtered(
            lambda mo: mo.mpc_allowed_wc_ids
            or any(op.parallel_mode == 'parallel' for op in mo.bom_id.operation_ids)
        )
        if productions:
            # For new MOs, we don't lock yet so missing WOs can be created from BoM ops
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
                lambda w: (
                    w.operation_id
                    and w.operation_id.parallel_mode == "parallel"
                    and w.state not in ("done", "cancel")
                )
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
        if self.env.context.get("mpc_auto_split_in_progress"):
            return

        productions = self.with_context(mpc_auto_split_in_progress=True)
        for mo in productions:

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
    def _mpc_get_blocked_wc_ids(self, wc_ids):
        """Batch check which workcenters are blocked (maintenance)."""
        if not wc_ids:
            return set()

        workcenters = self.env["mrp.workcenter"].browse(wc_ids)
        blocked_ids = set()

        # 1) Check maintenance_state (standard field if maintenance is installed)
        # We pre-read to avoid N+1 if maintenance is installed
        existing_fields = self.env["mrp.workcenter"]._fields
        if "maintenance_state" in existing_fields:
            for wc_data in workcenters.read(["maintenance_state"]):
                if wc_data.get("maintenance_state") and wc_data["maintenance_state"] not in ("normal", "available"):
                    blocked_ids.add(wc_data["id"])

        # 2) Check for active maintenance requests
        remaining_wc_ids = set(wc_ids) - blocked_ids
        if remaining_wc_ids and "maintenance.request" in self.env.registry:
            maintenance_model = self.env["maintenance.request"].sudo()
            domain = [("workcenter_id", "in", list(remaining_wc_ids))]

            # Dynamic stage check
            if "state" in maintenance_model._fields:
                domain.append(("state", "not in", ["done", "cancel"]))
            elif "stage_id" in maintenance_model._fields:
                stage_field = maintenance_model._fields.get("stage_id")
                stage_model = getattr(stage_field, "comodel_name", False)
                if stage_model and "done" in self.env[stage_model]._fields:
                    domain.append(("stage_id.done", "=", False))

            requests = maintenance_model.search(domain)
            blocked_ids |= set(requests.mapped("workcenter_id.id"))

        return blocked_ids

    def _mpc_is_wc_blocked(self, wc_id):
        """Single check; calls batch method."""
        return wc_id in self._mpc_get_blocked_wc_ids([wc_id])

    def _mpc_remove_blocked_workorders(self):
        """Cancel workorders assigned to blocked workcenters (maintenance)."""
        for mo in self:
            active_wos = mo.workorder_ids.filtered(
                lambda wo: wo.state not in ("done", "cancel") and wo.operation_id
            )
            if not active_wos:
                continue

            wc_ids = active_wos.mapped("workcenter_id.id")
            blocked_wc_ids = self._mpc_get_blocked_wc_ids(wc_ids)
            if not blocked_wc_ids:
                continue

            # Group by operation to ensure we keep at least one WO
            ops = {}
            for wo in active_wos:
                ops.setdefault(wo.operation_id, self.env["mrp.workorder"])
                ops[wo.operation_id] |= wo

            for op_wos in ops.values():
                blocked = op_wos.filtered(lambda wo: wo.workcenter_id.id in blocked_wc_ids)
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
        """Split float qty across workorders using capacity weights, respecting UOM rounding."""
        if not workorders or not total_qty:
            return []

        rounding = self.product_uom_id.rounding or 0.01
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
            base_qty = float_round(total_qty / n, precision_rounding=rounding)
            result_qtys = [base_qty] * n

            # Adjust remainder
            diff = float_round(total_qty - sum(result_qtys), precision_rounding=rounding)
            if not float_is_zero(diff, precision_rounding=rounding):
                result_qtys[0] = float_round(result_qtys[0] + diff, precision_rounding=rounding)
            return list(zip(wo_list, result_qtys))

        ideal = [total_qty * w / total_weight for w in weights]
        # We use floor rounding initially, but with UOM precision
        base = [float_round(x, precision_rounding=rounding, rounding_method="DOWN") for x in ideal]
        remainder = float_round(total_qty - sum(base), precision_rounding=rounding)

        if not float_is_zero(remainder, precision_rounding=rounding):
            # Sort by who lost the most in rounding
            fractions = sorted(
                [(ideal[i] - base[i], i) for i in range(len(wo_list))],
                key=lambda x: x[0],
                reverse=True
            )

            # Distribute remainder by smallest possible increments (rounding)
            idx = 0
            while not float_is_zero(remainder, precision_rounding=rounding) and idx < len(fractions):
                _, i = fractions[idx]
                base[i] = float_round(base[i] + rounding, precision_rounding=rounding)
                remainder = float_round(remainder - rounding, precision_rounding=rounding)
                idx = (idx + 1) % len(fractions)

            # Safety catch: if still a tiny remainder due to math precision
            if not float_is_zero(remainder, precision_rounding=rounding):
                base[0] = float_round(base[0] + remainder, precision_rounding=rounding)

        return list(zip(wo_list, base))

    def _mpc_auto_split_one_mo(self, create_missing=False):
        """Distribute MO quantity across parallel workorders (incremental)."""
        self.ensure_one()

        # Lock the MO row in PostgreSQL to prevent concurrent edits while splitting
        self.env.cr.execute("SELECT id FROM mrp_production WHERE id = %s FOR NO KEY UPDATE", [self.id])

        if create_missing:
            self._mpc_create_parallel_workorders()

        mo_qty = self.product_qty or 0.0
        if mo_qty <= 0:
            return

        rounding = self.product_uom_id.rounding or 0.000001

        parallel_groups = {}
        for wo in self.workorder_ids:
            if wo.state in ("done", "cancel"):
                continue
            op = wo.operation_id
            if not op or op.parallel_mode != "parallel":
                if not wo.planned_qty:
                    wo.with_context(
                        mpc_disable_auto_split=True,
                        mpc_skip_autosplit=True,
                    ).write({"planned_qty": mo_qty})
                continue

            key = op.id
            parallel_groups.setdefault(key, self.env["mrp.workorder"])
            parallel_groups[key] |= wo

        for _op_id, wos in parallel_groups.items():
            wos = wos.sorted("id")
            if not wos:
                continue

            # Calculate total already produced in this parallel group
            total_produced = sum(wos.mapped("qty_produced"))

            # The pool of quantity we can still distribute among these machines
            pool_qty = max(0, mo_qty - total_produced)

            # Distribute the pool based on capacity
            splits = self._mpc_split_qty_by_capacity(pool_qty, wos)

            touched_wos = self.env["mrp.workorder"]
            for wo, split_pool_qty in splits:
                # New planned qty = what it already produced + its share of the remaining pool
                new_planned = float_round(wo.qty_produced + split_pool_qty, precision_rounding=rounding)

                # Update only if changed to avoid unnecessary writes/syncs
                if float_compare(wo.planned_qty, new_planned, precision_rounding=rounding) != 0:
                    wo.with_context(
                        mpc_disable_auto_split=True,
                        mpc_skip_autosplit=True,
                    ).write({"planned_qty": new_planned})
                    touched_wos |= wo

            (touched_wos or wos)._recompute_parallel_siblings()


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
            if wo.state in ("done", "cancel"):
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
            blocked_wc_ids = self._mpc_get_blocked_wc_ids(list(desired_wc_ids))
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
                    to_remove.write({"state": "cancel"})
                    wos -= to_remove

            wos = wos.filtered(lambda wo: wo.exists())
            existing_wc_ids = set(wos.mapped("workcenter_id.id"))
            missing_wc_ids = desired_wc_ids - existing_wc_ids
            if not missing_wc_ids:
                continue

            template = wos[:1] or self.workorder_ids.filtered(
                lambda wo: wo.operation_id == op
            )[:1]
            if not template:
                continue
            template = template[0]

            vals_list = []
            for wc_id in missing_wc_ids:
                vals = {
                    "name": template.name,
                    "production_id": self.id,
                    "workcenter_id": wc_id,
                    "product_uom_id": template.product_uom_id.id,
                    "operation_id": op.id,
                    "state": template.state if template.state not in ("done", "cancel", "progress") else "ready",
                }
                vals_list.append(vals)

            if vals_list:
                Workorder.with_context(
                    mpc_skip_autosplit=True,
                    mpc_skip_duration_recompute=True,
                ).create(vals_list)

    def _mpc_fix_parallel_dependencies(self):
        """
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

        # Before unlinking, capture which WOs are being removed to prevent re-balancing them
        res = super().unlink()

        if productions:
            for mo in productions:
                # Sync allowed machine list to the current set of workcenters
                mo.mpc_allowed_wc_ids = [
                    (6, 0, mo.workorder_ids.filtered(
                        lambda wo: wo.state not in ("done", "cancel")
                    ).mapped("workcenter_id").ids)
                ]
                mo.mpc_lock_parallel_wc = True

                # Trigger incremental re-balancing
                mo._mpc_auto_split_one_mo(create_missing=False)
                mo._mpc_fix_parallel_dependencies()
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
                    allowed_wc_ids |= set(
                        mo.workorder_ids.filtered(
                            lambda wo: wo.state not in ("done", "cancel")
                        ).mapped("workcenter_id").ids
                    )
                    mo.mpc_allowed_wc_ids = [(6, 0, list(allowed_wc_ids))]

                # Trigger re-splitting to distribute quantities to new machines.
                # _mpc_auto_split_one_mo() is intentionally single-record.
                for mo in productions:
                    mo._mpc_auto_split_one_mo(create_missing=False)
                productions._mpc_fix_parallel_dependencies()

        return workorders[0] if single else workorders

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
