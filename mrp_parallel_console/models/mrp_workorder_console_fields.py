# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


PRODUCTIVITY_MODEL = "mrp.workcenter.productivity"
PRODUCTIVITY_LOSS_MODEL = "mrp.workcenter.productivity.loss"
EMPLOYEE_MODEL = "hr.employee"


class MrpWorkorder(models.Model):
    _inherit = "mrp.workorder"

    planned_qty = fields.Float(
        string="Planned Quantity (Parallel)",
        digits="Product Unit of Measure",
        help="Quantity planned for this work order when splitting a "
             "manufacturing order across parallel workcenters.",
    )
    console_qty = fields.Float(
        string="Console Quantity",
        digits="Product Unit of Measure",
        help="Quantity reported through the Parallel Shopfloor console "
             "for this work order.",
    )
    console_date_start = fields.Datetime(
        string="Console Start Time",
        help="Start time coming from the Parallel Shopfloor console.",
    )
    console_date_finished = fields.Datetime(
        string="Console End Time",
        help="End time coming from the Parallel Shopfloor console.",
    )
    employee_ids = fields.Many2many(
        "hr.employee",
        "mrp_workorder_employee_rel",
        "workorder_id",
        "employee_id",
        string="Console Employees",
        help="Employees assigned to this work order via the console.",
    )

    def write(self, vals):
        res = super().write(vals)
        # Fields to monitor for real-time sync
        monitor_fields = {"console_qty", "state", "console_date_start", "console_date_finished", "employee_ids"}
        if any(f in vals for f in monitor_fields):
            for record in self:
                if not record.production_id:
                    continue
                channel = f"mrp_parallel_console.production.{record.production_id.id}"
                changes = {
                    "console_qty": record.console_qty,
                    "state": record.state,
                    "console_date_start": fields.Datetime.to_string(record.console_date_start) if record.console_date_start else False,
                    "console_date_finished": fields.Datetime.to_string(record.console_date_finished) if record.console_date_finished else False,
                    "employee_ids": record.employee_ids.ids,
                    "employee_names": record.employee_ids.mapped("name"),
                }
                self.env["bus.bus"]._sendone(channel, "workorder_update", {
                    "workorder_id": record.id,
                    "changes": changes,
                    "timestamp": fields.Datetime.now().isoformat(),
                })
        return res

    def button_start(self, bypass=False):
        # Odoo 18 passes bypass=True when QC auto-starts a workorder; keep compat
        try:
            res = super().button_start(bypass=bypass)
        except TypeError:
            res = super().button_start()
        # Sync console start time if not set
        for record in self:
            if not record.console_date_start:
                record.console_date_start = fields.Datetime.now()
        return res

    def button_finish(self):
        res = super().button_finish()
        # Sync console end time
        for record in self:
            if not record.console_date_finished:
                record.console_date_finished = fields.Datetime.now()
        return res

    def verify_quality_checks(self):
        """Allow finishing without blocking when console explicitly skips QC check.

        Standard Odoo raises if any quality.check is not pass/fail. We bypass that
        when context mpc_skip_quality_checks is set, letting QC be handled later
        (e.g., at MO close) per console policy.
        """
        if self.env.context.get("mpc_skip_quality_checks"):
            return True
        return super().verify_quality_checks()

    def action_console_set_employees(self, employee_ids):
        """Assign/clear employees without auto-starting timers.

        - If timer is running, open/close productivity lines for added/removed employees.
        """
        employee_model = self.env[EMPLOYEE_MODEL].sudo()
        productivity_model = self.env[PRODUCTIVITY_MODEL].sudo()
        loss_model = self.env[PRODUCTIVITY_LOSS_MODEL].sudo()

        employee_ids = employee_ids or []
        new_emps = employee_model.browse(employee_ids)
        productive_loss = loss_model.search([("loss_type", "=", "productive")], limit=1)
        now = fields.Datetime.now()

        for wo in self:
            old_emps = wo.employee_ids
            to_add = new_emps - old_emps
            to_remove = old_emps - new_emps

            if wo.console_date_start and not wo.console_date_finished:
                if to_remove:
                    self._console_close_productivity_lines(
                        productivity_model, wo, to_remove, now
                    )
                if to_add:
                    self._console_open_productivity_lines(
                        productivity_model, productive_loss, wo, to_add, now
                    )

            wo.employee_ids = [(6, 0, new_emps.ids)]
    def _console_open_productivity_lines(
            self, productivity_model, productive_loss, wo, to_add, now
        ):
            for emp in to_add:
                open_line = productivity_model.search(
                    [
                        ("workorder_id", "=", wo.id),
                        ("employee_id", "=", emp.id),
                        ("date_end", "=", False),
                    ],
                    limit=1,
                )
                if open_line:
                    continue

                vals = {
                    "workorder_id": wo.id,
                    "employee_id": emp.id,
                    "workcenter_id": wo.workcenter_id.id,
                    "date_start": now,
                    "description": "Started from Parallel Console",
                }
                if productive_loss:
                    vals["loss_id"] = productive_loss.id
                productivity_model.create(vals)
    def _console_close_productivity_lines(
        self, productivity_model, wo, to_remove, now
    ):
        if not to_remove:
            return
        lines_to_close = productivity_model.search(
            [
                ("workorder_id", "=", wo.id),
                ("employee_id", "in", to_remove.ids),
                ("date_end", "=", False),
            ]
        )
        lines_to_close.write({"date_end": now})

    def _console_update_state_and_time(self, wo, new_emps, now):
        if not new_emps:
            return
        console_updates = {}
        if wo.state == "ready":
            console_updates["state"] = "progress"
        if not wo.console_date_start or wo.console_date_finished:
            console_updates.update(
                {
                    "console_date_start": now,
                    "console_date_finished": False,
                }
            )
        if console_updates:
            wo.write(console_updates)

    def action_console_start_timer(self):
        productivity_model = self.env[PRODUCTIVITY_MODEL].sudo()
        loss_model = self.env[PRODUCTIVITY_LOSS_MODEL].sudo()
        productive_loss = loss_model.search(
            [("loss_type", "=", "productive")],
            limit=1,
        )

        now = fields.Datetime.now()
        for wo in self:
            employees = wo.employee_ids
            if employees:
                self._console_open_productivity_lines(
                    productivity_model,
                    productive_loss,
                    wo,
                    employees,
                    now,
                )
            updates = {}
            if wo.state == "ready":
                updates["state"] = "progress"
            if not wo.console_date_start or wo.console_date_finished:
                updates.update(
                    {
                        "console_date_start": now,
                        "console_date_finished": False,
                    }
                )
            if updates:
                wo.write(updates)
        return now

    def action_console_stop_timer(self):
        productivity_model = self.env[PRODUCTIVITY_MODEL].sudo()

        now = fields.Datetime.now()
        for wo in self:
            employees = wo.employee_ids
            if employees:
                self._console_close_productivity_lines(
                    productivity_model,
                    wo,
                    employees,
                    now,
                )

            # Safety: close any open productivity/time lines tied to this WO even if employees were removed.
            open_lines = productivity_model.search(
                [
                    ("workorder_id", "=", wo.id),
                    ("date_end", "=", False),
                ]
            )
            if open_lines:
                open_lines.write({"date_end": now})

            updates = {
                "console_date_finished": now,
            }
            if not wo.console_date_start:
                updates["console_date_start"] = now
            if wo.state == "progress":
                updates["state"] = "ready"
            wo.write(updates)
        return now

    def button_pending(self):
        res = super().button_pending()
        for record in self:
            if not record.production_id:
                continue
            channel = f"mrp_parallel_console.production.{record.production_id.id}"
            changes = {
                "state": record.state,
                "console_date_start": fields.Datetime.to_string(record.console_date_start) if record.console_date_start else False,
                "console_date_finished": fields.Datetime.to_string(record.console_date_finished) if record.console_date_finished else False,
            }
            self.env["bus.bus"]._sendone(channel, "workorder_update", {
                "workorder_id": record.id,
                "changes": changes,
                "timestamp": fields.Datetime.now().isoformat(),
            })
        return res

    def button_unblock(self):
        res = super().button_unblock()
        for record in self:
            if not record.production_id:
                continue
            channel = f"mrp_parallel_console.production.{record.production_id.id}"
            changes = {
                "state": record.state,
                "console_date_start": fields.Datetime.to_string(record.console_date_start) if record.console_date_start else False,
                "console_date_finished": fields.Datetime.to_string(record.console_date_finished) if record.console_date_finished else False,
            }
            self.env["bus.bus"]._sendone(channel, "workorder_update", {
                "workorder_id": record.id,
                "changes": changes,
                "timestamp": fields.Datetime.now().isoformat(),
            })
        return res
