from odoo import models, fields, api

class AccountBilling(models.Model):
    _inherit = 'account.billing'

    closest_promised_date = fields.Date(
        string='วันนัดชำระ',
        compute='_compute_closest_promised_date',
        store=True
    )

    # เปลี่ยน dependency มาเป็น field ใหม่
    @api.depends('billing_line_ids.billing_schedule_date')
    def _compute_closest_promised_date(self):
        today = fields.Date.context_today(self)
        
        for record in self:
            closest_date = False
            min_diff = float('inf')
            
            for line in record.billing_line_ids:
                # ตรวจสอบจาก field ใหม่
                if line.billing_schedule_date:
                    if line.billing_schedule_date >= today:
                        diff = (line.billing_schedule_date - today).days
                        
                        if diff < min_diff:
                            min_diff = diff
                            closest_date = line.billing_schedule_date
                        
            record.closest_promised_date = closest_date