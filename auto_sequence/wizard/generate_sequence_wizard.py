from odoo import api, fields, models
from dateutil.relativedelta import relativedelta

class GenerateSequenceWizard(models.TransientModel):
    _name = 'generate.sequence.wizard'
    _description = 'Generate Sequence Wizard'

    start_date = fields.Date(string='Start Date', required=True, default=fields.Date.context_today)
    end_date = fields.Date(string='End Date', required=True)

    def action_generate(self):
        self.ensure_one()
        active_id = self.env.context.get('active_id')
        if not active_id:
            return
        
        sequence = self.env['ir.sequence'].browse(active_id)
        
        # Iterate from start month to end month
        current_date = self.start_date.replace(day=1)
        end_date = self.end_date.replace(day=1)
        
        while current_date <= end_date:
            sequence._ensure_month_range(current_date)
            current_date += relativedelta(months=1)
        
        return {'type': 'ir.actions.act_window_close'}
