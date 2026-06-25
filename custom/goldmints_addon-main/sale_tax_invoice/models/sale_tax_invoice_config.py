from odoo import models, fields, api


class SaleTaxInvoiceConfig(models.Model):
    _name = "sale.tax.invoice.config"
    _description = "Sale Tax Invoice Configuration"
    _rec_name = "report_id"
    _order = "sequence"

    sequence = fields.Selection(
        selection=[("1", "1"), ("2", "2")],
        string="ลำดับการพิมพ์",
        default="1",
        required=True,
        help="(365 custom) ระบุ '1' สำหรับการปริ้นครั้งแรก (ปุ่มม่วง) และ '2' สำหรับการปริ้นครั้งที่สอง (ปุ่มเทา)",
    )
    report_id = fields.Many2one(
        comodel_name="jasper.report",
        string="ประเภทการรายงาน Jasper",
        domain=[("model_id.model", "=", "sale.order")],
        required=True,
        help="(365 custom) เลือก Jasper Report template ที่ต้องการกำหนด",
    )
    _sql_constraints = [
        (
            "sequence_uniq",
            "unique(sequence)",
            "ลำดับการพิมพ์นี้ถูกตั้งค่าไปแล้ว!",
        )
    ]
