# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class ShAccountPeriod(models.Model):
    _name = "sh.account.period"
    _description = "Fiscal Period"
    _order = "date_start, id"

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
        index=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        related="fiscal_year_id.company_id",
        store=True,
        index=True,
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
    is_current_period = fields.Boolean(
        string="Current Period",
        compute="_compute_is_current_period",
    )

    @api.depends("date_start", "date_end")
    def _compute_is_current_period(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.is_current_period = bool(
                rec.date_start and rec.date_end and rec.date_start <= today <= rec.date_end
            )

    @api.constrains("date_start", "date_end")
    def _check_date_range(self):
        for rec in self:
            if rec.date_start and rec.date_end and rec.date_start > rec.date_end:
                raise ValidationError(_("Period start date must be before or equal to end date."))

    @api.constrains("fiscal_year_id", "date_start", "date_end")
    def _check_inside_fiscal_year(self):
        for rec in self.filtered(lambda r: r.fiscal_year_id and r.date_start and r.date_end):
            fy = rec.fiscal_year_id
            if rec.date_start < fy.date_start or rec.date_end > fy.date_end:
                raise ValidationError(
                    _(
                        "Period %(period)s must stay inside fiscal year %(fiscal)s (%(fy_start)s - %(fy_end)s)."
                    ) % {
                        "period": rec.display_name,
                        "fiscal": fy.display_name,
                        "fy_start": fy.date_start,
                        "fy_end": fy.date_end,
                    }
                )

    @api.constrains("company_id", "date_start", "date_end", "special")
    def _check_period_overlap(self):
        for rec in self.filtered(lambda r: r.company_id and r.date_start and r.date_end):
            domain = [
                ("id", "!=", rec.id),
                ("special", "=", rec.special),
                ("company_id", "=", rec.company_id.id),
                ("date_start", "<=", rec.date_end),
                ("date_end", ">=", rec.date_start),
            ]
            if self.search_count(domain):
                raise ValidationError(
                    _(
                        "Period %(period)s overlaps another %(kind)s period in the same company."
                    ) % {
                        "period": rec.display_name,
                        "kind": _("special") if rec.special else _("regular"),
                    }
                )

    def _check_manager_access(self):
        if not self.env.user.has_group("account.group_account_manager"):
            raise UserError(_("Only Accounting Managers can change fiscal periods."))

    def _sync_company_fiscal_lock_date(self):
        companies = self.mapped("company_id")
        for company in companies:
            if not company or not company.sh_sync_odoo_lock_dates:
                continue
            latest_closed_period = self.search(
                [
                    ("company_id", "=", company.id),
                    ("special", "=", False),
                    ("state", "=", "done"),
                ],
                order="date_end desc, id desc",
                limit=1,
            )
            target_lock_date = latest_closed_period.date_end or False
            if company.fiscalyear_lock_date == target_lock_date:
                continue
            company.sudo().write({"fiscalyear_lock_date": target_lock_date})

    def close_period(self):
        self._check_manager_access()
        for rec in self:
            if rec.company_id.sh_enable_approval:
                rec.write({"state": "waiting"})
            else:
                rec.write({"state": "done"})
        self.filtered(lambda p: p.state == "done")._sync_company_fiscal_lock_date()

    def reopen_period(self):
        self._check_manager_access()
        for rec in self:
            if rec.company_id.sh_enable_approval:
                rec.write({"state": "reopen"})
            else:
                rec.write({"state": "draft"})
        if any(not rec.company_id.sh_enable_approval for rec in self):
            self._sync_company_fiscal_lock_date()

    def close_period_approve(self):
        self._check_manager_access()
        for rec in self:
            rec.write({"state": "done"})
        self._sync_company_fiscal_lock_date()

    def reopen_period_approve(self):
        self._check_manager_access()
        self.write({"state": "draft"})
        self._sync_company_fiscal_lock_date()
