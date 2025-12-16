from collections import defaultdict
from math import floor
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# DELETE WORK CENTER WIZARD
# ---------------------------------------------------------


class MrpWorkCenterDeleteWizard(models.TransientModel):
    _name = "mrp.work.center.delete.wizard"
    _description = "Delete Work Center Wizard"

    production_id = fields.Many2one("mrp.production", required=True)
    work_center_line_ids = fields.One2many(
        "mrp.work.center.delete.line", "wizard_id", string="Work Centers"
    )

    @api.model
    def default_get(self, field_list):
        res = super().default_get(field_list)

        production_id = (
            self.env.context.get("active_id")
            or self.env.context.get("default_production_id")
        )
        if production_id:
            production = self.env["mrp.production"].browse(production_id)
            res["production_id"] = production.id

            lines = []
            for wo in production.workorder_ids.exists().filtered(lambda w: w.state != "cancel"):
                base_qty = (
                    getattr(wo, "planned_qty", 0.0)
                    or wo.qty_production
                    or production.product_qty
                )
                lines.append(
                    (
                        0,
                        0,
                        {
                            "workorder_id": wo.id,
                            "work_center_id": wo.workcenter_id.id,
                            "name": wo.name,
                            "qty_to_produce": base_qty,
                            "selected": False,
                        },
                    )
                )
            res["work_center_line_ids"] = lines
        return res

    def action_delete_work_centers(self):
        """Delete selected work orders with same guards as console Remove."""
        self.ensure_one()

        lines = self.work_center_line_ids.filtered("selected")
        if not lines:
            raise UserError("Please select at least one work center to delete.")

        production = self.production_id
        Workorder = self.env["mrp.workorder"].sudo()
        Productivity = self.env["mrp.workcenter.productivity"].sudo()

        wos = lines.mapped("workorder_id").exists()
        if not wos:
            raise UserError("No work orders found for selected lines.")

        # Guards: forbid removing running / produced / timed workorders.
        for wo in wos:
            if wo.state in ("progress", "done", "cancel"):
                raise UserError(
                    "You cannot remove this work order because it is in state %s."
                    % (wo.state,)
                )
            if wo.qty_produced:
                raise UserError(
                    "You cannot remove this work order because some quantity has already been produced."
                )
            if Productivity.search_count([("workorder_id", "=", wo.id)]) > 0:
                raise UserError(
                    "You cannot remove this work order because time tracking entries already exist."
                )

        remaining_wos = production.workorder_ids.exists() - wos
        if not remaining_wos:
            raise UserError(
                "You cannot delete all work centers. At least one must remain."
            )

        wos.unlink()

        remaining_wc_ids = remaining_wos.mapped("workcenter_id").ids
        production.write(
            {
                "mpc_allowed_wc_ids": [(6, 0, remaining_wc_ids)],
                "mpc_lock_parallel_wc": True,
            }
        )
        production.with_context(
            mpc_skip_cleanup=True
        )._mpc_auto_split_parallel_workorders(create_missing=False)
        return {"type": "ir.actions.act_window_close"}


class MrpWorkCenterDeleteLine(models.TransientModel):
    _name = "mrp.work.center.delete.line"
    _description = "Work Center Delete Line"

    wizard_id = fields.Many2one("mrp.work.center.delete.wizard")
    workorder_id = fields.Many2one("mrp.workorder")
    work_center_id = fields.Many2one("mrp.workcenter")
    name = fields.Char()
    qty_to_produce = fields.Float()
    selected = fields.Boolean(default=False)


# ---------------------------------------------------------
# ADD WORK CENTER WIZARD
# ---------------------------------------------------------


