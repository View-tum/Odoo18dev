from odoo import models, api

class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_quotation_send(self):
        action = super().action_quotation_send()

        # action เป็น dict ที่ใช้เปิด wizard mail.compose.message
        ctx = dict(action.get("context", {}))

        # ปุ่ม Send PRO-FORMA Invoice ของคุณส่ง context {'proforma': True, ...} มาอยู่แล้ว
        if ctx.get("proforma"):
            # ตัดค่า default attachments ออก (หลายระบบใช้ key นี้)
            # ctx.pop("default_attachment_ids", None)
            pass
            # บาง custom อาจใช้ default_attachment_ids เป็น commands ก็ยัง pop ได้เหมือนกัน

        action["context"] = ctx
        return action
    
    def _find_mail_template(self):
        # เช็คว่าเป็นการกดปุ่มมาจาก Pro-Forma หรือไม่ (ดูจาก Context)
        if self.env.context.get('proforma'):
            # ให้ Return Email Template ตัวใหม่ที่เพิ่งสร้าง
            template = self.env.ref('custom_sale.email_template_proforma', raise_if_not_found=False)
            
            # ถ้าไม่ได้สร้างผ่าน Code (สร้างผ่านหน้า UI) ให้ใช้วิธี Search หาด้วยชื่อแทน
            if not template:
                template = self.env['mail.template'].search([
                    ('name', '=', 'Sales: Send PRO-FORMA'),
                    ('model', '=', 'sale.order')
                ], limit=1)

            if template:
                return template 

        return super()._find_mail_template()
