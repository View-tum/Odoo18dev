# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.modules import module as odoo_module  # type: ignore

_logger = logging.getLogger(__name__)

# If mrp_mps is not installed, skip registering this model/wizard
if not odoo_module.get_module_path("mrp_mps"):
    _logger.debug("mrp_mps not installed: skipping MPS machines wizard models.")
else:

    # ---------------------------------------------------------
    # Wizard: Select machines for MPS line
    # ---------------------------------------------------------
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
                        lambda o: o.parallel_mode == "parallel"
                    ):
                        if op.workcenter_id:
                            machines |= op.workcenter_id
                        machines |= op.parallel_workcenter_ids

            if machines:
                res["mpc_machine_ids"] = [(6, 0, machines.ids)]
            return res

        def action_confirm(self):
            self.ensure_one()
            if not self.schedule_id:
                return {"type": "ir.actions.act_window_close"}

            # Save selected machines to MPS line
            self.schedule_id.mpc_machine_ids = [
                (6, 0, self.mpc_machine_ids.ids)
            ]
            return {"type": "ir.actions.act_window_close"}

    # ---------------------------------------------------------
    # Extend mrp.production.schedule (MPS line)
    # ---------------------------------------------------------
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
                        lambda op: op.parallel_mode == "parallel"
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
            """Auto-fill machines from parallel BOM operations when none are set."""
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
            for op in bom.operation_ids.filtered(lambda o: o.parallel_mode == "parallel"):
                if op.workcenter_id:
                    machines |= op.workcenter_id
                machines |= op.parallel_workcenter_ids
            if machines:
                self.mpc_machine_ids = [(6, 0, machines.ids)]

        def action_replenish(self, auto_confirm=False):
            """Run replenish per line to surface real errors and avoid half-broken cursors."""
            actions = []
            for sched in self:
                sched._mpc_prefill_machines_from_bom()
                with self.env.cr.savepoint():
                    try:
                        actions.append(
                            super(MrpProductionSchedule, sched).action_replenish(
                                auto_confirm
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

    # ---------------------------------------------------------
    # Hook stock.rule ให้ดึงเครื่องจาก MPS ลงใน MO + split ตาม capacity
    # ---------------------------------------------------------
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
                schedule = self.env["mrp.production.schedule"].search([
                    ("product_id", "=", product_id.id),
                    ("company_id", "=", company_id.id),
                ], limit=1)

            if schedule and schedule.exists() and schedule.mpc_machine_ids:
                machine_ids = schedule.mpc_machine_ids.ids
                vals["mpc_allowed_wc_ids"] = [(6, 0, machine_ids)]
                # เปิดให้ logic parallel split ทำงานเต็มที่
                vals["mpc_lock_parallel_wc"] = False
                _logger.debug("Setting MO machines from MPS: %s", machine_ids)
            else:
                _logger.debug("No machines found in schedule")
            return vals

            return mos