class MrpWorkCenterAddWizard(models.TransientModel):
    _name = "mrp.work.center.add.wizard"
    _description = "Add Work Center Wizard"

    production_id = fields.Many2one("mrp.production", required=True)
    # optional operation_id from context เพื่อโฟกัส op เดียว
    operation_id = fields.Many2one("mrp.routing.workcenter", string="Operation")
    work_center_line_ids = fields.One2many(
        "mrp.work.center.add.line", "wizard_id", string="Available Work Centers"
    )

    @api.model
    def default_get(self, field_list):
        """แสดงเฉพาะเครื่องที่ 'ควรมีแต่ยังไม่มี' ตาม parallel config + ให้ user เลือกติ๊ก."""
        res = super().default_get(field_list)

        production_id = (
            self.env.context.get("active_id")
            or self.env.context.get("default_production_id")
            or res.get("production_id")
        )
        operation_id = self.env.context.get("operation_id") or res.get("operation_id")

        if not production_id:
            return res

        production = self.env["mrp.production"].browse(production_id)
        if not production or not production.exists():
            return res

        res["production_id"] = production.id

        WC = self.env["mrp.workcenter"]
        lines = []

        # ถ้ามี operation_id ใน context -> ใช้ op นั้น
        # ไม่งั้นเอาเฉพาะ op ที่ parallel_mode = 'parallel'
        if operation_id:
            operations = self.env["mrp.routing.workcenter"].browse(operation_id)
        else:
            operations = production.bom_id.operation_ids.filtered(
                lambda op: op.parallel_mode == "parallel"
            )
            if not operations:
                operations = (
                    production.workorder_ids.exists()
                    .mapped("operation_id")
                    .filtered(lambda op: op.parallel_mode == "parallel")
                )

        existing_wos = production.workorder_ids.exists().filtered(lambda w: w.state != "cancel")

        if operations:
            res["operation_id"] = operations[0].id

        for op in operations:
            if not op:
                continue

            # เครื่องที่ "ควรมี" = main workcenter + parallel_workcenter_ids
            desired = set()
            if op.workcenter_id:
                desired.add(op.workcenter_id.id)
            desired |= set(op.parallel_workcenter_ids.ids)
            if not desired:
                continue

            # เครื่องที่มี WO ของ op นี้อยู่แล้ว
            existing = set(
                existing_wos.filtered(lambda w, op=op: w.operation_id == op)
                .mapped("workcenter_id")
                .ids
            )

            # เหลือเครื่องที่ "ยังไม่มี WO" ให้เลือกเพิ่ม
            available = desired - existing
            for wc in WC.browse(list(available)):
                lines.append(
                    (
                        0,
                        0,
                        {
                            "operation_id": op.id,
                            "work_center_id": wc.id,
                            "name": f"{op.name} - {wc.name}",
                            "selected": False,  # ให้ user ติ๊กเอง
                        },
                    )
                )

        res["work_center_line_ids"] = lines
        return res

    def action_add_work_centers(self):
        """สร้าง workorders จากบรรทัดที่ติ๊ก selected เท่านั้น + อัปเดต split/dep."""

        self.ensure_one()

        production = self.production_id
        if not production or not production.exists():
            raise UserError("Production is missing or has been deleted.")

        Workorder = self.env["mrp.workorder"]
        WC = self.env["mrp.workcenter"]

        # 1) ใช้เฉพาะบรรทัดที่ user ติ๊ก
        # log รายการ line ทั้งหมดให้เห็น op/wc/selected ก่อนกรอง
        for line in self.work_center_line_ids:
            _logger.info(
                "Add WC wizard line: id=%s op=%s wc=%s selected=%s name=%s",
                line.id,
                line.operation_id.id if line.operation_id else None,
                line.work_center_id.id if line.work_center_id else None,
                line.selected,
                line.name,
            )

        selected_lines = self.work_center_line_ids.filtered("selected")
        if not selected_lines:
            raise UserError(_("Please select at least one work center to add."))

        existing_wos = production.workorder_ids.exists().filtered(lambda w: w.state != "cancel")
        if not existing_wos:
            raise UserError(
                _(
                    "No work orders found for this manufacturing order. "
                    "Plan the MO before adding more work centers."
                )
            )

        _logger.info(
            "Add WC wizard: production=%s existing_wos=%s selected=%s",
            production.id,
            existing_wos.ids,
            [
                (line.operation_id.id, line.work_center_id.id)
                for line in selected_lines
            ],
        )
        for line in selected_lines:
            _logger.info(
                "Add WC wizard selected: id=%s op=%s wc=%s name=%s",
                line.id,
                line.operation_id.id if line.operation_id else None,
                line.work_center_id.id if line.work_center_id else None,
                line.name,
            )

        # WO ตัวแรกของ MO ใช้เป็น template default
        base_template = existing_wos[:1]
        if not base_template:
            raise UserError(_("No base work order found to copy from."))
        default_template = base_template[0]

        created = Workorder.browse()

        # เตรียมคู่ (op, wc) ที่ยังไม่มี โดยเรียงลำดับตาม BOM/existing op
        available_pairs = []
        ops_for_pairs = production.bom_id.operation_ids or existing_wos.mapped(
            "operation_id"
        )
        for op in ops_for_pairs:
            if not op:
                continue
            desired = set(op.parallel_workcenter_ids.ids)
            if op.workcenter_id:
                desired.add(op.workcenter_id.id)
            if not desired:
                continue
            existing = set(
                existing_wos.filtered(lambda w, op=op: w.operation_id == op)
                .mapped("workcenter_id")
                .ids
            )
            for wc_id in sorted(desired - existing):
                available_pairs.append((op, WC.browse(wc_id)))

        # ถ้า payload ของ line ว่าง (op/wc = None) ให้ map ตาม available_pairs
        if all(
            not line.operation_id and not line.work_center_id for line in selected_lines
        ):
            if len(selected_lines) > len(available_pairs):
                raise UserError(_("Not enough available work centers to add."))
            target_pairs = available_pairs[: len(selected_lines)]
        else:
            target_pairs = []
            for line in selected_lines:
                op = line.operation_id or default_template.operation_id
                wc = line.work_center_id
                if op and wc:
                    target_pairs.append((op, wc))

        for op, wc in target_pairs:
            if not wc:
                continue

            # ป้องกันซ้ำ op + wc เดิม
            already = existing_wos.filtered(
                lambda w, op=op, wc=wc: w.operation_id == op and w.workcenter_id == wc
            )
            if already:
                continue

            # template: พยายามหา WO ของ op นี้ก่อน ถ้าไม่มีใช้ default_template
            template = (
                existing_wos.filtered(lambda w, op=op: w.operation_id == op)[:1]
                or base_template
            )[0]

            vals = {
                "name": template.name,
                "production_id": production.id,
                "workcenter_id": wc.id,
                "product_uom_id": template.product_uom_id.id,
                "operation_id": op.id if op else False,
                "qty_production": template.qty_production,
                "planned_qty": template.planned_qty,
                "console_qty": template.console_qty or template.planned_qty,
                # ให้ core workflow จัด state เอง
                "state": "pending",
            }

            # ❌ ไม่ใช้ mpc_skip_autosplit/mpc_skip_cleanup ที่นี่
            new_wo = Workorder.with_context(
                mpc_skip_autosplit=True, mpc_skip_cleanup=True
            ).create(vals)
            created |= new_wo
            _logger.info(
                "Add WC wizard: created WO %s (op=%s, wc=%s)",
                new_wo.id,
                op.id if op else None,
                wc.id,
            )

        if not created:
            # กรณีติ๊กแต่ทั้งหมดซ้ำอยู่แล้ว ก็แค่ปิด popup
            return {"type": "ir.actions.act_window_close"}

        # 2) sync allowed workcenters ให้รวมเครื่องใหม่ด้วย
        all_wc_ids = production.workorder_ids.exists().mapped("workcenter_id").ids
        production.write(
            {
                "mpc_allowed_wc_ids": [(6, 0, all_wc_ids)],
                "mpc_lock_parallel_wc": True,
            }
        )

        # 3) ให้ logic parallel ของ MO ทำงานเต็ม ๆ (แต่ไม่ cleanup เพิ่ม)
        production.with_context(mpc_skip_cleanup=True)._mpc_auto_split_parallel_workorders(
            create_missing=False
        )

        return {"type": "ir.actions.act_window_close"}



