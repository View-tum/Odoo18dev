# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    period_id = fields.Many2one(
        "sh.account.period", string="Period", related="move_id.period_id", store=True
    )
    fiscal_year = fields.Many2one(
        "sh.fiscal.year",
        string="Fiscal Year",
        related="period_id.fiscal_year_id",
        store=True,
    )

    def sh_compute_balance(self):
        for line in self:
            line.balance = line.debit - line.credit
