from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    @api.model_create_multi
    def create(self, vals_list):
        # Prevent l10n_th_account_tax compute from forcefully overwriting the user's
        # choice of payment_difference_handling back to 'reconcile' when WHT exists.
        return super(AccountPaymentRegister, self.with_context(skip_wht_auto_payment_difference_handling=True)).create(vals_list)

    @api.onchange('amount')
    def _onchange_amount(self):
        # Fix for single invoice payments: account_partner_settlement skips synchronizing
        # custom_user_amount for single invoices. We must manually sync it here so that
        # wht_payment_auto_deduct does not erroneously force 'reconcile' in the UI.
        for wizard in self:
            if hasattr(wizard, '_sync_custom_user_amount_from_current_amount'):
                wizard._sync_custom_user_amount_from_current_amount()
        return super()._onchange_amount()

    @api.depends(
        'can_edit_wizard',
        'source_amount',
        'source_amount_currency',
        'source_currency_id',
        'company_id',
        'currency_id',
        'payment_date',
        'journal_id',
        'payment_method_line_id',
        'installments_mode',
        'manual_currency_rate',
        'manual_currency_rate_active',
    )
    def _compute_amount(self):
        super()._compute_amount()
        for wizard in self:
            if wizard.manual_currency_rate_active and wizard.manual_currency_rate:
                # If user hasn't explicitly set a custom amount, recalculate using manual rate
                if not wizard.custom_user_amount:
                    if wizard.currency_id == wizard.company_id.currency_id and wizard.source_amount_currency:
                        manual_rate = wizard.manual_currency_rate
                        is_inverted = wizard._is_inverted_manual_rate()
                        if is_inverted:
                            wizard.amount = wizard.company_id.currency_id.round(abs(wizard.source_amount_currency) * manual_rate)
                        else:
                            wizard.amount = wizard.company_id.currency_id.round(abs(wizard.source_amount_currency) / manual_rate)


    def _convert_to_wizard_currency(self, installments):
        if not (self.manual_currency_rate_active and self.manual_currency_rate):
            return super()._convert_to_wizard_currency(installments)

        from collections import defaultdict
        self.ensure_one()
        total_per_currency = defaultdict(lambda: {
            'amount_residual': 0.0,
            'amount_residual_currency': 0.0,
        })
        for installment in installments:
            line = installment['line']
            total_per_currency[line.currency_id]['amount_residual'] += installment['amount_residual']
            total_per_currency[line.currency_id]['amount_residual_currency'] += installment['amount_residual_currency']

        total_amount = 0.0
        wizard_curr = self.currency_id
        comp_curr = self.company_currency_id
        for currency, amounts in total_per_currency.items():
            amount_residual = amounts['amount_residual']
            amount_residual_currency = amounts['amount_residual_currency']
            if currency == wizard_curr:
                total_amount += amount_residual_currency
            elif currency != comp_curr and wizard_curr == comp_curr:
                total_amount += self._convert_with_manual_rate(
                    amount_residual_currency, currency, comp_curr
                )
            elif currency == comp_curr and wizard_curr != comp_curr:
                total_amount += self._convert_with_manual_rate(
                    amount_residual, comp_curr, wizard_curr
                )
            else:
                total_amount += self._convert_with_manual_rate(
                    amount_residual, comp_curr, wizard_curr
                )
        return total_amount

    @api.depends('can_edit_wizard', 'amount', 'installments_mode', 'manual_currency_rate', 'manual_currency_rate_active', 'currency_id', 'source_currency_id', 'source_amount_currency')
    def _compute_payment_difference(self):
        super()._compute_payment_difference()

    @api.onchange('manual_currency_rate', 'manual_currency_rate_active')
    def _onchange_manual_currency_rate_fix(self):
        if hasattr(super(), '_onchange_manual_currency_rate'):
            super()._onchange_manual_currency_rate()

        if hasattr(super(), '_onchange_manual_currency_rate_active'):
            super()._onchange_manual_currency_rate_active()

    def action_create_payments(self):
        manual_active = any(getattr(wiz, 'manual_currency_rate_active', False) for wiz in self)
        if manual_active:
            self = self.with_context(no_exchange_difference=True)
        return super().action_create_payments()

    def _should_sync_allocation_lines(self):
        self.ensure_one()
        if getattr(self, 'manual_currency_rate_active', False) and getattr(self, 'manual_currency_rate', False):
            return False
        if hasattr(super(), '_should_sync_allocation_lines'):
            return super()._should_sync_allocation_lines()
        return False

    def _is_inverted_manual_rate(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'bi_manual_currency_exchange_rate.inverted_rate'
        ) == 'True'

    def _get_company_balance_from_payment_currency(self, amount_currency):
        self.ensure_one()
        if self.currency_id == self.company_id.currency_id:
            return amount_currency

        manual_active = bool(getattr(self, 'manual_currency_rate_active', False))
        manual_rate = getattr(self, 'manual_currency_rate', 0.0)
        if manual_active and manual_rate:
            if self._is_inverted_manual_rate():
                return self.company_id.currency_id.round(amount_currency * manual_rate)
            return self.company_id.currency_id.round(amount_currency / manual_rate)

        return self.currency_id._convert(
            amount_currency,
            self.company_id.currency_id,
            self.company_id,
            self.payment_date or fields.Date.context_today(self),
        )

    def _get_fx_writeoff_account(self, writeoff_balance):
        self.ensure_one()
        company = self.company_id
        if writeoff_balance > 0:
            return (
                company.expense_currency_exchange_account_id
                or company.income_currency_exchange_account_id
            )
        return (
            company.income_currency_exchange_account_id
            or company.expense_currency_exchange_account_id
        )

    def _get_fx_account_ids(self):
        self.ensure_one()
        company = self.company_id
        return {
            company.income_currency_exchange_account_id.id if company.income_currency_exchange_account_id else False,
            company.expense_currency_exchange_account_id.id if company.expense_currency_exchange_account_id else False,
        } - {False}

    def _is_wht_writeoff_line(self, line_vals):
        return bool(line_vals.get('wht_tax_id') or line_vals.get('tax_base_amount'))

    def _is_fx_writeoff_line(self, line_vals):
        name = (line_vals.get('name') or '').strip()
        return 'fx_protected_balance' in line_vals or name == _("Exchange Difference")

    def _append_manual_fx_writeoff_line(self, payment_vals, batch_result):
        self.ensure_one()
        manual_active = getattr(self, 'manual_currency_rate_active', False) or self._context.get('manual_currency_rate_active', False)
        manual_rate = getattr(self, 'manual_currency_rate', 0.0) or self._context.get('manual_currency_rate', 0.0)
        
        if not manual_active or not manual_rate:
            return payment_vals

        lines = batch_result.get('lines') or self.line_ids
        if not lines:
            return payment_vals

        company_currency = self.company_id.currency_id
        has_foreign_source = any(
            line.currency_id and line.currency_id != company_currency
            for line in lines
        )
        if (
            self.currency_id == company_currency
            and self.source_currency_id == company_currency
            and not has_foreign_source
        ):
            return payment_vals

        all_writeoffs = list(payment_vals.get('write_off_line_vals', []))
        non_fx_writeoffs = [vals for vals in all_writeoffs if not self._is_fx_writeoff_line(vals)]
        payment_vals['write_off_line_vals'] = non_fx_writeoffs

        if self.payment_type == 'inbound':
            liquidity_amount_currency = self.amount
        elif self.payment_type == 'outbound':
            liquidity_amount_currency = -self.amount
        else:
            liquidity_amount_currency = 0.0

        liquidity_balance = self._get_company_balance_from_payment_currency(
            liquidity_amount_currency
        )
        existing_writeoff_balance = sum(
            line_vals.get('balance', 0.0)
            for line_vals in payment_vals['write_off_line_vals']
        )
        total_residual = sum(lines.mapped('amount_residual'))
        total_residual_currency = sum(lines.mapped('amount_residual_currency'))

        is_partial_payment = self.payment_difference_handling == 'open'
        if not is_partial_payment and hasattr(self, 'deduction_ids'):
            if any(d.is_open for d in self.deduction_ids):
                is_partial_payment = True

        if is_partial_payment:
            # Proportional target counterpart for partial payment
            total_payment_thb = liquidity_balance + existing_writeoff_balance
            residual_at_manual_rate = self._convert_with_manual_rate(
                total_residual_currency, self.source_currency_id, self.company_id.currency_id
            )
            if residual_at_manual_rate != 0:
                pay_ratio = abs(total_payment_thb / residual_at_manual_rate)
                pay_ratio = min(pay_ratio, 1.0)
                target_counterpart_balance = - (total_residual * pay_ratio)
                target_settled_amount_currency = total_residual_currency * pay_ratio
            else:
                target_counterpart_balance = -total_residual
                target_settled_amount_currency = total_residual_currency
        else:
            # Full reconciliation
            target_counterpart_balance = -total_residual
            target_settled_amount_currency = total_residual_currency

        fx_writeoff_balance = self.company_id.currency_id.round(
            -liquidity_balance - existing_writeoff_balance - target_counterpart_balance
        )
        
        fx_account = self._get_fx_writeoff_account(fx_writeoff_balance)
        if not fx_account:
            raise UserError(
                _(
                    "Please configure Exchange Gain/Loss accounts on the company before posting a manual-rate payment."
                )
            )

        fx_amount_currency = fx_writeoff_balance if self.currency_id == self.company_id.currency_id else 0.0

        debit = fx_writeoff_balance if fx_writeoff_balance > 0 else 0.0
        credit = -fx_writeoff_balance if fx_writeoff_balance < 0 else 0.0

        fx_line_vals = {
            'name': _("Exchange Difference"),
            'account_id': fx_account.id,
            'partner_id': self.partner_id.id,
            'currency_id': self.currency_id.id,
            'amount_currency': fx_amount_currency,
            'debit': debit,
            'credit': credit,
            'fx_protected_balance': fx_writeoff_balance,
            'target_settled_amount_currency': target_settled_amount_currency,
            'target_settled_currency_id': self.source_currency_id.id,
        }

        if 'write_off_line_vals' not in payment_vals:
            payment_vals['write_off_line_vals'] = [fx_line_vals]
        else:
            existing_lines = payment_vals['write_off_line_vals']
            if len(existing_lines) == 1 and existing_lines[0].get('account_id') == fx_account.id:
                payment_vals['write_off_line_vals'][0].update({
                    'name': _("Exchange Difference"),
                    'fx_protected_balance': fx_writeoff_balance,
                    'amount_currency': fx_amount_currency,
                    'debit': debit,
                    'credit': credit,
                    'balance': fx_writeoff_balance,
                    'target_settled_amount_currency': target_settled_amount_currency,
                    'target_settled_currency_id': self.source_currency_id.id,
                })
            else:
                payment_vals['write_off_line_vals'].append(fx_line_vals)

        return payment_vals

    def _create_payment_vals_from_wizard(self, batch_result):
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        return self._append_manual_fx_writeoff_line(payment_vals, batch_result)

    def _convert_with_manual_rate(self, amount, from_currency, to_currency):
        self.ensure_one()
        manual_active = getattr(self, 'manual_currency_rate_active', False)
        manual_rate = getattr(self, 'manual_currency_rate', 0.0)
        
        if not manual_active or not manual_rate:
            if self._origin:
                manual_active = manual_active or getattr(self._origin, 'manual_currency_rate_active', False)
                manual_rate = manual_rate or getattr(self._origin, 'manual_currency_rate', 0.0)
            if not manual_active or not manual_rate:
                if self._context.get('manual_currency_rate_active') and self._context.get('manual_currency_rate'):
                    manual_active = self._context['manual_currency_rate_active']
                    manual_rate = self._context['manual_currency_rate']

        if not manual_active or not manual_rate:
            return from_currency._convert(amount, to_currency, self.company_id, self.payment_date or fields.Date.context_today(self))

        if from_currency == to_currency:
            return amount

        is_inverted = self._is_inverted_manual_rate()
        company_currency = self.company_id.currency_id

        if from_currency == company_currency:
            if is_inverted:
                return amount / manual_rate
            else:
                return amount * manual_rate
        elif to_currency == company_currency:
            if is_inverted:
                return amount * manual_rate
            else:
                return amount / manual_rate
        else:
            return from_currency._convert(amount, to_currency, self.company_id, self.payment_date or fields.Date.context_today(self))

    def _check_deduction_amount(self):
        try:
            super()._check_deduction_amount()
        except UserError as e:
            for rec in self:
                if getattr(rec, 'manual_currency_rate_active', False) and getattr(rec, 'manual_currency_rate', 0.0):
                    continue
                raise e

    def _prepare_deduct_move_line(self, deduct):
        res = super()._prepare_deduct_move_line(deduct)

        manual_active = getattr(self, 'manual_currency_rate_active', False)
        manual_rate = getattr(self, 'manual_currency_rate', 0.0)

        if manual_active and manual_rate and self.currency_id != self.company_id.currency_id:
            is_inverted = self._is_inverted_manual_rate()
            write_off_amount_currency = res.get('amount_currency', 0.0)

            if write_off_amount_currency != 0.0:
                if is_inverted:
                    write_off_balance = self.company_id.currency_id.round(
                        write_off_amount_currency * manual_rate
                    )
                else:
                    write_off_balance = self.company_id.currency_id.round(
                        write_off_amount_currency / manual_rate
                    ) if manual_rate else 0.0

                res['balance'] = write_off_balance

        return res

    def _prepare_writeoff_move_line(self, write_off_line_vals):
        write_off_line_vals = super()._prepare_writeoff_move_line(write_off_line_vals)

        manual_active = getattr(self, 'manual_currency_rate_active', False)
        manual_rate = getattr(self, 'manual_currency_rate', 0.0)
        if not (manual_active and manual_rate):
            return write_off_line_vals

        if self.currency_id == self.company_id.currency_id:
            return write_off_line_vals

        is_inverted = self._is_inverted_manual_rate()
        if is_inverted:
            wht_amount_base_company = self.company_id.currency_id.round(
                self.wht_amount_base * manual_rate
            )
        else:
            wht_amount_base_company = self.company_id.currency_id.round(
                self.wht_amount_base / manual_rate
            ) if manual_rate else 0.0

        wht_tax_id = getattr(self, 'wht_tax_id', False)
        for write_off in write_off_line_vals:
            if wht_tax_id:
                write_off['wht_tax_id'] = wht_tax_id.id
            write_off['tax_base_amount'] = wht_amount_base_company
            
            if write_off.get('currency_id') == self.company_id.currency_id.id:
                if write_off.get('balance') and not write_off.get('amount_currency'):
                    write_off['amount_currency'] = write_off['balance']

            if write_off.get('currency_id') != self.currency_id.id:
                continue
            amount_currency = write_off.get('amount_currency', 0.0)

            if amount_currency != 0.0:
                if is_inverted:
                    write_off['balance'] = self.company_id.currency_id.round(
                        amount_currency * manual_rate
                    )
                else:
                    write_off['balance'] = self.company_id.currency_id.round(
                        amount_currency / manual_rate
                    ) if manual_rate else 0.0

        return write_off_line_vals

    def _auto_apply_wht_from_lines(self):
        for wizard in self:
            manual_active = getattr(wizard, 'manual_currency_rate_active', False)
            manual_rate = getattr(wizard, 'manual_currency_rate', 0.0)
            if manual_active and manual_rate:
                wizard = wizard.with_context(
                    manual_currency_rate_active=manual_active,
                    manual_currency_rate=manual_rate
                )
            super(AccountPaymentRegister, wizard)._auto_apply_wht_from_lines()
