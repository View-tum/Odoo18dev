# -*- coding: utf-8 -*-

from odoo import api, models, _
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = "res.partner"

    TH_RECEIVABLE_CODE = "113001"
    TH_PAYABLE_CODE = "212001"
    RECEIVABLE_CODE = "113002"
    PAYABLE_CODE = "212002"

    @api.model
    def _get_company_for_partner(self, vals):
        company_id = vals.get("company_id") or self.env.context.get("default_company_id")
        if company_id:
            company = self.env["res.company"].browse(company_id)
            if company:
                return company
        return self.env.company

    @api.model
    def _find_account_by_code(self, code, company):
        company = company or self.env.company
        Account = (
            self.env["account.account"]
            .with_company(company)
            .with_context(allowed_company_ids=[company.id])
        )
        # company_ids is the multi-company field in account.account (company_id is not present)
        return Account.search(
            [
                ("code", "=", code),
                ("company_ids", "in", company.id),
            ],
            limit=1,
        )

    @api.model
    def _get_account_codes(self, company, country_id=None):
        country = None
        if country_id:
            country = self.env["res.country"].browse(country_id)
        elif self.env.context.get("default_country_id"):
            country = self.env["res.country"].browse(self.env.context["default_country_id"])
        elif company.country_id:
            country = company.country_id

        if country and country.code == "TH":
            return self.TH_RECEIVABLE_CODE, self.TH_PAYABLE_CODE
        return self.RECEIVABLE_CODE, self.PAYABLE_CODE

    @api.model
    def _get_target_accounts(self, company, country_id=None):
        receivable_code, payable_code = self._get_account_codes(company, country_id)
        receivable = self._find_account_by_code(receivable_code, company)
        payable = self._find_account_by_code(payable_code, company)
        missing = []

        if not receivable:
            missing.append(receivable_code)
        if not payable:
            missing.append(payable_code)

        if missing:
            raise UserError(
                _("Default accounts %s are not available in company %s.")
                % (", ".join(missing), company.display_name)
            )
        return receivable, payable

    @api.model
    def _prepare_default_accounts(self, vals, company):
        if vals.get("parent_id"):
            return vals

        receivable, payable = self._get_target_accounts(company, vals.get("country_id"))
        vals = dict(vals)
        vals.setdefault("property_account_receivable_id", receivable.id)
        vals.setdefault("property_account_payable_id", payable.id)
        return vals

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        parent_id = res.get("parent_id") or self.env.context.get("default_parent_id")
        if parent_id:
            return res

        company = self._get_company_for_partner(res)
        country_id = res.get("country_id") or self.env.context.get("default_country_id")
        receivable, payable = self.with_company(company)._get_target_accounts(company, country_id)
        res["property_account_receivable_id"] = receivable.id
        res["property_account_payable_id"] = payable.id
        return res

    @api.onchange("country_id")
    def _onchange_country_set_accounts(self):
        for partner in self:
            # Do not override child contacts or saved partners; only adjust new commercial entities
            if partner.parent_id or partner.id:
                continue

            company = partner._get_company_for_partner(
                {"company_id": partner.company_id.id if partner.company_id else False}
            )
            country_id = partner.country_id.id if partner.country_id else False
            try:
                receivable, payable = partner.with_company(company)._get_target_accounts(
                    company, country_id
                )
            except UserError as error:
                partner.property_account_receivable_id = False
                partner.property_account_payable_id = False
                return {
                    "warning": {
                        "title": _("Missing Accounts"),
                        "message": error.name,
                    }
                }

            partner.property_account_receivable_id = receivable
            partner.property_account_payable_id = payable

    @api.model
    def create(self, vals_list):
        if isinstance(vals_list, list):
            partners = self.env["res.partner"]
            for vals in vals_list:
                company = self._get_company_for_partner(vals)
                prepared_vals = self.with_company(company)._prepare_default_accounts(vals, company)
                partners |= super(ResPartner, self.with_company(company)).create(prepared_vals)
            return partners

        company = self._get_company_for_partner(vals_list)
        prepared_vals = self.with_company(company)._prepare_default_accounts(vals_list, company)
        return super(ResPartner, self.with_company(company)).create(prepared_vals)
