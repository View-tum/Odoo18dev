from odoo import models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

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
