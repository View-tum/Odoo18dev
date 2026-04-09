# mrp_machine_report_wizard_line.py
from odoo import models, fields

class MrpMachineReportWizardLine(models.TransientModel):
    _name = 'mrp.machine.report.wizard.line'
    _description = 'MRP Machine Report Wizard Line'

    wizard_id = fields.Many2one(
        'mrp.machine.report.wizard',
        ondelete='cascade',
        index=True
    )

    machine_id = fields.Many2one('mrp.workcenter')
    machine_name = fields.Char()

    workorder_id = fields.Many2one('mrp.workorder')
    operation_name = fields.Char()

    date_start = fields.Datetime()
    date_finished = fields.Datetime()
    duration_minutes = fields.Float()
    workorder_state = fields.Char()

    mo_name = fields.Char()
    product_name = fields.Char()
    factory_type = fields.Char()

    bom_code = fields.Char()
    lot_name = fields.Char()

    qty_produced = fields.Float()
    good_qty = fields.Float()
    scrap_qty = fields.Float()
