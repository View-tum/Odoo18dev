from odoo import models, fields, api

class CreateBillWizard(models.TransientModel):
    _name = 'create.bill.wizard'
    _description = 'Wizard for creating bills from PO'

    purchase_id = fields.Many2one('purchase.order', string="Current PO", readonly=True)
    billing_note_id = fields.Many2one('vendor.billing.note', string="Billing Note", readonly=True)
    
    # ฟิลด์สำหรับโชว์ข้อความเตือนว่ามี PO อะไรบ้าง
    po_names = fields.Char(string="Included POs", compute="_compute_po_names")
    
    # ตัวเลือกให้ User กด
    create_type = fields.Selection([
        ('specific', 'สร้าง Vendor Bill เฉพาะรายการนี้ใบเดียว'),
        ('all', 'สร้าง Vendor Bill ให้ทุก PO ที่อยู่ในใบวางบิลนี้พร้อมกัน')
    ], string="รูปแบบการสร้างบิล", default='specific', required=True)

    @api.depends('billing_note_id')
    def _compute_po_names(self):
        for wiz in self:
            if wiz.billing_note_id:
                wiz.po_names = ', '.join(wiz.billing_note_id.purchase_ids.mapped('name'))
            else:
                wiz.po_names = ''

    def action_confirm(self):
        self.ensure_one()
        # เช็คตัวเลือกของ User แล้วส่ง Context ลับไปให้ Billing Note ทำงาน
        if self.create_type == 'specific':
            return self.billing_note_id.with_context(bill_only_po_id=self.purchase_id.id).action_create_bill()
        else:
            return self.billing_note_id.action_create_bill()