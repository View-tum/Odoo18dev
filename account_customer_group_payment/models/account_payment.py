# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    group_payment_memo = fields.Char(string="Group Payment Memo")
