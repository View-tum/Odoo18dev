# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import fields, models, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta


class ShFiscalYear(models.Model):
    _name = "sh.fiscal.year"
    _description = "Fiscal Year"

    name = fields.Char(
        "Fiscal Year",
        required="1",
        copy=False,
        readonly=True,
    )
    code = fields.Char(
        "Code",
        required="1",
        copy=False,
        readonly=True,
    )
    date_start = fields.Date(
        "Start Date",
        required=True,
        copy=False,
        readonly=True,
    )
    date_end = fields.Date(
        "End Date",
        required=True,
        copy=False,
        readonly=True,
    )
    period_ids = fields.One2many(
        "sh.account.period",
        "fiscal_year_id",
        string="Periods",
        readonly=True,
    )
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
    move_id = fields.Many2one(
        "account.move",
        string="End of Year Entries Journal",       
    )

    def create_period3(self):
        return self.create_period(3)

    def create_period(self, interval=1):
        period_obj = self.env["sh.account.period"]
        for rec in self:
            ds = rec.date_start
            period_obj.create(
                {
                    "name": "%s %s" % (_("Opening Period"), ds.strftime("%Y")),
                    "code": ds.strftime("00/%Y"),
                    "date_start": ds,
                    "date_end": ds,
                    "special": True,
                    "fiscal_year_id": rec.id,
                }
            )
            while ds < rec.date_end:
                de = ds + relativedelta(months=interval, days=-1)

                if de > rec.date_end:
                    de = rec.date_end

                period_obj.create(
                    {
                        "name": ds.strftime("%m/%Y"),
                        "code": ds.strftime("%m/%Y"),
                        "date_start": ds.strftime("%Y-%m-%d"),
                        "date_end": de.strftime("%Y-%m-%d"),
                        "fiscal_year_id": rec.id,
                    }
                )
                ds = ds + relativedelta(months=interval)
        return True

    def close_fiscal_year_approve(self):
        if self.move_id.state != "posted":
            raise UserError(
                _(
                    "In order to close a fiscalyear, you must first post related journal entries."
                )
            )

        self._cr.execute(
            "UPDATE sh_account_period SET state = %s " "WHERE fiscal_year_id = %s",
            ("done", self.id),
        )
        self._cr.execute(
            "UPDATE sh_fiscal_year " "SET state = %s WHERE id = %s", ("done", self.id)
        )

        return {"type": "ir.actions.act_window_close"}

    def re_open_fiscal_year_approve(self):
        if self.state == "reopen":
            self._cr.execute(
                "UPDATE sh_fiscal_year " "SET state = %s WHERE id = %s",
                ("draft", self.id),
            )
            self._cr.execute(
                "UPDATE sh_account_period SET state = %s " "WHERE fiscal_year_id = %s",
                ("draft", self.id),
            )

    def re_open_fiscal_year(self):
        for rec in self:
            if rec.env.user.company_id.sh_enable_approval:
                rec.write({"state": "reopen"})
                rec.period_ids.write({"state": "reopen"})
            else:
                rec.write({"state": "draft"})
                self.period_ids.write({"state": "draft"})
