# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    group_payment_memo = fields.Char(string="Group Payment Memo")
    company_group_id = fields.Many2one(
        "res.partner",
        string="กลุ่มบริษัท (Company Group)",
        domain="[('is_company_group', '=', True)]",
    )
