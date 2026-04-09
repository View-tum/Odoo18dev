from odoo import models

class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    def _prepare_default_reversal(self, move):
        # ดึงค่าพื้นฐานที่ Odoo จะเตรียมไว้สร้าง Credit Note
        reverse_vals = super()._prepare_default_reversal(move)
        
        # ถ่ายทอดกรรมพันธุ์ (เลขใบวางบิล) จาก Vendor Bill ต้นทาง ไปยัง Credit Note ใบใหม่
        if move.vendor_billing_note_id:
            reverse_vals['vendor_billing_note_id'] = move.vendor_billing_note_id.id
            
        return reverse_vals