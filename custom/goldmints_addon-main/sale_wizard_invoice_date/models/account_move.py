from odoo import models, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model_create_multi
    def create(self, vals_list):
        # จังหวะที่ 1: ดักใส่ข้อมูลตอนกำลังสร้าง
        forced_date = self.env.context.get('force_wizard_invoice_date')
        if forced_date:
            for vals in vals_list:
                vals['invoice_date'] = forced_date
                
        return super(AccountMove, self).create(vals_list)

    def write(self, vals):
        # จังหวะที่ 2: เกราะป้องกัน! 
        # เช็คว่ามี Context ส่งมาจาก Wizard ของเราหรือไม่
        forced_date = self.env.context.get('force_wizard_invoice_date')
        
        # ถ้ามี Wizard กำลังทำงานอยู่ และมีคน/ระบบ พยายามจะเขียนทับ (write) ฟิลด์ invoice_date
        # เราจะบังคับสลับกลับมาเป็นวันที่จาก Wizard ทันที
        if forced_date and 'invoice_date' in vals:
            vals['invoice_date'] = forced_date
            
        return super(AccountMove, self).write(vals)