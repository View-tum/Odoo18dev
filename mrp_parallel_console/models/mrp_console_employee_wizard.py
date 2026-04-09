# -*- coding: utf-8 -*-

from odoo import api, fields, models


class MrpParallelConsoleEmployeeWizard(models.TransientModel):
    _name = "mrp.parallel.console.employee.wizard"
    _description = "Parallel Console Employees Wizard"

    def _default_workorders(self):
        ids = (
            self.env.context.get("default_workorder_ids")
            or self.env.context.get("active_ids")
            or []
        )
        return self.env["mrp.workorder"].browse(ids)

    workorder_ids = fields.Many2many(
        "mrp.workorder",
        string="Work Orders",
        default=_default_workorders,
    )

    employee_ids = fields.Many2many(
        "hr.employee",
        string="Employees",
        required=True,
        help="Employees to assign to the selected workorders.",
    )

    @api.onchange("workorder_ids")
    def _onchange_workorder_ids(self):
        if not self.workorder_ids:
            ids = (
                self.env.context.get("default_workorder_ids")
                or self.env.context.get("active_ids")
                or []
            )
            self.workorder_ids = [(6, 0, ids)]

    def action_apply(self):
        self.ensure_one()
        if not self.workorder_ids:
            return {"type": "ir.actions.act_window_close"}

        for workorder in self.workorder_ids:
            workorder.action_console_set_employees(self.employee_ids.ids)
        return {"type": "ir.actions.act_window_close"}
