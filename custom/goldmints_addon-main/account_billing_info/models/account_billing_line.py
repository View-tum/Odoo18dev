from odoo import models, fields, api

class AccountBillingLine(models.Model):
    _inherit = 'account.billing.line'

    # 1. สร้าง Field ใหม่ขึ้นมาเลย เพื่อตัดขาดจาก move_id 100%
    billing_schedule_date = fields.Date(
        string='วันที่นัดชำระ',
        store=True,
        readonly=False
    )

    # 2. ทำงานเวลาผู้ใช้กดเพิ่มบิลด้วยตัวเองในหน้าจอ (UI)
    @api.onchange('move_id', 'billing_id')
    def _onchange_billing_schedule_date(self):
        for line in self:
            if line.billing_id and line.billing_id.partner_id:
                partner = line.billing_id.partner_id
                
                if 'pps_schedule_ids' in partner._fields and partner.pps_schedule_ids:
                    schedule = partner.pps_schedule_ids[0]
                    if schedule.next_run:
                        # ใส่ค่าลงใน Field ใหม่
                        line.billing_schedule_date = schedule.next_run.date()
                        continue
            
            line.billing_schedule_date = False

    # 3. ทำงานเวลาที่ระบบดึงบิลเข้ามาอัตโนมัติ (Backend)
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # เช็คและใส่ค่าลงใน Field ใหม่
            if not vals.get('billing_schedule_date') and vals.get('billing_id'):
                billing = self.env['account.billing'].browse(vals['billing_id'])
                if billing.partner_id and 'pps_schedule_ids' in billing.partner_id._fields and billing.partner_id.pps_schedule_ids:
                    schedule = billing.partner_id.pps_schedule_ids[0]
                    if schedule.next_run:
                        vals['billing_schedule_date'] = schedule.next_run.date()
                        
        return super(AccountBillingLine, self).create(vals_list)