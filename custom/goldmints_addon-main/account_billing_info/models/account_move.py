from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    billing_schedule_date = fields.Date(
        string="วันที่นัดชำระ",
        store=True,
        readonly=False
    )
