# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    ppc_override = fields.Boolean(
        string="Override Payment Conditions",
        help="(365 custom) If enabled, invoices for partners using this pricelist will use these values.",
    )
    ppc_payment_extra_days = fields.Integer(
        string="จำนวนวันผ่อนผันเพิ่มเติม (+วัน)",
        help="(365 custom) จำนวนวันที่ให้เลื่อนวันครบกำหนดเพิ่มเติมจากวันที่คำนวณได้.",
        default=0,
    )
    ppc_collect_on_day_enabled = fields.Boolean(
        string="ใช้การตัดรอบตามวันที่กำหนด",
        help="(365 custom) เปิดใช้งานเพื่อให้ระบบกำหนดวันครบกำหนดเป็นวันที่เดียวกันของทุกเดือน.",
        default=False,
    )
    ppc_collect_on_day = fields.Integer(
        string="ตัดรอบในวันที่ (1-31)",
        help="(365 custom) ระบุวันที่ต้องการให้ครบกำหนด หากเดือนนั้นไม่มีวันดังกล่าวระบบจะใช้วันสุดท้ายของเดือน.",
        default=0,
    )

    @api.constrains("ppc_collect_on_day", "ppc_collect_on_day_enabled")
    def _check_ppc_collect_on_day(self):
        for pricelist in self:
            if pricelist.ppc_collect_on_day_enabled:
                day = pricelist.ppc_collect_on_day or 0
                if not 1 <= day <= 31:
                    raise ValidationError(_("กรุณากรอกวันที่ตัดรอบระหว่าง 1 ถึง 31"))

    @api.onchange("ppc_collect_on_day_enabled")
    def _onchange_ppc_collect_on_day_enabled(self):
        for record in self:
            if not record.ppc_collect_on_day_enabled:
                record.ppc_collect_on_day = 0