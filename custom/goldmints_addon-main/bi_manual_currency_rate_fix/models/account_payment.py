from odoo import Command, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def _get_preserved_writeoff_line_vals(self, writeoff_lines):
        """Keep custom metadata when payment sync rebuilds journal lines.

        Core account.payment._synchronize_to_moves() collapses all write-off lines
        into a single synthetic line and only preserves a minimal key set.
        Our WHT flow stores legal filing data on the payment write-off line
        (wht_tax_id / tax_base_amount). If sync runs after payment creation,
        those fields are lost and no withholding certificate can be created.
        """
        preserved_vals = []
        for line in writeoff_lines:
            line_vals = {
                'name': line.name,
                'account_id': line.account_id.id,
                'partner_id': line.partner_id.id,
                'currency_id': line.currency_id.id,
                'amount_currency': line.amount_currency,
                'balance': line.balance,
            }
            if 'analytic_distribution' in line._fields:
                line_vals['analytic_distribution'] = line.analytic_distribution
            if 'wht_tax_id' in line._fields and line.wht_tax_id:
                line_vals['wht_tax_id'] = line.wht_tax_id.id
            if 'tax_base_amount' in line._fields:
                line_vals['tax_base_amount'] = line.tax_base_amount
            preserved_vals.append(line_vals)
        return preserved_vals

    @staticmethod
    def _set_balance_on_line_vals(line_vals, balance):
        # Keep debit/credit as source of truth when we force a line balance.
        line_vals.pop('balance', None)
        line_vals['debit'] = balance if balance > 0.0 else 0.0
        line_vals['credit'] = -balance if balance < 0.0 else 0.0

    @staticmethod
    def _get_line_balance(line_vals):
        debit = line_vals.get('debit')
        credit = line_vals.get('credit')
        if debit is not None or credit is not None:
            return (debit or 0.0) - (credit or 0.0)
        return line_vals.get('balance', 0.0) or 0.0

    def _get_manual_rate_balance(self, amount_currency):
        self.ensure_one()
        if not self.manual_currency_rate or not self.manual_currency_rate_active:
            return None

        is_inverted = self.env['ir.config_parameter'].sudo().get_param(
            'bi_manual_currency_exchange_rate.inverted_rate'
        ) == 'True'
        if is_inverted:
            return self.company_id.currency_id.round(amount_currency * self.manual_currency_rate)
        else:
            if self.manual_currency_rate:
                return self.company_id.currency_id.round(amount_currency / self.manual_currency_rate)
            return 0.0

    def _prepare_move_line_default_vals(self, write_off_line_vals=None, force_balance=None):
        if write_off_line_vals:
            for write_off in write_off_line_vals:
                if 'fx_protected_balance' in write_off:
                    # Restore the native 'balance' right before Odoo consumes it, bypassing
                    # earlier aggressive manual rate overrides in upstream modules.
                    write_off['balance'] = write_off.pop('fx_protected_balance')

        line_vals_list = super()._prepare_move_line_default_vals(write_off_line_vals, force_balance)

        if not self.manual_currency_rate_active or not self.manual_currency_rate:
            return line_vals_list

        destination_account_id = self.destination_account_id.id

        # If payment is in foreign currency (e.g. USD payment -> THB DB),
        # standard Odoo bank line amount_currency is e.g. 200 USD. We recalculate its THB balance manually.
        if self.currency_id != self.company_id.currency_id:
            for line_vals in line_vals_list:
                amount_currency = line_vals.get('amount_currency') or 0.0
                if not amount_currency:
                    continue
                if line_vals.get('currency_id') != self.currency_id.id:
                    continue
                if line_vals.get('account_id') == destination_account_id:
                    continue

                abs_balance = self._get_manual_rate_balance(abs(amount_currency))
                if abs_balance is None:
                    continue
                balance = abs_balance if amount_currency > 0 else -abs_balance
                self._set_balance_on_line_vals(line_vals, balance)

            # To avoid "The entry is not balanced" error:
            # Since standard Odoo calculated the destination line (AR/AP) based on the system-rate bank line,
            # we must adjust the destination line's balance so the whole journal entry perfectly balances.
            non_dest_balance_sum = sum(
                self._get_line_balance(lv) for lv in line_vals_list if lv.get('account_id') != destination_account_id
            )
            for line_vals in line_vals_list:
                if line_vals.get('account_id') == destination_account_id:
                    self._set_balance_on_line_vals(line_vals, self.company_id.currency_id.round(-non_dest_balance_sum))

        return line_vals_list

    def _synchronize_to_moves(self, changed_fields):
        if self.env.context.get('skip_account_move_synchronization'):
            return
        if any(rec.is_multi_deduction for rec in self if 'is_multi_deduction' in rec._fields):
            return
        if not any(field_name in changed_fields for field_name in self._get_trigger_fields_to_synchronize()):
            return

        for pay in self:
            liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()
            write_off_line_vals = pay._get_preserved_writeoff_line_vals(writeoff_lines)
            line_vals_list = pay._prepare_move_line_default_vals(
                write_off_line_vals=write_off_line_vals
            )
            line_ids_commands = [
                Command.update(liquidity_lines.id, line_vals_list[0]) if liquidity_lines else Command.create(line_vals_list[0]),
                Command.update(counterpart_lines.id, line_vals_list[1]) if counterpart_lines else Command.create(line_vals_list[1]),
            ]
            for line in writeoff_lines:
                line_ids_commands.append(Command.delete(line.id))
            for extra_line_vals in line_vals_list[2:]:
                line_ids_commands.append(Command.create(extra_line_vals))
            to_write = {
                'date': pay.date,
                'partner_id': pay.partner_id.id,
                'currency_id': pay.currency_id.id,
                'partner_bank_id': pay.partner_bank_id.id,
                'line_ids': line_ids_commands,
            }
            if 'journal_id' in changed_fields:
                to_write.update({
                    'name': '/',
                    'journal_id': pay.journal_id.id,
                })
            pay.move_id.with_context(skip_invoice_sync=True).write(to_write)
