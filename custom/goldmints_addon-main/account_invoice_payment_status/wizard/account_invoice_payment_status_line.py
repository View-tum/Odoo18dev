# -*- coding: utf-8 -*-
from odoo import models, fields


class AccountInvoicePaymentStatusLine(models.TransientModel):
    _name = "account.invoice.payment.status.line"
    _description = "Account Invoice Payment Status Line"
    _order = "invoice_date desc"

    wizard_id = fields.Many2one(
        comodel_name="account.invoice.payment.status",
        ondelete="cascade",
        help="(365 custom) เชื่อมโยงกับ Wizard หลักเพื่อจัดกลุ่มข้อมูลบรรทัดตามการเรียกดูของผู้ใช้",
    )
    invoice_id = fields.Many2one(
        comodel_name="account.move",
        string="Invoice",
        required=True,
        help="(365 custom) หมายเลขใบแจ้งหนี้ที่เกี่ยวข้องกับบรรทัดนี้",
    )
    user_id = fields.Many2one(
        related="invoice_id.invoice_user_id",
        string="พนักงานขาย",
        store=True,
        help="(365 custom) พนักงานขายที่รับผิดชอบใบแจ้งหนี้นี้",
    )
    ref = fields.Char(
        related="invoice_id.partner_id.ref",
        string="รหัสลูกค้า",
        help="(365 custom) รหัสของลูกค้าที่เกี่ยวข้องกับใบแจ้งหนี้นี้",
    )
    partner_id = fields.Many2one(
        related="invoice_id.partner_id",
        string="ลูกค้า",
        store=True,
        help="(365 custom) ลูกค้าที่เกี่ยวข้องกับใบแจ้งหนี้นี้",
    )
    currency_id = fields.Many2one(
        related="invoice_id.currency_id",
        readonly=True,
        help="(365 custom) เหรียญที่ใช้สำหรับจำนวนเงินในใบแจ้งหนี้",
    )
    invoice_name = fields.Char(
        related="invoice_id.name",
        string="หมายเลข Invoice",
        help="(365 custom) หมายเลขของใบแจ้งหนี้",
    )
    invoice_date = fields.Date(
        related="invoice_id.invoice_date",
        string="วันที่ Invoice",
        help="(365 custom) วันที่ของใบแจ้งหนี้",
    )
    invoice_date_due = fields.Date(
        related="invoice_id.invoice_date_due",
        string="วันที่ครบกำหนด",
        help="(365 custom) วันที่ครบกำหนดชำระของใบแจ้งหนี้",
    )
    amount_total = fields.Monetary(
        related="invoice_id.amount_total",
        string="จำนวนเงินรวม",
        currency_field="currency_id",
        help="(365 custom) จำนวนเงินรวมของใบแจ้งหนี้",
    )
    amount_residual = fields.Monetary(
        related="invoice_id.amount_residual",
        string="จำนวนเงินคงเหลือ",
        currency_field="currency_id",
        help="(365 custom) จำนวนเงินที่ยังไม่ได้ชำระของใบแจ้งหนี้",
    )
    payment_state = fields.Selection(
        related="invoice_id.payment_state",
        string="สถานะการชำระเงิน",
        help="(365 custom) สถานะการชำระเงินของใบแจ้งหนี้ (เช่น ชำระแล้ว, ยังไม่ชำระ, กำลังชำระ, ย้อนกลับ)",
    )
    payment_date = fields.Date(
        related="invoice_id.date",
        string="วันที่ชำระเงิน",
        help="(365 custom) วันที่ชำระเงินล่าสุดของใบแจ้งหนี้",
    )
    statement_date = fields.Date(
        string="วันที่กระทบยอด",
        help="(365 custom) วันที่กระทบยอดจากใบแจ้งหนี้ธนาคาร",
    )
