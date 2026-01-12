from collections import defaultdict
from itertools import groupby
from dateutil.relativedelta import relativedelta

from odoo import models, fields, _, api, Command
from odoo.exceptions import UserError
from odoo.tools import SQL
from odoo.addons.account_accountant.models.account_move import DEFERRED_DATE_MIN, DEFERRED_DATE_MAX


class DeferredReportCustomHandler(models.AbstractModel):
    _inherit = 'account.deferred.report.handler'

    @api.model
    def _get_select(self, options):
        res = super()._get_select(options)
        res.append(SQL("account_move_line.deferred_journal_id AS deferred_journal_id"))
        res.append(SQL("account_move_line.deferred_account_id AS deferred_account_id"))
        return res

    def action_generate_entry(self, options):
        date_from = fields.Date.to_date(DEFERRED_DATE_MIN)
        date_to = fields.Date.from_string(options['date']['date_to'])
        
        # Original validation logic
        import calendar
        if date_to.day != calendar.monthrange(date_to.year, date_to.month)[1]:
            raise UserError(_("You cannot generate entries for a period that does not end at the end of the month."))

        report = self.env["account.report"].browse(options["report_id"])
        options['all_entries'] = False
        self.env['account.move.line'].flush_model()
        lines = self._get_lines(report, options, filter_already_generated=True)
        
        if not lines:
            raise UserError(_("No entry to generate."))

        lines_by_journal = defaultdict(list)
        company = self.env.company
        deferred_type = self._get_deferred_report_type()
        
        default_journal = company.deferred_expense_journal_id if deferred_type == 'expense' else company.deferred_revenue_journal_id
        
        # Group lines by journal
        for line in lines:
            journal_id = line.get('deferred_journal_id') or default_journal.id
            if not journal_id:
                 raise UserError(_("Please set the deferred journal in the accounting settings or on the line."))
            lines_by_journal[journal_id].append(line)

        new_deferred_moves = self.env['account.move']
        
        for journal_id, journal_lines in lines_by_journal.items():
            journal = self.env['account.journal'].browse(journal_id)
            if company._get_violated_lock_dates(date_to, False, journal):
                 raise UserError(_("You cannot generate entries for a period that is locked."))

            lines_by_account = defaultdict(list)
            default_account = company.deferred_expense_account_id if deferred_type == 'expense' else company.deferred_revenue_account_id
            
            # Group lines by account
            for line in journal_lines:
                account_id = line.get('deferred_account_id') or default_account.id
                if not account_id:
                    raise UserError(_("Please set the deferred account in the accounting settings or on the line."))
                lines_by_account[account_id].append(line)
            
            move_lines_vals = []
            all_original_move_ids = set()
            
            deferral_entry_period = self.env['account.report']._get_dates_period(date_from, date_to, 'range', period_type='month')
            ref = _("Grouped Deferral Entry of %s", deferral_entry_period['string'])
            
            for account_id, account_lines in lines_by_account.items():
                 deferred_account = self.env['account.account'].browse(account_id)
                 generated_lines, original_move_ids = self._get_deferred_lines(
                     account_lines, 
                     deferred_account, 
                     (date_from, date_to, 'current'), 
                     deferred_type == 'expense', 
                     ref
                 )
                 move_lines_vals.extend(generated_lines)
                 all_original_move_ids.update(original_move_ids)

            if not move_lines_vals:
                continue

            deferred_move = self.env['account.move'].with_context(skip_account_deprecation_check=True).create({
                'move_type': 'entry',
                'deferred_original_move_ids': [Command.set(list(all_original_move_ids))],
                'journal_id': journal_id,
                'date': date_to,
                'auto_post': 'at_date',
                'ref': ref,
            })
            deferred_move.write({'line_ids': move_lines_vals})
            
            ref_rev = _("Reversal of Grouped Deferral Entry of %s", deferral_entry_period['string'])
            reverse_move = deferred_move._reverse_moves()
            reverse_move.write({
                'date': deferred_move.date + relativedelta(days=1),
                'ref': ref_rev,
            })
            reverse_move.line_ids.name = ref_rev
            
            pair_moves = deferred_move + reverse_move
            new_deferred_moves += pair_moves
            
            self.env.cr.execute_values("""
                INSERT INTO account_move_deferred_rel(original_move_id, deferred_move_id)
                     VALUES %s
                ON CONFLICT DO NOTHING
            """, [
                (original_move_id, deferral_move.id)
                for original_move_id in all_original_move_ids
                for deferral_move in pair_moves
            ])

        new_deferred_moves.invalidate_recordset()
        new_deferred_moves._post(soft=True)

        return {
            'name': _('Deferred Entries'),
            'type': 'ir.actions.act_window',
            'views': [(False, "list"), (False, "form")],
            'domain': [('id', 'in', new_deferred_moves.ids)],
            'res_model': 'account.move',
            'context': {
                'search_default_group_by_move': True,
                'expand': True,
            },
            'target': 'current',
        }
