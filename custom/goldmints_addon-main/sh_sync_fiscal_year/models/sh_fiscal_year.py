# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta


class ShFiscalYear(models.Model):
    _name = "sh.fiscal.year"
    _description = "Fiscal Year"
    _order = "date_start, id"

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
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        index=True,
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
        check_company=True,
    )

    @api.constrains("date_start", "date_end")
    def _check_date_range(self):
        for rec in self:
            if rec.date_start and rec.date_end and rec.date_start > rec.date_end:
                raise ValidationError(_("Fiscal year start date must be before or equal to end date."))

    @api.constrains("company_id", "date_start", "date_end")
    def _check_overlap(self):
        for rec in self.filtered(lambda r: r.company_id and r.date_start and r.date_end):
            domain = [
                ("id", "!=", rec.id),
                ("company_id", "=", rec.company_id.id),
                ("date_start", "<=", rec.date_end),
                ("date_end", ">=", rec.date_start),
            ]
            if self.search_count(domain):
                raise ValidationError(
                    _(
                        "Fiscal year %(name)s overlaps another fiscal year in the same company."
                    ) % {"name": rec.display_name}
                )

    def _check_manager_access(self):
        if not self.env.user.has_group("account.group_account_manager"):
            raise UserError(_("Only Accounting Managers can change fiscal years and periods."))

    def _get_default_period_state(self, date_start, date_end, special=False):
        self.ensure_one()
        if special:
            return "draft"
        company = self.company_id or self.env.company
        today = fields.Date.context_today(self)
        if company.sh_only_current_period_open:
            if date_start and date_end and date_start <= today <= date_end:
                return "draft"
            return "done"
        if date_start and date_start > today and company.sh_auto_close_future_periods:
            return "done"
        return "draft"

    def _sync_company_fiscal_lock_date(self):
        period_model = self.env["sh.account.period"]
        for company in self.mapped("company_id"):
            if not company or not company.sh_sync_odoo_lock_dates:
                continue
            latest_closed_period = period_model.search(
                [
                    ("company_id", "=", company.id),
                    ("special", "=", False),
                    ("state", "=", "done"),
                ],
                order="date_end desc, id desc",
                limit=1,
            )
            company.sudo().write({"fiscalyear_lock_date": latest_closed_period.date_end or False})

    def create_period3(self):
        raise UserError(
            _("Quarterly periods are disabled by policy. Use monthly periods to avoid cross-month postings.")
        )

    def create_period(self, interval=1):
        self._check_manager_access()
        if interval != 1:
            raise UserError(_("Only monthly periods are allowed by the current policy."))
        period_obj = self.env["sh.account.period"]
        for rec in self:
            if rec.period_ids:
                raise UserError(
                    _("Periods already exist for fiscal year %s.") % rec.display_name
                )
            ds = rec.date_start
            period_obj.create(
                {
                    "name": "%s %s" % (_("Opening Period"), ds.strftime("%Y")),
                    "code": ds.strftime("00/%Y"),
                    "date_start": ds,
                    "date_end": ds,
                    "special": True,
                    "fiscal_year_id": rec.id,
                    "state": rec._get_default_period_state(ds, ds, special=True),
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
                        "state": rec._get_default_period_state(ds, de),
                    }
                )
                ds = ds + relativedelta(months=interval)
        return True

    def close_fiscal_year_approve(self):
        self._check_manager_access()
        for rec in self:
            if not rec.move_id or rec.move_id.state != "posted":
                raise UserError(
                    _(
                        "In order to close a fiscal year, you must first post the related closing journal entry."
                    )
                )
            rec.period_ids.write({"state": "done"})
            rec.write({"state": "done"})
        self._sync_company_fiscal_lock_date()
        return {"type": "ir.actions.act_window_close"}

    def re_open_fiscal_year_approve(self):
        self._check_manager_access()
        for rec in self:
            if rec.state == "reopen":
                rec.write({"state": "draft"})
                rec.period_ids.write({"state": "draft"})
        self._sync_company_fiscal_lock_date()

    def re_open_fiscal_year(self):
        self._check_manager_access()
        for rec in self:
            if rec.company_id.sh_enable_approval:
                rec.write({"state": "reopen"})
                rec.period_ids.write({"state": "reopen"})
            else:
                rec.write({"state": "draft"})
                rec.period_ids.write({"state": "draft"})
        if any(not rec.company_id.sh_enable_approval for rec in self):
            self._sync_company_fiscal_lock_date()
