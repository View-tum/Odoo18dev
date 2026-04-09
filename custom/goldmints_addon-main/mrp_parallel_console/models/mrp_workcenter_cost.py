# -*- coding: utf-8 -*-
from odoo import fields, models


class MrpWorkcenter(models.Model):
    _inherit = "mrp.workcenter"

    mpc_labor_cost = fields.Monetary(
        string="Parallel Labor Cost / Hour",
        currency_field="currency_id",
        related="employee_costs_hour",
        readonly=False,
        help="Deprecated alias. Edit the standard 'Cost per hour (per employee)' field instead.",
    )
    mpc_require_employee_production = fields.Boolean(
        string="Require Employee Production Input",
        default=False,
        help="If enabled, the system will require production quantities per employee before finishing the job.",
    )
