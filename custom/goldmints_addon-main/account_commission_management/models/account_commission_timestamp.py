from odoo import models, fields


class AccountCommissionTimestamp(models.Model):
    _name = "account.commission.timestamp"
    _description = "Account Commission Timestamp Log"
    _order = "create_date desc"

    salesperson_id = fields.Many2one(
        comodel_name="res.users",
        string="พนักงานขาย",
        required=True,
        readonly=True,
        help="(365 cusotm) ผู้ใช้ที่ได้รับค่าคอมมิชชั่น",
    )
    sale_order_name = fields.Char(
        string="ใบสั่งขาย",
        readonly=True,
        help="(365 custom) ชื่อใบสั่งขายที่เกี่ยวข้องกับค่าคอมมิชชั่น",
    )
    invoice_names = fields.Char(
        string="ใบแจ้งหนี้",
        readonly=True,
        help="(365 custom) ชื่อใบแจ้งหนี้ที่เกี่ยวข้องกับค่าคอมมิชชั่น",
    )
    commission_amount = fields.Float(
        string="จำนวนค่าคอมมิชชั่น",
        readonly=True,
        help="(365 custom) จำนวนค่าคอมมิชชั่นที่คำนวณได้",
    )
    log_date = fields.Datetime(
        string="วันที่บันทึก",
        default=fields.Datetime.now,
        readonly=True,
        help="(365 custom) วันที่และเวลาที่บันทึกข้อมูลค่าคอมมิชชั่น",
    )
