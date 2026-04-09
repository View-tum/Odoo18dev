from odoo import models, fields


class ResPartner(models.Model):
    _inherit = "res.partner"

    account_note = fields.Text(
        string="Account Note",
        help="(365 custom) ข้อความเพิ่มเติมสำหรับบัญชีลูกค้า",
    )
