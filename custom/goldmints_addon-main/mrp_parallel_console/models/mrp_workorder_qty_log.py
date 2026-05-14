# -*- coding: utf-8 -*-
from odoo import fields, models


class MrpWorkorderQtyLog(models.Model):
    _name = "mrp.workorder.qty.log"
    _description = "Workorder Quantity Log"
    _order = "id desc"

    workorder_id = fields.Many2one(
        "mrp.workorder",
        string="Work Order",
        required=True,
        ondelete="cascade",
    )
    log_date = fields.Datetime(
        string="Log Date",
        default=fields.Datetime.now,
        help="Date/time to display for this output entry (typically the workorder end time).",
        index=True,
    )
    qty = fields.Float(string="Quantity", required=True, digits="Product Unit of Measure")
    note = fields.Char(string="Note")
    employee_ids = fields.Many2many(
        "hr.employee",
        string="Employees",
        help="Employees who produced this quantity entry.",
    )
    company_id = fields.Many2one(related="workorder_id.company_id", store=True, readonly=True)

    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.workorder_id.production_id:
                record.workorder_id.production_id._console_sync_qty_producing()
        return records

    def write(self, vals):
        res = super().write(vals)
        if "qty" in vals:
            for record in self:
                if record.workorder_id.production_id:
                    record.workorder_id.production_id._console_sync_qty_producing()
        return res

    def unlink(self):
        productions = self.mapped("workorder_id.production_id")
        res = super().unlink()
        for production in productions:
            production._console_sync_qty_producing()
        return res
