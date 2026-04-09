from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    @api.onchange('amount')
    def _onchange_amount(self):
        # Keep core behavior for tracking manual amount and clearing stale custom flags.
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
            if not wizard.journal_id or not wizard.currency_id or wizard.custom_user_amount:
                continue

            if getattr(wizard, 'manual_currency_rate_active', False) and getattr(wizard, 'manual_currency_rate', 0.0):
                if wizard.currency_id == wizard.source_currency_id:
                    continue

                is_inverted = wizard._is_inverted_manual_rate()
                pay_is_company = wizard.currency_id == wizard.company_id.currency_id
                src_is_company = wizard.source_currency_id == wizard.company_id.currency_id

                expected_amount = 0.0
                if pay_is_company and not src_is_company:
                    if is_inverted:
                        expected_amount = wizard.source_amount_currency * wizard.manual_currency_rate
                    else:
                        expected_amount = wizard.source_amount_currency / wizard.manual_currency_rate if wizard.manual_currency_rate else 0.0
                elif src_is_company and not pay_is_company:
                    if is_inverted:
                        expected_amount = wizard.source_amount / wizard.manual_currency_rate if wizard.manual_currency_rate else 0.0
                    else:
                        expected_amount = wizard.source_amount * wizard.manual_currency_rate
                else:
                    if is_inverted:
                        expected_amount = wizard.source_amount_currency * wizard.manual_currency_rate
                    else:
                        expected_amount = wizard.source_amount_currency / wizard.manual_currency_rate if wizard.manual_currency_rate else 0.0

                expected_amount = wizard.currency_id.round(expected_amount)
                if expected_amount > 0.0:
                    wizard.amount = expected_amount


    @api.depends('can_edit_wizard', 'amount', 'installments_mode', 'manual_currency_rate', 'manual_currency_rate_active', 'currency_id', 'source_currency_id', 'source_amount_currency')
    def _compute_payment_difference(self):
        import logging
        _logger = logging.getLogger(__name__)

        super()._compute_payment_difference()
        for wizard in self:
            if wizard.manual_currency_rate_active and wizard.manual_currency_rate:
                _logger.info("COMPUTE DIFF: cur=%s src_cur=%s amount=%s src_amount=%s src_amount_cur=%s",
                             wizard.currency_id.name, wizard.source_currency_id.name, wizard.amount, wizard.source_amount, wizard.source_amount_currency)
                if wizard.currency_id == wizard.source_currency_id:
                    _logger.info("COMPUTE DIFF SKIPPED because same currency!")
                    continue

                is_inverted = wizard._is_inverted_manual_rate()
                pay_is_company = wizard.currency_id == wizard.company_id.currency_id
                src_is_company = wizard.source_currency_id == wizard.company_id.currency_id

                expected_amount = 0.0
                if pay_is_company and not src_is_company:
                    if is_inverted:
                        expected_amount = wizard.source_amount_currency * wizard.manual_currency_rate
                    else:
                        expected_amount = wizard.source_amount_currency / wizard.manual_currency_rate if wizard.manual_currency_rate else 0.0
                elif src_is_company and not pay_is_company:
                    if is_inverted:
                        expected_amount = wizard.source_amount / wizard.manual_currency_rate if wizard.manual_currency_rate else 0.0
                    else:
                        expected_amount = wizard.source_amount * wizard.manual_currency_rate
                else:
                    if is_inverted:
                        expected_amount = wizard.source_amount_currency * wizard.manual_currency_rate
                    else:
                        expected_amount = wizard.source_amount_currency / wizard.manual_currency_rate if wizard.manual_currency_rate else 0.0

                expected_amount = wizard.currency_id.round(expected_amount)
                wizard.payment_difference = expected_amount - wizard.amount
                _logger.info("COMPUTE DIFF SUCCESS: expected=%s diff=%s", expected_amount, wizard.payment_difference)

    @api.onchange('manual_currency_rate', 'manual_currency_rate_active')
    def _onchange_manual_currency_rate_fix(self):
        # A change in manual rate means we want standard manual rate re-calculation, not custom frozen amount
        self.custom_user_amount = 0.0

        if hasattr(super(), '_onchange_manual_currency_rate'):
            super()._onchange_manual_currency_rate()

        if hasattr(super(), '_onchange_manual_currency_rate_active'):
            super()._onchange_manual_currency_rate_active()

        # Trigger the compute amount implicitly by calling the method
        self._compute_amount()


    def action_create_payments(self):
        """
        Force pass 'no_exchange_difference' context to prevent Odoo from natively
        spawning an EXCH journal entry if we already injected our custom FX Diff mapping
        into the main Payment/RV entry.
        """
        manual_active = any(getattr(wiz, 'manual_currency_rate_active', False) for wiz in self)
        if manual_active:
            self = self.with_context(no_exchange_difference=True)

        return super().action_create_payments()

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
        # Only clear explicitly auto-generated FX lines from THIS module
        return 'fx_protected_balance' in line_vals or name == _("Exchange Difference")

    def _append_manual_fx_writeoff_line(self, payment_vals, batch_result):
        self.ensure_one()
        if not getattr(self, 'manual_currency_rate_active', False):
            return payment_vals
        if not getattr(self, 'manual_currency_rate', 0.0):
            return payment_vals

        # Keep partial-payment behavior unchanged in "Keep open".
        if self.payment_difference != 0.0 and self.payment_difference_handling == 'open':
            return payment_vals

        lines = batch_result.get('lines') or self.line_ids
        if not lines:
            return payment_vals

        company_currency = self.company_id.currency_id
        has_foreign_source = any(
            line.currency_id and line.currency_id != company_currency
            for line in lines
        )
        # Some custom flows/wizards may normalize source_currency_id to company currency.
        # Use source move lines as the source of truth to decide if FX writeoff is needed.
        if (
            self.currency_id == company_currency
            and self.source_currency_id == company_currency
            and not has_foreign_source
        ):
            return payment_vals

        # Keep ALL explicit user write-offs intact (manual deductions / WHT / bank fees).
        # We only remove existing purely auto-generated FX lines if any slipped through.
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
        target_counterpart_balance = -sum(lines.mapped('amount_residual'))

        fx_writeoff_balance = self.company_id.currency_id.round(
            -liquidity_balance - existing_writeoff_balance - target_counterpart_balance
        )
        if self.company_id.currency_id.is_zero(fx_writeoff_balance):
            return payment_vals

        fx_account = self._get_fx_writeoff_account(fx_writeoff_balance)
        if not fx_account:
            raise UserError(
                _(
                    "Please configure Exchange Gain/Loss accounts on the company before posting a manual-rate payment."
                )
            )

        # Odoo 16+ enforces amount_currency == balance when currency_id == company_id
        # Hardcoding amount_currency to 0.0 forces Odoo's compute methods to overwrite the balance to 0.00!
        fx_amount_currency = fx_writeoff_balance if self.currency_id == self.company_id.currency_id else 0.0

        # Guarantee Odoo doesn't zero it out by passing explicit debit/credit
        debit = fx_writeoff_balance if fx_writeoff_balance > 0 else 0.0
        credit = -fx_writeoff_balance if fx_writeoff_balance < 0 else 0.0

        payment_vals.setdefault('write_off_line_vals', []).append(
            {
                'name': _("Exchange Difference"),
                'account_id': fx_account.id,
                'partner_id': self.partner_id.id,
                'currency_id': self.currency_id.id,
                'amount_currency': fx_amount_currency,
                'debit': debit,
                'credit': credit,
                'fx_protected_balance': fx_writeoff_balance,
            }
        )
        return payment_vals

    def _create_payment_vals_from_wizard(self, batch_result):
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        return self._append_manual_fx_writeoff_line(payment_vals, batch_result)

    def _check_deduction_amount(self):
        """
        Bypass Ecosoft's multi-deduction constraint if manual currency rate is active.
        The system will auto-generate the remaining Exchange Difference line to balance it.
        """
        try:
            super()._check_deduction_amount()
        except UserError as e:
            # We catch the UserError because Ecosoft's multi-deduction throws it directly from @api.constrains
            # Odoo 18 api.constrains are executed immediately or at the end of flush.
            for rec in self:
                if getattr(rec, 'manual_currency_rate_active', False) and getattr(rec, 'manual_currency_rate', 0.0):
                    continue
                raise e

    def _prepare_deduct_move_line(self, deduct):
        res = super()._prepare_deduct_move_line(deduct)

        manual_active = getattr(self, 'manual_currency_rate_active', False)
        manual_rate = getattr(self, 'manual_currency_rate', 0.0)

        # Only touch the deduction if it's evaluated natively in a foreign currency
        if manual_active and manual_rate and self.currency_id != self.company_id.currency_id:
            is_inverted = self._is_inverted_manual_rate()
            write_off_amount_currency = res.get('amount_currency', 0.0)

            # If the original amount_currency is 0 (e.g. paying in THB), the deduct amount is actually stored in balance
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

        # Company-currency payment must keep write-off balances as-is.
        # Re-converting here would multiply/divide already-THB amounts again.
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

            # Only force conversion for lines really in payment currency.
            if write_off.get('currency_id') != self.currency_id.id:
                continue
            amount_currency = write_off.get('amount_currency', 0.0)

            # If the deduction amount_currency is 0 (i.e. strictly THB amount), don't wipe it out.
            # Its balance is already correctly established.
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
