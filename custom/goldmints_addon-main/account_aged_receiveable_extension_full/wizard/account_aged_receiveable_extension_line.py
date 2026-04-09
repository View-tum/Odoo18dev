# -*- coding: utf-8 -*-
from odoo import models, fields


class AccountAgedReceiveableExtensionLine(models.TransientModel):
    _inherit = "account.aged.receiveable.extension.line"

    extra_days = fields.Integer(string="วันพิเศษ")
    next_run_date = fields.Date(string="วันที่รันถัดไป")
