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
    sh_only_current_period_open = fields.Boolean(
        string="Open Current Period Only",
        related="company_id.sh_only_current_period_open",
        readonly=False,
    )
    sh_auto_close_future_periods = fields.Boolean(
        string="Auto Close Future Periods",
        related="company_id.sh_auto_close_future_periods",
        readonly=False,
    )
    sh_sync_odoo_lock_dates = fields.Boolean(
        string="Sync Odoo Global Lock Date from Closed Periods",
        related="company_id.sh_sync_odoo_lock_dates",
        readonly=False,
    )

    def update_old_records(self):
        # Backfill by company to avoid assigning a period from another company.
        query = """
        UPDATE account_move AS am
        SET period_id = period_map.period_id,
            fiscal_year = period_map.fiscal_year_id
        FROM LATERAL (
            SELECT sp.id AS period_id, sp.fiscal_year_id
            FROM sh_account_period sp
            WHERE sp.date_start <= am.date
              AND sp.date_end >= am.date
              AND (sp.company_id = am.company_id OR sp.company_id IS NULL)
            ORDER BY
                CASE WHEN sp.company_id = am.company_id THEN 0 ELSE 1 END,
                sp.date_start DESC,
                sp.id DESC
            LIMIT 1
        ) AS period_map
        WHERE (am.period_id IS NULL OR am.fiscal_year IS NULL)
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
