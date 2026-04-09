# -*- coding: utf-8 -*-
from odoo import models, fields


class AccountAgedReceiveableExtensionLine(models.TransientModel):
    _name = "account.aged.receiveable.extension.line"
    _description = "Aged Receivable Report Line"
    _order = "days_overdue desc, invoice_date desc"

    wizard_id = fields.Many2one(
        "account.aged.receiveable.extension", string="Wizard", ondelete="cascade"
    )
    invoice_id = fields.Many2one("account.move", string="ใบแจ้งหนี้")
    sale_order_id = fields.Many2one("sale.order", string="ใบสั่งขาย")
    partner_ref = fields.Char(string="รหัสลูกค้า")
    partner_id = fields.Many2one("res.partner", string="ลูกค้า")
    salesperson_id = fields.Many2one("res.users", string="พนักงานขาย")
    invoice_date = fields.Date(string="วันที่ใบแจ้งหนี้")
    date_maturity = fields.Date(string="วันที่ครบกำหนดชำระ")
    invoice_currency_id = fields.Many2one("res.currency", string="สกุลเงินใบแจ้งหนี้")
    payment_term_id = fields.Many2one("account.payment.term", string="เงื่อนไขการชำระเงิน")
    amount_residual = fields.Monetary(string="ยอดคงเหลือ")
    currency_id = fields.Many2one("res.currency", string="สกุลเงิน")
    days_overdue = fields.Integer(string="จำนวนวันเกินกำหนด")
    amount_not_due = fields.Monetary(string="ยอดที่ยังไม่ถึงกำหนดชำระ")
    amount_1_30 = fields.Monetary(string="1-30 วัน")
    amount_31_60 = fields.Monetary(string="31-60 วัน")
    amount_61_90 = fields.Monetary(string="61-90 วัน")
    amount_over_90 = fields.Monetary(string="เกิน 90 วัน")
