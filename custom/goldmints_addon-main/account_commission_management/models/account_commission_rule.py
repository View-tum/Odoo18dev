from odoo import fields, models, api
from odoo.exceptions import ValidationError


class AccountCommissionRule(models.Model):
    _name = "account.commission.rule"
    _description = "Account Commission Rule"
    _order = "commission_trigger asc"

    commission_trigger = fields.Selection(
        selection=[
            ("invoice_confirmed", "ใบแจ้งหนี้ได้รับการยืนยัน"),
            ("invoice_paid", "ใบแจ้งหนี้ได้รับการชำระบางส่วน"),
            ("fully_paid", "ใบแจ้งหนี้ได้รับการชำระเต็มจำนวน"),
        ],
        string="เงื่อนไขค่าคอมมิชชั่น",
        required=True,
        help="(365 custom) เหตุการณ์ที่เป็นตัวกระตุ้นการคำนวณค่าคอมมิชชั่นสำหรับกฎนี้ เช่น 'ใบแจ้งหนี้ได้รับการยืนยัน', 'ใบแจ้งหนี้ได้รับการชำระบางส่วน', หรือ 'ใบแจ้งหนี้ได้รับการชำระเต็มจำนวน'",
    )

    region_ids = fields.Many2many(
        comodel_name="delivery.sales.region",
        string="สาย",
        help="(365 custom) สายการขายที่เกี่ยวข้องกับกฎนี้สำหรับการคำนวณค่าคอมมิชชั่น",
    )
    rate_id = fields.Many2one(
        "account.commission.rate",
        string="ค่าคอมมิชชั่น",
        help="(365 custom) ค่าคอมมิชชั่นที่ใช้ในการคำนวณค่าคอมมิชชั่นสำหรับกฎนี้",
    )

    _sql_constraints = [
        (
            "commission_trigger_unique",
            "unique(commission_trigger)",
            "เงื่อนไขค่าคอมมิชชั่นต้องไม่ซ้ำกัน",
        ),
    ]

    @api.constrains("region_ids")
    def _check_unique_regions(self):
        for record in self:
            if not record.region_ids:
                continue
            other_rules = self.search([("id", "!=", record.id)])
            used_regions = other_rules.mapped("region_ids")
            duplicates = set(record.region_ids) & set(used_regions)
            if duplicates:
                duplicate_names = ", ".join([r.name for r in duplicates])
                raise ValidationError(
                    f"ไม่สามารถบันทึกได้: สาย '{duplicate_names}' ถูกใช้ในกฎค่าคอมมิชชั่นอื่นแล้ว\n"
                    "เคล็ดลับ: สายการขายสามารถกำหนดให้กับกฎค่าคอมมิชชั่นได้เพียงหนึ่งกฎเท่านั้น"
                )
