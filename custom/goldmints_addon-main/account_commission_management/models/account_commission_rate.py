from odoo import fields, models, api


class AccountCommissionRate(models.Model):
    _name = "account.commission.rate"
    _description = "Account Commission Rate"
    _order = "value asc"
    _rec_name = "name"

    name = fields.Char(
        string="ชื่อค่าคอมมิชชั่น",
        compute="_compute_name",
        store=True,
        readonly=True,
        help="(365 custom) ชื่อของค่าคอมมิชชั่นที่ใช้ในการแสดงผลในระบบ",
    )
    value = fields.Float(
        string="ค่าคอมมิชชั่น",
        default=0.0,
        help="(365 custom) ค่าคอมมิชชั่นที่ใช้ในการคำนวณค่าคอมมิชชั่นสำหรับบัญชี",
    )

    _sql_constraints = [
        ("rate_value_unique", "unique(value)", "Commission value must be unique."),
        ("value_positive", "CHECK(value >= 0)", "Commission value cannot be negative."),
    ]

    @api.depends("value")
    def _compute_name(self):
        for record in self:
            record.name = str(record.value) + "%"
