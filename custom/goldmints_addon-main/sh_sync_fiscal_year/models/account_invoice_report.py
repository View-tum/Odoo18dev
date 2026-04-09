# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import fields, models


class AccountInvoiceReport(models.Model):
    _inherit = "account.invoice.report"

    period_id = fields.Many2one(
        "sh.account.period",
        string="Period",
    )
    fiscal_year = fields.Many2one(
        "sh.fiscal.year",
        string="Fiscal Year",
    )

    # def _select(self):
    #     return (
    #         super(AccountInvoiceReport, self)._select()
    #         + ", move.period_id as period_id , move.fiscal_year as fiscal_year"
    #     )
