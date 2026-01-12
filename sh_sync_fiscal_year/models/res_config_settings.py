# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    sh_enable_approval = fields.Boolean(
        string="Enable Approval work Flow",
        related="company_id.sh_enable_approval",
        readonly=False,
    )
    sh_restrict_for_close_period = fields.Boolean(
        string="Restrict record creation for Closed Fiscal Period or Closed Fiscal Year",
        related="company_id.sh_restrict_for_close_period",
        readonly=False,
    )

    def update_old_records(self):
        query = """
        UPDATE account_move AS am
        SET period_id = (
            SELECT id
            FROM sh_account_period
            WHERE date_start <= am.date
            AND date_end >= am.date
            LIMIT 1
        ),
        fiscal_year = (
            SELECT fiscal_year_id
            FROM sh_account_period
            WHERE date_start <= am.date
            AND date_end >= am.date
            LIMIT 1
        )
        WHERE (period_id IS NULL OR fiscal_year IS NULL)
        AND am.date IS NOT NULL
        AND am.company_id IN %(company_ids)s;
        """
        self._cr.execute(query, {"company_ids": tuple(self.env.companies.ids)})
        query2 = """
        UPDATE account_move_line AS aml
        SET period_id = (
            SELECT period_id
            FROM account_move
            WHERE id = aml.move_id
        )
        , fiscal_year = (
            SELECT fiscal_year
            FROM account_move
            WHERE id = aml.move_id
        )

        WHERE (period_id IS NULL OR fiscal_year IS NULL)
        AND aml.company_id IN %(company_ids)s;
        """
        self._cr.execute(query2, {"company_ids": tuple(self.env.companies.ids)})

        # for rec in self.env['account.move'].sudo().search(['|', ('period_id', '=', False), ('fiscal_year', '=', False)]):
        #     if rec.date:
        #         period = self.env['sh.account.period'].sudo().search(
        #             [('date_start', '<=', rec.date), ('date_end', '>=', rec.date)], limit=1)
        #         if period:
        #             rec.period_id = period.id
