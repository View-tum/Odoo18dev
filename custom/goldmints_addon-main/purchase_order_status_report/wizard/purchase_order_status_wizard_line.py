from odoo import fields, models

class PurchaseOrderStatusReportWizardLine(models.TransientModel):
    _name = "purchase.order.status.report.wizard.line"
    _description = "Purchase Order Status Report Wizard Line"

    wizard_id = fields.Many2one(
        "purchase.order.status.report.wizard", 
        string="Wizard", 
        ondelete="cascade"
    )
    
    # Checkbox แบบติ๊กถูก
    # is_selected = fields.Boolean(string=" ")
    
    # ข้อมูลจากรายงาน QWeb 100%
    order_id = fields.Many2one("purchase.order", string="เลขที่ใบสั่งซื้อ")
    source_document = fields.Char(string="อ้างอิง")
    date_order = fields.Date(string="วันที่สั่งซื้อ")
    expected_arrival = fields.Date(string="วันที่คาดว่าจะมาถึง")
    vendor_id = fields.Many2one("res.partner", string="ผู้ขาย")
    product_id = fields.Many2one("product.product", string="สินค้า")
    qty = fields.Float(string="จำนวน")
    qty_received = fields.Float(string="รับสินค้า/บริการ")
    qty_pending_invoice = fields.Float(string="ค้างรับชำระ")
    uom_id = fields.Many2one("uom.uom", string="หน่วยนับ")
    unit_price = fields.Float(string="ราคาต่อหน่วย")
    subtotal = fields.Float(string="ยอดไม่รวมภาษี")
    
    state = fields.Selection([
        ("draft", "ใบขอเสนอราคา"),
        ("sent", "ส่งใบขอเสนอราคาแล้ว"),
        ("to approve", "รออนุมัติ"),
        ("purchase", "ใบสั่งซื้อ"),
        ("done", "ล็อกแล้ว"),
        ("rejected", "ปฏิเสธ"),
        ("cancel", "ยกเลิก"),
    ], string="สถานะใบสั่งซื้อ")

    invoice_status = fields.Selection([
        ("no", "ยังไม่ตั้งหนี้"),
        ("to invoice", "รอตั้งหนี้"),
        ("invoiced", "ตั้งหนี้ครบแล้ว"),
    ], string="สถานะการตั้งหนี้")
    
    billing_note_status = fields.Selection([
        ("no", "ยังไม่วางบิล"),
        ("draft", "ร่างใบวางบิล"),
        ("partial", "วางบิลบางส่วน"),
        ("fully", "วางบิลครบแล้ว"),
    ], string="สถานะการวางบิล")
    
    
    def action_open_po_new_tab(self):
        self.ensure_one()
        url = f"/web#id={self.order_id.id}&model=purchase.order&view_type=form"
        
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }