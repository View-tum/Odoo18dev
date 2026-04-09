# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import fields, models


class ShAccountPeriod(models.Model):
    _name = "sh.account.period"
    _description = "Fiscal Period"

    name = fields.Char(
        "Period Name",
        required="1",
        copy=False,
        readonly=True,
    )
    code = fields.Char(
        "Code", copy=False, readonly=True
    )
    date_start = fields.Date(
        "Start of Period",
        required=True,
        copy=False,
        readonly=True,
    )
    date_end = fields.Date(
        "End of Period",
        required=True,
        copy=False,
        readonly=True,
    )
    fiscal_year_id = fields.Many2one(
        "sh.fiscal.year",
        string="Fiscal Year",
        readonly=True,
    )
    special = fields.Boolean(
        "Opening/Closing Period", readonly=True)
    state = fields.Selection(
        [
            ("draft", "Open"),
            ("waiting", "Waiting for Approval"),
            ("done", "Closed"),
            ("reopen", "Waiting for Re-Open Approval"),
        ],
        string="State",
        default="draft",
    )

    def close_period(self):
        for rec in self:
            if rec.env.user.company_id.sh_enable_approval:
                rec.write({"state": "waiting"})
            else:
                rec.write({"state": "done"})

    def reopen_period(self):
        if self.env.user.company_id.sh_enable_approval:
            self.write({"state": "reopen"})
        else:
            self.write({"state": "draft"})

    def close_period_approve(self):
        for rec in self:
            rec.write({"state": "done"})

    def reopen_period_approve(self):
        self.write({"state": "draft"})
