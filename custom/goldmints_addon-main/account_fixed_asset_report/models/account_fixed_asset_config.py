from odoo import models, fields, api


class AccountFixedAssetConfig(models.Model):
    _name = "account.fixed.asset.config"
    _description = "Account Fixed Asset Configuration"
    _rec_name = "excel_id"

    excel_id = fields.Selection(
        selection=[
            ("detailed", "รายงานสินทรัพย์ถาวร"),
            ("summary", "รายงานสรุปการเคลื่อนไหวสินทรัพย์"),
        ],
        string="ประเภทการรายงาน Excel",
        default="detailed",
        help="(365 custom) เลือกรายงานที่ต้องการดาวน์โหลด",
    )
    report_id = fields.Many2one(
        comodel_name="jasper.report",
        string="ประเภทการรายงาน Jasper",
        domain=[("model_id.model", "=", "account.fixed.asset.report")],
        help="(365 custom) เลือก Jasper Report template ที่จะถูกเลือกโดยอัตโนมัติ",
    )
    _sql_constraints = [
        (
            "excel_id_uniq",
            "unique(excel_id)",
            "This Excel report type is already configured!",
        )
    ]
