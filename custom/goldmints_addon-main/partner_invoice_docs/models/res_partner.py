# partner_invoice_docs/models/res_partner.py
from odoo import models, fields


class ResPartner(models.Model):
    _inherit = "res.partner"

    # Field สำหรับกรอกข้อความทั่วไป
    inv_doc_description = fields.Text(
        string="รายละเอียดเอกสาร", help="(365 custom) ระบุรายละเอียดเพิ่มเติมเกี่ยวกับเอกสาร"
    )

    # ปรับเป็น Integer เพื่อระบุจำนวน (Default คือ 0)
    inv_doc_white = fields.Integer(
        string="สำเนาสีขาว (ใบ)", default=0, help="(365 custom) จำนวนสำเนาสีขาวของเอกสาร"
    )
    inv_doc_yellow = fields.Integer(
        string="สำเนาสีเหลือง (ใบ)",
        default=0,
        help="(365 custom) จำนวนสำเนาสีเหลืองของเอกสาร",
    )
    inv_doc_pink = fields.Integer(
        string="สำเนาสีชมพู (ใบ)", default=0, help="(365 custom) จำนวนสำเนาสีชมพูของเอกสาร"
    )
    inv_doc_po = fields.Integer(
        string="ใบสั่งซื้อ (PO) (ใบ)", default=0, help="(365 custom) จำนวนใบสั่งซื้อของเอกสาร"
    )

    # Field สำหรับหมายเหตุและการเรียงเอกสาร
    inv_doc_sorting_note = fields.Text(
        string="หมายเหตุ/การเรียงเอกสาร",
        help="(365 custom) ระบุวิธีการเรียงเอกสารหรือหมายเหตุเพิ่มเติม",
    )
