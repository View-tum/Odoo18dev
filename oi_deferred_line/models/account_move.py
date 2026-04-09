from itertools import chain

from odoo import _, Command, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    deferred_default_journal_id = fields.Many2one(
        "account.journal",
        string="Default Deferred Journal",
        domain="[('type', '=', 'general'), ('company_id', '=', company_id)]",
        copy=False,
    )
    deferred_default_account_id = fields.Many2one(
        "account.account",
        string="Default Deferred Account",
        domain="[('deprecated', '=', False), ('company_ids', 'parent_of', company_id)]",
        copy=False,
    )

    def _generate_deferred_entries(self):
        self.ensure_one()
        if self.state != "posted":
            return
        if self.is_entry():
            raise UserError(_("You cannot generate deferred entries for a miscellaneous journal entry."))

        deferred_type = "expense" if self.is_purchase_document(include_receipts=True) else "revenue"

        moves_vals_to_create = []
        lines_vals_to_create = []
        lines_periods = []

        for line in self.line_ids.filtered(lambda l: l.deferred_start_date and l.deferred_end_date):
            journal = line.deferred_journal_id or (
                self.company_id.deferred_expense_journal_id if deferred_type == "expense" else self.company_id.deferred_revenue_journal_id
            )
            account = line.deferred_account_id or (
                self.company_id.deferred_expense_account_id if deferred_type == "expense" else self.company_id.deferred_revenue_account_id
            )
            if not journal:
                raise UserError(_("Please set the deferred journal on the line or in the accounting settings."))
            if not account:
                raise UserError(_("Please set the deferred account on the line or in the accounting settings."))

            periods = line._get_deferred_periods()
            if not periods:
                continue

            ref = _("Deferral of %s", line.move_id.name or "")

            moves_vals_to_create.append({
                "move_type": "entry",
                "deferred_original_move_ids": [Command.set(line.move_id.ids)],
                "journal_id": journal.id,
                "company_id": self.company_id.id,
                "partner_id": line.partner_id.id,
                "auto_post": "at_date",
                "ref": ref,
                "name": False,
                "date": line.move_id.date,
            })
            lines_vals_to_create.append([
                self.env["account.move.line"]._get_deferred_lines_values(account_id, coeff * line.balance, ref, line.analytic_distribution, line)
                for (account_id, coeff) in [(line.account_id.id, -1), (account.id, 1)]
            ])
            lines_periods.append((line, periods, journal, account))

        moves_fully_deferred = self.create(moves_vals_to_create)
        for move_fully_deferred, lines_vals in zip(moves_fully_deferred, lines_vals_to_create):
            for line_vals in lines_vals:
                line_vals["move_id"] = move_fully_deferred.id
        self.env["account.move.line"].create(list(chain(*lines_vals_to_create)))

        deferral_moves_vals = []
        deferral_moves_line_vals = []
        for (line, periods, journal, account), move_vals in zip(lines_periods, moves_vals_to_create):
            remaining_balance = line.balance
            for period_index, period in enumerate(periods):
                force_balance = remaining_balance if period_index == len(periods) - 1 else None
                deferred_amounts = self._get_deferred_amounts_by_line(line, [period], deferred_type)[0]
                balance = deferred_amounts[period] if force_balance is None else force_balance
                remaining_balance -= line.currency_id.round(balance)
                deferral_moves_vals.append({**move_vals, "journal_id": journal.id, "date": period[1]})
                deferral_moves_line_vals.append([
                    {
                        **self.env["account.move.line"]._get_deferred_lines_values(account_id, coeff * balance, move_vals["ref"], line.analytic_distribution, line),
                        "partner_id": line.partner_id.id,
                        "product_id": line.product_id.id,
                    }
                    for (account_id, coeff) in [(deferred_amounts["account_id"].id if hasattr(deferred_amounts["account_id"], "id") else deferred_amounts["account_id"], 1), (account.id, -1)]
                ])

        deferral_moves = self.create(deferral_moves_vals)
        for deferral_move, lines_vals in zip(deferral_moves, deferral_moves_line_vals):
            for line_vals in lines_vals:
                line_vals["move_id"] = deferral_move.id
        self.env["account.move.line"].create(list(chain(*deferral_moves_line_vals)))

        to_unlink = deferral_moves.filtered(lambda move: move.currency_id.is_zero(move.amount_total))
        for move_fully_deferred in moves_fully_deferred:
            deferred_move_ids = move_fully_deferred + deferral_moves
            cancelling_moves = deferred_move_ids.filtered(lambda m: move_fully_deferred.date.replace(day=1) == m.date.replace(day=1) and m.amount_total == move_fully_deferred.amount_total)
            if len(cancelling_moves) == 2:
                to_unlink |= cancelling_moves
                continue

        to_unlink.unlink()
        (moves_fully_deferred + deferral_moves - to_unlink)._post(soft=True)
