# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import fields, models, _
from odoo.exceptions import UserError


class CancelEntries(models.TransientModel):
    _name = "cancel.closing.entries"
    _description = "Cancel Closing Entries"

    fiscal_year_id = fields.Many2one("sh.fiscal.year", string="Fiscal Year")

    def cancel_entry(self):
        period_journal = self.fiscal_year_id.move_id.journal_id or False
        period_id = self.fiscal_year_id.move_id.period_id or False

        if not period_journal:
            raise UserError(
                _(
                    "You have to set the 'End  of Year Entries Journal' for this Fiscal Year which is set after generating opening entries from 'Generate Opening Entries'."
                )
            )

        if period_id.state == "done":
            raise UserError(
                _(
                    "You can not cancel closing entries if the 'End of Year Entries Journal' period is closed."
                )
            )

        if self.fiscal_year_id.move_id:
            self._cr.execute(
                "delete from account_move where id = %s",
                (self.fiscal_year_id.move_id.id,),
            )
        return {"type": "ir.actions.act_window_close"}


class CloseFiscalYear(models.TransientModel):
    _name = "close.fiscal.year"
    _description = "Close Fiscal Year"

    fiscal_year_id = fields.Many2one(
        "sh.fiscal.year", string="Fiscal Year to Close")

    def close_fiscal_year(self):
        self.fiscal_year_id._check_manager_access()
        if self.fiscal_year_id.move_id.state != "posted":
            raise UserError(
                _(
                    "In order to close a fiscalyear, you must first post related journal entries."
                )
            )

        if self.fiscal_year_id.company_id.sh_enable_approval:
            self.fiscal_year_id.period_ids.write({"state": "waiting"})
            self.fiscal_year_id.write({"state": "waiting"})

        else:
            self.fiscal_year_id.write({"state": "done"})
            self.fiscal_year_id.period_ids.write({"state": "done"})
            self.fiscal_year_id._sync_company_fiscal_lock_date()

        return {"type": "ir.actions.act_window_close"}
