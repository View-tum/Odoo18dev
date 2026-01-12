# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import fields, models, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta


class AccountMove(models.Model):
    _inherit = "account.move"

    period_id = fields.Many2one(
        "sh.account.period", string="Period", compute="_compute_get_period", store=True
    )
    fiscal_year = fields.Many2one(
        "sh.fiscal.year",
        string="Fiscal Year",
        related="period_id.fiscal_year_id",
        store=True,
    )

    @api.depends("date")
    def _compute_get_period(self):
        if self:
            for rec in self:
                rec.period_id = False
                if rec.date:
                    period = (
                        self.env["sh.account.period"]
                        .sudo()
                        .search(
                            [
                                ("date_start", "<=", rec.date),
                                ("date_end", ">=", rec.date),
                            ],
                            limit=1,
                        )
                    )
                    if period:
                        rec.period_id = period.id

    @api.model_create_multi
    def create(self, vals_list):
        # OVERRIDE
        res = super(AccountMove, self).create(vals_list)
        for vals in vals_list:
            if "date" in vals:
                period = (
                    self.env["sh.account.period"]
                    .sudo()
                    .search(
                        [
                            ("date_start", "<=", vals["date"]),
                            ("date_end", ">=", vals["date"]),
                        ],
                        limit=1,
                    )
                )

                if self.env.company.sh_restrict_for_close_period and period.state in [
                    "done",
                    "reopen",
                ]:
                    raise UserError(
                        _(
                            "You can not Select Date from Closed Fiscal Period / Closed Fiscal Year."
                        )
                    )
        return res

    def write(self, vals):
        rslt = super(AccountMove, self).write(vals)
        if self:
            for rec in self:
                if (
                    rec.company_id.sh_restrict_for_close_period
                    and rec.period_id.state in ["done", "reopen"]
                ):
                    raise UserError(
                        _(
                            "You can not Select Date from Closed Fiscal Period / Closed Fiscal Year."
                        )
                    )
        return rslt
