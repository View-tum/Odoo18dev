from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    document_ref = fields.Char(
        string="เลขที่เอกสาร", help="เลขที่เอกสารอ้างอิงจากระบบเดิม หรือ เลขที่เอกสารภายนอก"
    )
