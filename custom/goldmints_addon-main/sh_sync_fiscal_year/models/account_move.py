# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"
    _PERIOD_RESTRICTED_WRITE_FIELDS = {
        "date",
        "invoice_date",
        "invoice_date_due",
        "line_ids",
        "invoice_line_ids",
        "journal_id",
        "company_id",
        "partner_id",
        "currency_id",
        "move_type",
        "state",
        "name",
        "ref",
        "period_id",
    }

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
        for rec in self:
            rec.period_id = rec._find_period_for_date(rec.date, rec.company_id)

    def _find_period_for_date(self, accounting_date, company=None):
        self.ensure_one()
        if not accounting_date:
            return self.env["sh.account.period"]
        company = company or self.company_id or self.env.company
        base_domain = [
            ("date_start", "<=", accounting_date),
            ("date_end", ">=", accounting_date),
        ]
        period_model = self.env["sh.account.period"].sudo()
        if company:
            period = period_model.search(base_domain + [("company_id", "=", company.id)], order="date_start desc, id desc", limit=1)
            if period:
                return period
        return period_model.search(base_domain + [("company_id", "=", False)], order="date_start desc, id desc", limit=1)

    @api.model
    def _get_period_for_date_and_company(self, accounting_date, company):
        if not accounting_date:
            return self.env["sh.account.period"]
        base_domain = [
            ("date_start", "<=", accounting_date),
            ("date_end", ">=", accounting_date),
        ]
        period_model = self.env["sh.account.period"].sudo()
        if company:
            period = period_model.search(base_domain + [("company_id", "=", company.id)], order="date_start desc, id desc", limit=1)
            if period:
                return period
        return period_model.search(base_domain + [("company_id", "=", False)], order="date_start desc, id desc", limit=1)

    @api.model
    def _raise_period_restriction_error(self, period, accounting_date, company):
        raise UserError(
            _(
                "You cannot use Accounting Date %(date)s because Fiscal Period %(period)s (%(start)s - %(end)s) in company %(company)s is %(state)s."
            ) % {
                "date": accounting_date,
                "period": period.display_name,
                "start": period.date_start,
                "end": period.date_end,
                "company": company.display_name if company else self.env.company.display_name,
                "state": dict(period._fields["state"].selection).get(period.state, period.state),
            }
        )

    @api.model
    def _precheck_period_policy_for_vals(self, vals, existing_move=None):
        move = existing_move or self.env["account.move"]
        company = self.env["res.company"].browse(vals["company_id"]) if vals.get("company_id") else (move.company_id or self.env.company)
        accounting_date = vals.get("date", move.date if move else False)
        if not accounting_date:
            return
        period = self._get_period_for_date_and_company(accounting_date, company)
        if not period:
            # Allow draft moves with no period for future planning (e.g. assets)
            if vals.get("state", move.state if move else "draft") == "draft":
                return
            raise ValidationError(
                _(
                    "No fiscal period found for Accounting Date %(date)s in company %(company)s."
                ) % {
                    "date": accounting_date,
                    "company": company.display_name if company else self.env.company.display_name,
                }
            )
        if company and company.sh_restrict_for_close_period and period.state in ("done", "reopen"):
            self._raise_period_restriction_error(period, accounting_date, company)

    def _precheck_period_policy_for_write(self, vals):
        if not (set(vals) & self._PERIOD_RESTRICTED_WRITE_FIELDS):
            return
        for rec in self:
            effective_company = self.env["res.company"].browse(vals["company_id"]) if vals.get("company_id") else rec.company_id
            effective_date = vals.get("date", rec.date)
            if not effective_date:
                continue
            period = self._get_period_for_date_and_company(effective_date, effective_company)
            if not period:
                # Allow draft moves with no period for future planning (e.g. assets)
                if vals.get("state", rec.state) == "draft":
                    continue
                raise ValidationError(
                    _(
                        "No fiscal period found for Accounting Date %(date)s in company %(company)s."
                    ) % {
                        "date": effective_date,
                        "company": effective_company.display_name if effective_company else self.env.company.display_name,
                    }
                )
            if effective_company and effective_company.sh_restrict_for_close_period and period.state in ("done", "reopen"):
                self._raise_period_restriction_error(period, effective_date, effective_company)

    @api.constrains("date", "period_id", "company_id")
    def _check_period_matches_accounting_date(self):
        for rec in self.filtered(lambda m: m.date and m.period_id):
            if not (rec.period_id.date_start <= rec.date <= rec.period_id.date_end):
                raise ValidationError(
                    _(
                        "Accounting Date %(date)s must belong to period %(period)s (%(start)s - %(end)s)."
                    ) % {
                        "date": rec.date,
                        "period": rec.period_id.display_name,
                        "start": rec.period_id.date_start,
                        "end": rec.period_id.date_end,
                    }
                )
            if rec.period_id.company_id and rec.company_id and rec.period_id.company_id != rec.company_id:
                raise ValidationError(
                    _(
                        "Period %(period)s belongs to company %(period_company)s but the document belongs to %(move_company)s."
                    ) % {
                        "period": rec.period_id.display_name,
                        "period_company": rec.period_id.company_id.display_name,
                        "move_company": rec.company_id.display_name,
                    }
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._precheck_period_policy_for_vals(vals)
        return super(AccountMove, self).create(vals_list)

    def write(self, vals):
        self._precheck_period_policy_for_write(vals)
        return super(AccountMove, self).write(vals)
