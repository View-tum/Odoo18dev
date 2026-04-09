# -*- coding: utf-8 -*-
from odoo import models, fields


class AccountPaymentBillingReportLine(models.TransientModel):
    _name = "account.payment.billing.report.line"
    _description = "Payment Billing Report Preview Line"

    report_id = fields.Many2one(
        comodel_name="account.payment.billing.report",
        string="Report",
        ondelete="cascade",
        help="(365 custom) The report this line belongs to.",
    )
    move_id = fields.Many2one(
        comodel_name="account.move",
        string="Invoice",
        help="(365 custom) ใบแจ้งหนี้ที่เกี่ยวข้อง.",
    )
    invoice_name = fields.Char(
        string="หมายเลข Invoice", help="(365 custom) หมายเลขของใบแจ้งหนี้."
    )
    invoice_date = fields.Date(string="วันที่ Invoice", help="(365 custom) วันที่ของใบแจ้งหนี้.")
    due_date = fields.Date(string="วันที่ครบกำหนด", help="(365 custom) วันครบกำหนดชำระ.")
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        help="(365 custom) สกุลเงินของใบแจ้งหนี้.",
    )
    amount_total = fields.Float(
        string="จำนวนเงิน", help="(365 custom) จำนวนเงินรวมของใบแจ้งหนี้."
    )
    sale_name = fields.Char(
        string="พนักงานขาย",
        help="(365 custom) ผู้ดูแลลูกค้าหรือพนักงานขายที่เกี่ยวข้อง.",
    )
    sale_region = fields.Char(string="พื้นที่", help="(365 custom) พื้นที่การขายที่เกี่ยวข้อง.")
    partner_name = fields.Char(string="ชื่อลูกค้า", help="(365 custom) ชื่อลูกค้าที่เกี่ยวข้อง.")
    invoice_summary = fields.Char(
        string="สถานะ",
        help="(365 custom) สรุปสถานะของใบแจ้งหนี้ (เช่น ฝากเก็บ ฝากวางบิล ฯลฯ).",
    )
    route_name = fields.Char(string="สาย", help="(365 custom) สายการจัดส่งของลูกค้า.")
    subregion_name = fields.Char(
        string="เขต",
        help="(365 custom) เขตการจัดส่งของลูกค้า.",
    )
    # sequence = fields.Integer(
    #     string="No.",
    #     help="(365 custom) The sequence number of this line in the report.",
    # )
    partner_code = fields.Char(string="รหัสลูกค้า", help="(365 custom) รหัสลูกค้าที่เกี่ยวข้อง.")


class AccountPaymentBillingReportLine(models.TransientModel):
    _inherit = "account.payment.billing.report.line"

    account_note = fields.Text(
        string="หมายเหตุ", help="(365 custom) หมายเหตุบัญชีจากข้อมูลลูกค้า"
    )
