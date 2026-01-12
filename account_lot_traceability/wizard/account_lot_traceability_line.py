from odoo import models, fields


class AccountLotTraceabilityLine(models.TransientModel):
    _name = "account.lot.traceability.line"
    _description = "Account Lot/Serial Traceability Result Line"

    lot_id = fields.Many2one(
        comodel_name="stock.lot",
        string="Lot/Serial",
        readonly=True,
        help="(365 custom) หมายเลขล็อตหรือซีเรียลนัมเบอร์ที่ใช้อ้างอิง",
    )
    customer_id = fields.Many2one(
        comodel_name="res.partner",
        string="Customer",
        readonly=True,
        help="(365 custom) ลูกค้าที่ระบุในใบแจ้งหนี้",
    )
    invoice_id = fields.Many2one(
        comodel_name="account.move",
        string="Invoice",
        readonly=True,
        help="(365 custom) ใบแจ้งหนี้ที่เกี่ยวข้องกับล็อตสินค้านี้",
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product",
        readonly=True,
        help="(365 custom) สินค้าที่ถูกขายในล็อตนี้",
    )
    quantity = fields.Float(
        string="Qty",
        readonly=True,
        help="(365 custom) จำนวนสินค้าที่ระบุในบรรทัดรายการใบแจ้งหนี้",
    )
    amount_total = fields.Monetary(
        string="Amount (Subtotal)",
        currency_field="currency_id",
        readonly=True,
        help="(365 custom) ยอดรวมเป็นเงิน (ก่อนภาษี) ของรายการนี้",
    )
    price_per_unit_calculated = fields.Monetary(
        string="Price/Unit (Calc)",
        currency_field="currency_id",
        readonly=True,
        help="(365 custom) ราคาต่อหน่วยที่คำนวณจากยอดรวมหารด้วยจำนวนสินค้า",
    )
    currency_id = fields.Many2one(
        related="invoice_id.currency_id",
        readonly=True,
        help="(365 custom) สกุลเงินที่ใช้ในเอกสารใบแจ้งหนี้",
    )
    payment_state = fields.Selection(
        related="invoice_id.payment_state",
        string="Payment Status",
        readonly=True,
        help="(365 custom) สถานะการชำระเงินของใบแจ้งหนี้ (เช่น จ่ายแล้ว, ยังไม่จ่าย)",
    )
    invoice_date = fields.Date(
        string="Invoice Date",
        readonly=True,
        help="(365 custom) วันที่ที่ระบุบนใบแจ้งหนี้",
    )
    sale_order_id = fields.Many2one(
        "sale.order",
        string="Source SO",
        readonly=True,
        help="(365 custom) ใบสั่งขายต้นทางที่เชื่อมโยงกับใบแจ้งหนี้นี้",
    )

    def action_open_invoice(self):
        """
        TH: เปิดหน้าฟอร์มใบแจ้งหนี้ที่เกี่ยวข้องเพื่อให้ผู้ใช้ดูรายละเอียดเพิ่มเติม
        EN: Open the related invoice form view to allow users to see more details.
        """
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": self.invoice_id.id,
            "view_mode": "form",
            "target": "current",
        }
