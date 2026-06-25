import logging

from odoo import Command, api, fields, models

_logger = logging.getLogger(__name__)


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    is_multi_allocation_enabled = fields.Boolean(
        related='company_id.enable_multi_invoice_allocation'
    )

    allocation_line_ids = fields.One2many(
        'account.payment.allocation.line', 'wizard_id', string='Allocations'
    )

    def _get_allocation_currency(self, res, move_lines):
        currency = self.env['res.currency'].browse(res.get('currency_id'))
        if currency:
            return currency

        line_currencies = move_lines.mapped('currency_id')
        if len(line_currencies) == 1:
            return line_currencies

        move_currencies = move_lines.mapped('move_id.currency_id')
        if len(move_currencies) == 1:
            return move_currencies

        company_currencies = move_lines.mapped('company_currency_id')
        if len(company_currencies) == 1:
            return company_currencies

        return self.env.company.currency_id

    def _get_allocation_residual_amount(self, move_line, wizard_currency, payment_date, manual_active, manual_rate):
        company_currency = move_line.company_id.currency_id
        line_currency = move_line.currency_id or move_line.move_id.currency_id or company_currency

        if line_currency == wizard_currency:
            if move_line.currency_id:
                amount = abs(move_line.amount_residual_currency)
            elif line_currency == company_currency:
                amount = abs(move_line.amount_residual)
            else:
                amount = abs(company_currency._convert(
                    abs(move_line.amount_residual),
                    wizard_currency,
                    move_line.company_id,
                    payment_date,
                ))
            return wizard_currency.round(amount)

        if manual_active and line_currency == company_currency:
            is_inverted = self.env['ir.config_parameter'].sudo().get_param(
                'bi_manual_currency_exchange_rate.inverted_rate'
            ) == 'True'
            if is_inverted:
                return wizard_currency.round(abs(move_line.amount_residual) / manual_rate)
            return wizard_currency.round(abs(move_line.amount_residual) * manual_rate)

        if move_line.currency_id and move_line.currency_id != company_currency:
            converted = move_line.currency_id._convert(
                abs(move_line.amount_residual_currency),
                wizard_currency,
                move_line.company_id,
                payment_date,
            )
        else:
            converted = company_currency._convert(
                abs(move_line.amount_residual),
                wizard_currency,
                move_line.company_id,
                payment_date,
            )
        return wizard_currency.round(abs(converted))

    def _get_allocation_total_amount(self, move_line, wizard_currency, payment_date, manual_active, manual_rate):
        company_currency = move_line.company_id.currency_id
        line_currency = move_line.currency_id or move_line.move_id.currency_id or company_currency

        if line_currency == wizard_currency:
            if move_line.currency_id:
                amount = abs(move_line.amount_currency)
            elif line_currency == company_currency:
                amount = abs(move_line.balance)
            else:
                amount = abs(company_currency._convert(
                    abs(move_line.balance),
                    wizard_currency,
                    move_line.company_id,
                    payment_date,
                ))
            return wizard_currency.round(amount)

        if manual_active and line_currency == company_currency:
            is_inverted = self.env['ir.config_parameter'].sudo().get_param(
                'bi_manual_currency_exchange_rate.inverted_rate'
            ) == 'True'
            if is_inverted:
                return wizard_currency.round(abs(move_line.balance) / manual_rate)
            return wizard_currency.round(abs(move_line.balance) * manual_rate)

        if move_line.currency_id and move_line.currency_id != company_currency:
            converted = move_line.currency_id._convert(
                abs(move_line.amount_currency),
                wizard_currency,
                move_line.company_id,
                payment_date,
            )
        else:
            converted = company_currency._convert(
                abs(move_line.balance),
                wizard_currency,
                move_line.company_id,
                payment_date,
            )
        return wizard_currency.round(abs(converted))

    def _refresh_allocation_lines_for_display(self):
        self.ensure_one()
        if not self.currency_id:
            return
        payment_date = self.payment_date or fields.Date.context_today(self)
        manual_rate = self.manual_currency_rate or 0.0
        manual_active = bool(self.manual_currency_rate_active and manual_rate)

        for alloc in self.allocation_line_ids:
            move_line = alloc.move_line_id
            if not move_line:
                continue

            is_credit_note = move_line.move_id.move_type in ('out_refund', 'in_refund')
            sign = -1 if is_credit_note else 1

            previous_amount_to_pay = alloc.amount_to_pay
            previous_amount_residual = alloc.amount_residual
            previous_residual_original = alloc.amount_residual_original

            new_total = sign * self._get_allocation_total_amount(
                move_line,
                self.currency_id,
                payment_date,
                manual_active,
                manual_rate,
            )
            new_residual_original = sign * self._get_allocation_residual_amount(
                move_line,
                self.currency_id,
                payment_date,
                manual_active,
                manual_rate,
            )

            alloc.amount_total = new_total
            alloc.amount_residual_original = new_residual_original

            allocation_total = previous_amount_to_pay + previous_amount_residual
            if not self.currency_id.is_zero(allocation_total):
                paid_ratio = abs(previous_amount_to_pay) / abs(allocation_total)
            elif not self.currency_id.is_zero(previous_residual_original):
                paid_ratio = abs(previous_amount_to_pay) / abs(previous_residual_original)
            else:
                paid_ratio = 1.0

            paid_ratio = min(max(paid_ratio, 0.0), 1.0)
            new_amount_to_pay = self.currency_id.round(
                abs(new_residual_original) * paid_ratio
            )
            if new_residual_original < 0:
                new_amount_to_pay *= -1
            alloc.amount_to_pay = new_amount_to_pay
            alloc.amount_residual = new_residual_original - new_amount_to_pay

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'allocation_line_ids' in fields_list and 'line_ids' in res:
            line_ids = res.get('line_ids')
            if line_ids and isinstance(line_ids[0], (list, tuple)) and line_ids[0][0] == 6:
                aml_ids = line_ids[0][2]
            else:
                aml_ids = []

            if aml_ids:
                move_lines = self.env['account.move.line'].browse(aml_ids)
                currency = self._get_allocation_currency(res, move_lines)
                payment_date = res.get('payment_date') or fields.Date.context_today(self)
                manual_rate = res.get('manual_currency_rate', 1.0)
                manual_active = bool(res.get('manual_currency_rate_active') and manual_rate)
                allocation_lines = []
                for aml_id in aml_ids:
                    aml = self.env['account.move.line'].browse(aml_id)
                    is_credit_note = aml.move_id.move_type in ('out_refund', 'in_refund')
                    sign = -1 if is_credit_note else 1

                    amount_residual = sign * self._get_allocation_residual_amount(
                        aml,
                        currency,
                        payment_date,
                        manual_active,
                        manual_rate,
                    )

                    allocation_lines.append(Command.create({
                        'move_line_id': aml_id,
                        'amount_to_pay': amount_residual,
                        'amount_residual': 0.0,
                    }))
                res['allocation_line_ids'] = allocation_lines

            if len(aml_ids) > 1:
                res['group_payment'] = True
        return res

    def _refresh_allocation_amount(self):
        self.ensure_one()
        if not self.currency_id:
            return
        if not self.is_multi_allocation_enabled or not self.allocation_line_ids:
            return
        self.allocation_line_ids._compute_amounts()
        self._refresh_allocation_lines_for_display()
        if self._has_wht_source_lines():
            return
        if self._is_fx_amount_context():
            if not getattr(self, 'manual_currency_rate_active', False) and not self.custom_user_amount:
                total_amount_values = self._get_total_amounts_to_pay(self.batches)
                target_amount = total_amount_values['amount_by_default']
                if self.currency_id.compare_amounts(self.amount, target_amount) != 0:
                    self.amount = target_amount
            return
        total_allocation = sum(self.allocation_line_ids.mapped('amount_to_pay'))
        if self.currency_id.compare_amounts(self.amount, total_allocation) != 0:
            self.amount = total_allocation

    def _has_wht_source_lines(self):
        self.ensure_one()
        get_wht_lines = getattr(self, '_get_wht_source_lines', None)
        if get_wht_lines:
            return bool(get_wht_lines())

        invoice_lines = self.line_ids.mapped('move_id').mapped('invoice_line_ids')
        return bool(
            invoice_lines.filtered(
                lambda line: line.wht_tax_id or (hasattr(line, 'wht_tax_ids') and line.wht_tax_ids)
            )
        )

    @api.onchange(
        'currency_id',
        'journal_id',
        'payment_date',
        'manual_currency_rate',
        'manual_currency_rate_active',
    )
    def _onchange_allocation_context_fields(self):
        for wizard in self:
            wizard._refresh_allocation_amount()

    @api.onchange('currency_id')
    def _onchange_currency_id(self):
        res = super()._onchange_currency_id()
        for wizard in self:
            wizard._refresh_allocation_amount()
        return res

    @api.onchange('allocation_line_ids')
    def _onchange_allocation_line_ids(self):
        for wizard in self:
            wizard._refresh_allocation_amount()

    def _is_fx_amount_context(self):
        self.ensure_one()
        if getattr(self, 'manual_currency_rate_active', False):
            return True
        if self.currency_id and self.currency_id != self.company_id.currency_id:
            return True
        if self.source_currency_id and self.source_currency_id != self.company_id.currency_id:
            return True
        if self.source_currency_id and self.currency_id and self.source_currency_id != self.currency_id:
            return True
        return False

    def _create_payment_vals_from_wizard(self, batch_result):
        vals = super()._create_payment_vals_from_wizard(batch_result)
        # Avoid forcing amount = sum(allocation) because that is Gross.
        # super() already uses self.amount which is Net.
        return vals

    def _create_payment_vals_from_batch(self, batch_result):
        vals = super()._create_payment_vals_from_batch(batch_result)
        # Avoid forcing amount per batch to allocation sum if it's already handled by Odoo's net logic.
        return vals

    def _is_fx_reconcile_context(self, vals):
        self.ensure_one()
        payment = vals['payment']
        if vals.get('rate'):
            return True
        if getattr(self, 'manual_currency_rate_active', False):
            return True
        if payment.currency_id and payment.currency_id != payment.company_currency_id:
            return True

        company_currency = payment.company_id.currency_id
        lines_to_reconcile = vals.get('to_reconcile') or self.env['account.move.line']
        return bool(
            lines_to_reconcile.filtered(
                lambda line: line.currency_id and line.currency_id != company_currency
            )
        )

    def _compute_partial_amount_currency(self, line, amount_company):
        if line.currency_id and line.currency_id != line.company_currency_id:
            amount_currency = line.company_currency_id._convert(
                amount_company,
                line.currency_id,
                line.company_id,
                line.date or fields.Date.context_today(line),
            )
            return abs(amount_currency)
        return abs(amount_company)

    def _reconcile_with_strict_allocation(self, vals):
        payment = vals['payment']
        lines_to_reconcile = vals.get('to_reconcile') or self.env['account.move.line']
        valid_account_types = self.env['account.payment']._get_valid_payment_account_types()
        company_currency = payment.company_id.currency_id

        pay_lines = payment.move_id.line_ids.filtered_domain(
            [
                ('parent_state', '=', 'posted'),
                ('account_type', 'in', valid_account_types),
                ('reconciled', '=', False),
            ]
        )
        if not pay_lines:
            _logger.warning(
                "Strict allocation skipped: no payable/receivable lines on payment %s",
                payment.id,
            )
            return

        allocations = self.allocation_line_ids.filtered(
            lambda alloc: alloc.move_line_id in lines_to_reconcile
            and not self.currency_id.is_zero(alloc.amount_to_pay)
        )
        if not allocations:
            _logger.info(
                "Strict allocation skipped: no allocation lines matched batch for payment %s",
                payment.id,
            )
            return

        matched_moves = self.env['account.move']
        for alloc in allocations:
            inv_line = alloc.move_line_id
            if inv_line.reconciled:
                continue

            amount_left = abs(alloc.amount_to_pay)
            if self.currency_id.is_zero(amount_left):
                continue

            candidate_pay_lines = pay_lines.filtered(
                lambda line: (
                    not line.reconciled
                    and line.account_id == inv_line.account_id
                    and (line.partner_id == inv_line.partner_id or self.group_payment)
                    and line.balance
                    and inv_line.balance
                    and line.balance * inv_line.balance < 0
                )
            )
            if not candidate_pay_lines:
                candidate_pay_lines = pay_lines.filtered(
                    lambda line: (
                        not line.reconciled
                        and line.account_id == inv_line.account_id
                        and (line.partner_id == inv_line.partner_id or self.group_payment)
                    )
                )
            if not candidate_pay_lines:
                _logger.warning(
                    "Strict allocation skipped line %s: no matching payment line (account/partner).",
                    inv_line.id,
                )
                continue

            for pay_line in candidate_pay_lines:
                if inv_line.reconciled:
                    break

                inv_available = abs(inv_line.amount_residual)
                pay_available = abs(pay_line.amount_residual)
                amount_company = min(amount_left, inv_available, pay_available)
                if company_currency.is_zero(amount_company):
                    continue

                if inv_line.balance > 0:
                    debit_line = inv_line
                    credit_line = pay_line
                else:
                    debit_line = pay_line
                    credit_line = inv_line

                self.env['account.partial.reconcile'].create(
                    {
                        'debit_move_id': debit_line.id,
                        'credit_move_id': credit_line.id,
                        'amount': abs(amount_company),
                        'debit_amount_currency': self._compute_partial_amount_currency(
                            debit_line, amount_company
                        ),
                        'credit_amount_currency': self._compute_partial_amount_currency(
                            credit_line, amount_company
                        ),
                    }
                )
                matched_moves |= inv_line.move_id
                amount_left -= amount_company
                if company_currency.is_zero(amount_left):
                    break

            if not company_currency.is_zero(amount_left):
                _logger.warning(
                    "Strict allocation partial leftover %.6f on invoice line %s (payment %s).",
                    amount_left,
                    inv_line.id,
                    payment.id,
                )

        if matched_moves:
            matched_moves.matched_payment_ids += payment

    def _reconcile_payments(self, to_process, edit_mode=False):
        if self._context.get("is_group_payment"):
            return super()._reconcile_payments(to_process, edit_mode=edit_mode)

        if not self.is_multi_allocation_enabled or not self.allocation_line_ids:
            return super()._reconcile_payments(to_process, edit_mode=edit_mode)

        fallback_to_core = []
        valid_account_types = self.env['account.payment']._get_valid_payment_account_types()

        for vals in to_process:
            if self._is_fx_reconcile_context(vals):
                payment = vals['payment']
                _logger.info(
                    "Multi-allocation fallback to core reconcile for payment %s due to FX/manual-rate context.",
                    payment.id,
                )
                fallback_to_core.append(vals)
                continue
            self._reconcile_with_strict_allocation(vals)

            payment = vals['payment']
            remaining_pay_lines = payment.move_id.line_ids.filtered_domain([
                ('parent_state', '=', 'posted'),
                ('account_type', 'in', valid_account_types),
                ('reconciled', '=', False),
            ]).filtered(lambda line: line.account_id == payment.destination_account_id)
            if remaining_pay_lines:
                if self.env.context.get('skip_multi_allocation_core_fallback'):
                    _logger.info(
                        "Strict allocation left unreconciled AR lines on payment %s; "
                        "core fallback skipped by context.",
                        payment.id,
                    )
                    continue
                _logger.info(
                    "Strict allocation left unreconciled AR lines on payment %s, "
                    "falling back to core reconcile for remaining lines.",
                    payment.id,
                )
                fallback_to_core.append(vals)

        if fallback_to_core:
            return super()._reconcile_payments(
                fallback_to_core, edit_mode=edit_mode
            )
        return True
