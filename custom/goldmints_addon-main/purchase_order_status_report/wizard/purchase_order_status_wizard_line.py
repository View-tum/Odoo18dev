from odoo import fields, models, api

class PurchaseOrderStatusReportWizardLine(models.TransientModel):
    _name = "purchase.order.status.report.wizard.line"
    _description = "Purchase Order Status Report Wizard Line"

    wizard_id = fields.Many2one(
        "purchase.order.status.report.wizard", 
        string="Wizard", 
        ondelete="cascade"
    )
    
    # Checkbox แบบติ๊กถูก
    is_selected = fields.Boolean(string="Select", default=False)
    is_billable = fields.Boolean(string="Is Billable", default=True)
    is_already_billed = fields.Boolean(string="Already Billed", default=False)

    @api.onchange('is_selected')
    def _onchange_is_selected(self):
        # Just to trigger UI refresh for the parent wizard's computed field
        pass
    
    # ข้อมูลจากรายงาน QWeb 100%
    order_id = fields.Many2one("purchase.order", string="เลขที่ใบสั่งซื้อ")
    po_line_id = fields.Many2one("purchase.order.line", string="รายการใบสั่งซื้อ")
    picking_id = fields.Many2one("stock.picking", string="ใบรับสินค้า")
    service_acceptance_id = fields.Many2one("service.acceptance", string="ใบตรวจรับงาน")
    
    source_document = fields.Char(string="อ้างอิง")
    receipt_ref = fields.Char(string="ใบรับสินค้า/บริการ", help="เลขที่ใบรับสินค้า (Picking) หรือ ใบตรวจรับงาน (Service Acceptance)")
    inv_ref = fields.Char(string="เลขที่ใบแจ้งหนี้ (Inv Ref)", help="เลขที่ใบแจ้งหนี้อ้างอิงจากใบรับสินค้าหรือใบตรวจรับงาน")
    date_order = fields.Date(string="วันที่สั่งซื้อ")
    expected_arrival = fields.Date(string="วันที่คาดว่าจะมาถึง")
    vendor_id = fields.Many2one("res.partner", string="ผู้ขาย")
    product_id = fields.Many2one("product.product", string="สินค้า")
    product_display = fields.Char(string="สินค้า (แสดงผล)")
    qty = fields.Float(string="จำนวน")
    qty_received = fields.Float(string="รับสินค้า/บริการ")
    qty_pending_invoice = fields.Float(string="ค้างรับชำระ")
    uom_id = fields.Many2one("uom.uom", string="หน่วยนับ")
    unit_price = fields.Float(string="ราคาต่อหน่วย")
    subtotal = fields.Float(string="ยอดไม่รวมภาษี")
    is_pending = fields.Boolean(string="ค้างรับ")
    is_header = fields.Boolean(string="เป็นบรรทัดหลัก")
    receipt_date = fields.Date(string="วันที่รับสินค้า/บริการ")
    
    @api.model
    def _get_state_selection(self):
        selection = self.env["purchase.order"]._fields["state"].selection
        if callable(selection):
            return selection(self.env["purchase.order"])
        return selection

    state = fields.Selection(
        selection="_get_state_selection",
        string="สถานะใบสั่งซื้อ"
    )

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