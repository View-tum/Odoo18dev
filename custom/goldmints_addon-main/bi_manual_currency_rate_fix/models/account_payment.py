from odoo import api, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @staticmethod
    def _set_balance_on_line_vals(line_vals, balance):
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

    @api.onchange('manual_currency_rate_active', 'currency_id')
    def check_currency_id(self):
        active_before = {p.id: p.manual_currency_rate_active for p in self}
        rate_before = {p.id: p.manual_currency_rate for p in self}
        res = super().check_currency_id()
        for payment in self:
            if not active_before.get(payment.id):
                continue
            reconciled_currencies = (
                payment.reconciled_invoice_ids.mapped('currency_id')
                | payment.move_id.line_ids.mapped('currency_id')
            )
            has_foreign = any(c != payment.company_id.currency_id for c in reconciled_currencies if c)
            if has_foreign:
                payment.manual_currency_rate_active = active_before[payment.id]
                payment.manual_currency_rate = rate_before[payment.id]
        return res

    def _prepare_move_line_default_vals(self, write_off_line_vals=None, force_balance=None):
        has_fx_protected_balance = False
        target_settled_amount_currency = None
        target_settled_currency_id = None
        
        if write_off_line_vals:
            for write_off in list(write_off_line_vals):
                if 'fx_protected_balance' in write_off:
                    has_fx_protected_balance = True
                    write_off['balance'] = write_off.pop('fx_protected_balance')
                    
                    if 'target_settled_amount_currency' in write_off:
                        target_settled_amount_currency = write_off.pop('target_settled_amount_currency')
                        target_settled_currency_id = write_off.pop('target_settled_currency_id')
                    
                    if self.company_id.currency_id.is_zero(write_off['balance']) and not write_off.get('amount_currency'):
                        write_off_line_vals.remove(write_off)

        line_vals_list = super()._prepare_move_line_default_vals(write_off_line_vals, force_balance)

        if not self.manual_currency_rate_active or not self.manual_currency_rate:
            return line_vals_list

        destination_account_id = self.destination_account_id.id
        is_foreign_payment = self.currency_id != self.company_id.currency_id
        has_foreign_dest = any(
            lv.get('currency_id') and lv.get('currency_id') != self.company_id.currency_id.id
            for lv in line_vals_list
            if lv.get('account_id') == destination_account_id
        )

        if is_foreign_payment or has_foreign_dest or has_fx_protected_balance or (self.manual_currency_rate_active and self.manual_currency_rate):
            for line_vals in line_vals_list:
                amount_currency = line_vals.get('amount_currency') or 0.0
                if not amount_currency:
                    continue
                if line_vals.get('account_id') == destination_account_id:
                    continue
                line_currency_id = line_vals.get('currency_id')
                if not line_currency_id or line_currency_id == self.company_id.currency_id.id:
                    continue

                abs_balance = self._get_manual_rate_balance(abs(amount_currency))
                if abs_balance is None:
                    continue
                balance = abs_balance if amount_currency > 0 else -abs_balance
                self._set_balance_on_line_vals(line_vals, balance)

            non_dest_balance_sum = sum(
                self._get_line_balance(lv) for lv in line_vals_list if lv.get('account_id') != destination_account_id
            )
            for line_vals in line_vals_list:
                if line_vals.get('account_id') == destination_account_id:
                    self._set_balance_on_line_vals(line_vals, self.company_id.currency_id.round(-non_dest_balance_sum))

        if target_settled_currency_id and target_settled_amount_currency:
            for lv in line_vals_list:
                if lv.get('account_id') == destination_account_id:
                    lv['currency_id'] = target_settled_currency_id
                    lv['amount_currency'] = -abs(target_settled_amount_currency) if self.payment_type == 'inbound' else abs(target_settled_amount_currency)

        return line_vals_list

    def _synchronize_to_moves(self, changed_fields):
        if any(pay.manual_currency_rate_active and pay.manual_currency_rate for pay in self):
            for pay in self:
                if pay.manual_currency_rate_active and pay.manual_currency_rate and pay.move_id:
                    pay.move_id.with_context(skip_account_move_synchronization=True).write({
                        'manual_currency_rate_active': pay.manual_currency_rate_active,
                        'manual_currency_rate': pay.manual_currency_rate,
                    })
            return
        super()._synchronize_to_moves(changed_fields)