class MrpWorkCenterAddLine(models.TransientModel):
    _name = "mrp.work.center.add.line"
    _description = "Work Center Add Line"

    wizard_id = fields.Many2one("mrp.work.center.add.wizard")
    operation_id = fields.Many2one("mrp.routing.workcenter")
    work_center_id = fields.Many2one("mrp.workcenter")
    name = fields.Char()
    selected = fields.Boolean(default=False)


# ---------------------------------------------------------
# ADJUST PLANNED QTY WIZARD
# ---------------------------------------------------------


class MrpWorkCenterAdjustQtyWizard(models.TransientModel):
    _name = "mrp.work.center.adjust.qty.wizard"
    _description = "Adjust Planned Qty Wizard"

    production_id = fields.Many2one("mrp.production", required=True)
    work_center_line_ids = fields.One2many(
        "mrp.work.center.adjust.qty.line", "wizard_id"
    )

    @api.model
    def default_get(self, field_list):
        res = super().default_get(field_list)

        pid = (
            self.env.context.get("active_id")
            or self.env.context.get("default_production_id")
        )
        if pid:
            prod = self.env["mrp.production"].browse(pid)
            res["production_id"] = prod.id

            lines = []
            for wo in prod.workorder_ids.exists().filtered(lambda w: w.state != "cancel"):
                base_qty = (
                    getattr(wo, "planned_qty", 0.0)
                    or wo.qty_production
                    or prod.product_qty
                )
                lines.append(
                    (
                        0,
                        0,
                        {
                            "workorder_id": wo.id,
                            "work_center_id": wo.workcenter_id.id,
                            "name": wo.name,
                            "original_qty": base_qty,
                            "new_qty": base_qty,
                            "locked": False,
                        },
                    )
                )

            res["work_center_line_ids"] = lines
        return res

    def _recompute_distribution(self):
        """Recompute planned quantities based on locks so total = MO qty."""
        for wiz in self:
            prod = wiz.production_id
            if not prod:
                continue
            lines = wiz.work_center_line_ids.filtered(
                lambda l: l.workorder_id.state != "cancel"
            )
            if not lines:
                continue

            target_int = int(round(prod.product_qty or 0.0))

            locked = lines.filtered(
                lambda l: l.locked
                or (
                    l.new_qty is not None
                    and l.original_qty is not None
                    and int(round(l.new_qty)) != int(round(l.original_qty))
                )
            )
            free = lines - locked

            locked_int_total = 0
            for line in locked:
                q_int = int(round(line.new_qty or 0.0))
                line.new_qty = q_int
                locked_int_total += q_int

            if locked_int_total > target_int:
                raise UserError("Locked quantities exceed the MO quantity.")

            remainder = target_int - locked_int_total
            if not free:
                continue

            n_free = len(free)
            if n_free == 1:
                free[0].new_qty = remainder
                continue

            weights = [line.original_qty or 0.0 for line in free]
            total_weight = sum(weights)

            if total_weight <= 0:
                base = int(floor(remainder / n_free))
                for line in free:
                    line.new_qty = base
                rem = remainder - base * n_free
                for line in free[:rem]:
                    line.new_qty += 1
                continue

            ideal = [remainder * w / total_weight for w in weights]
            base_ints = [int(floor(x)) for x in ideal]
            assigned = sum(base_ints)
            rem = remainder - assigned

            for idx, line in enumerate(free):
                line.new_qty = base_ints[idx]

            fractions = [(ideal[i] - base_ints[i], i) for i in range(n_free)]
            fractions.sort(reverse=True)

            idx = 0
            while rem > 0 and fractions:
                _, i = fractions[idx]
                free[i].new_qty += 1
                rem -= 1
                idx = (idx + 1) % len(fractions)

    def action_adjust_quantities(self):
        self.ensure_one()

        self._recompute_distribution()

        for line in self.work_center_line_ids.filtered(lambda l: l.workorder_id.state != "cancel"):
            qty = max(line.new_qty, 0.0)
            wo = line.workorder_id
            if wo and wo.exists():
                wo.write(
                    {
                        "planned_qty": qty,
                        "console_qty": qty,
                        "qty_production": qty,
                    }
                )

        return {"type": "ir.actions.act_window_close"}


class MrpWorkCenterAdjustQtyLine(models.TransientModel):
    _name = "mrp.work.center.adjust.qty.line"
    _description = "Adjust Qty Line"

    wizard_id = fields.Many2one("mrp.work.center.adjust.qty.wizard")
    workorder_id = fields.Many2one("mrp.workorder")
    work_center_id = fields.Many2one("mrp.workcenter")
    name = fields.Char()
    original_qty = fields.Float()
    new_qty = fields.Float()
    locked = fields.Boolean(string="Lock", default=False)

    @api.onchange("new_qty")
    def _onchange_new_qty(self):
        # When user edits qty, lock the line and redistribute others.
        for line in self:
            if line.new_qty is not None:
                line.locked = True
        wizards = self.mapped("wizard_id")
        if wizards:
            wizards._recompute_distribution()

    @api.onchange("locked")
    def _onchange_locked(self):
        wizards = self.mapped("wizard_id")
        if wizards:
            wizards._recompute_distribution()
