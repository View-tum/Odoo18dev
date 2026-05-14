from odoo import models, fields


class AccountCommissionManagementLine(models.TransientModel):
    _name = "account.commission.management.line"
    _description = "Account Commission Management Line"

    account_commission_id = fields.Many2one(
        comodel_name="account.commission.management",
        string="Account Commission Management",
        help="(365 custom) ความสัมพันธ์กับรายงานการจัดการค่าคอมมิชชั่น",
    )
    salesperson_id = fields.Many2one(
        comodel_name="res.users",
        string="พนักงานขาย",
        help="(365 custom) เลือกพนักงานขายเพื่อกรองข้อมูลในรายงาน",
    )
    customer_code = fields.Char(
        string="รหัสลูกค้า", help="(365 custom) แสดงรหัสลูกค้าในรายงาน"
    )
    customer_name = fields.Char(
        string="ลูกค้า",
        help="(365 custom) แสดงชื่อลูกค้าในรายงาน"
    )
    sale_order_name = fields.Char(
        string="ใบสั่งขาย",
        help="(365 custom) แสดงเลขที่ใบสั่งขายในรายงาน"
    )
    invoice_date = fields.Date(
        string="วันที่ใบแจ้งหนี้", help="(365 custom) แสดงวันที่ใบแจ้งหนี้ในรายงาน"
    )
    invoice_name = fields.Char(
        string="เลขที่ใบแจ้งหนี้", help="(365 custom) แสดงเลขที่ใบแจ้งหนี้ในรายงาน"
    )
    credit_note_name = fields.Char(
        string="เลขที่ใบลดหนี้", help="(365 custom) แสดงเลขที่ใบลดหนี้ในรายงาน"
    )
    amount_invoice_total = fields.Float(
        string="ยอดรวมใบแจ้งหนี้", help="(365 custom) แสดงยอดรวมใบแจ้งหนี้ในรายงาน"
    )
    amount_payment_total = fields.Float(
        string="ยอดรวมการชำระเงิน", help="(365 custom) แสดงยอดรวมการชำระเงินในรายงาน"
    )
    amount_credit_note_total = fields.Float(
        string="ยอดรวมใบลดหนี้", help="(365 custom) แสดงยอดรวมใบลดหนี้ในรายงาน"
    )
    amount_commission = fields.Float(
        string="ยอดรวมค่าคอมมิชชั่น", help="(365 custom) แสดงยอดรวมค่าคอมมิชชั่นในรายงาน"
    )
