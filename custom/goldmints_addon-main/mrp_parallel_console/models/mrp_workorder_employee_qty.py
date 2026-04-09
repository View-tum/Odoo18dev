# -*- coding: utf-8 -*-
from odoo import fields, models


class MrpWorkorderEmployeeQty(models.Model):
    _name = "mrp.workorder.employee.qty"
    _description = "Workorder Employee Quantity Breakdown"
    _order = "id"

    workorder_id = fields.Many2one(
        "mrp.workorder",
        string="Work Order",
        required=True,
        ondelete="cascade",
    )
    employee_id = fields.Many2one(
        "hr.employee",
        string="Employee",
        required=True,
    )
    qty = fields.Float(
        string="Quantity",
        required=True,
        digits="Product Unit of Measure",
        default=0.0,
    )
    company_id = fields.Many2one(
        related="workorder_id.company_id",
        store=True,
        readonly=True,
    )
