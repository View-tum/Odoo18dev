# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    auto_diff_account_id = fields.Many2one(
        'account.account',
        string="Default Auto Difference Account",
        check_company=True,
        help="Account used automatically when rounding/bank fee differences occur during payment registration."
    )
    auto_diff_label = fields.Char(
        string="Default Auto Difference Label",
        default="Bank Fee / Difference",
        help="Label applied to the auto-generated multi-deduction line."
    )
    auto_diff_analytic_distribution = fields.Json(
        string="Default Analytic Distribution",
    )
