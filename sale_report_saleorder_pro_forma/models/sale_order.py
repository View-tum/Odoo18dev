from odoo import models

class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_quotation_send(self):
        action = super().action_quotation_send()

        # action เป็น dict ที่ใช้เปิด wizard mail.compose.message
        ctx = dict(action.get("context", {}))

        # ปุ่ม Send PRO-FORMA Invoice ของคุณส่ง context {'proforma': True, ...} มาอยู่แล้ว
        if ctx.get("proforma"):
            # ตัดค่า default attachments ออก (หลายระบบใช้ key นี้)
            ctx.pop("default_attachment_ids", None)
            # บาง custom อาจใช้ default_attachment_ids เป็น commands ก็ยัง pop ได้เหมือนกัน

        action["context"] = ctx
        return action
