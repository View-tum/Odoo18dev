# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    auto_diff_account_id = fields.Many2one(
        related='company_id.auto_diff_account_id',
        readonly=False,
    )
    auto_diff_label = fields.Char(
        related='company_id.auto_diff_label',
        readonly=False,
    )
    auto_diff_analytic_distribution = fields.Json(
        related='company_id.auto_diff_analytic_distribution',
        readonly=False,
    )
