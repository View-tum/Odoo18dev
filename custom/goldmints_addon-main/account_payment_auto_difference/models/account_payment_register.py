# -*- coding: utf-8 -*-
from odoo import Command, api, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    def _is_manual_exchange_difference_context(self):
        self.ensure_one()
        return bool(
            getattr(self, 'manual_currency_rate_active', False)
            and getattr(self, 'manual_currency_rate', 0.0)
        )

    def _get_auto_difference_label(self):
        self.ensure_one()
        return self.company_id.auto_diff_label or 'Difference'

    def _is_account_payment_auto_difference_line(self, deduction):
        self.ensure_one()
        auto_account = self.company_id.auto_diff_account_id
        if not auto_account:
            return False
        return (
            deduction.account_id == auto_account
            and (deduction.name or '') == self._get_auto_difference_label()
        )

    def _get_deduction_command_values(self, deduction):
        values = {
            'account_id': deduction.account_id.id,
            'name': deduction.name,
            'amount': deduction.amount,
            'is_open': deduction.is_open,
        }
        for field_name in (
            'analytic_distribution',
            'partner_id',
            'wht_tax_id',
            'wht_amount_base',
            'tax_base_amount',
            'currency_id',
        ):
            if field_name not in deduction._fields:
                continue
            value = deduction[field_name]
            values[field_name] = value.id if hasattr(value, 'id') else value or False
        return values

    def _cleanup_auto_difference_deductions(self):
        for wizard in self:
            auto_lines = wizard.deduction_ids.filtered(
                wizard._is_account_payment_auto_difference_line
            )
            if not auto_lines:
                continue
            keep_lines = wizard.deduction_ids - auto_lines
            wizard.deduction_ids = [Command.clear()] + [
                Command.create(wizard._get_deduction_command_values(line))
                for line in keep_lines
            ]
            if not keep_lines and wizard.payment_difference_handling == 'reconcile_multi_deduct':
                # We do NOT force it to 'open' here, because if they are using manual currency rate,
                # they STILL want the invoice to be fully paid (reconciled) with FX write-off.
                pass

    @api.onchange('payment_difference', 'manual_currency_rate_active', 'manual_currency_rate')
    def _onchange_payment_difference_auto_deduction(self):
        for wizard in self:
            if not wizard.company_id.auto_diff_account_id:
                continue

            if wizard._is_manual_exchange_difference_context():
                wizard._cleanup_auto_difference_deductions()
                if wizard.payment_difference != 0.0:
                    wizard.payment_difference_handling = 'reconcile_multi_deduct'
                continue

            if wizard.currency_id.is_zero(wizard.payment_difference):
                wizard._cleanup_auto_difference_deductions()
                continue

            auto_account = wizard.company_id.auto_diff_account_id
            auto_label = wizard._get_auto_difference_label()
            auto_analytic = wizard.company_id.auto_diff_analytic_distribution or {}

            if not wizard.deduction_ids:
                wizard.payment_difference_handling = 'reconcile_multi_deduct'
                wizard.deduction_ids = [Command.create({
                    'account_id': auto_account.id,
                    'name': auto_label,
                    'amount': wizard.payment_difference,
                    'analytic_distribution': auto_analytic,
                    'is_open': False,
                })]
            else:
                auto_lines = wizard.deduction_ids.filtered(
                    wizard._is_account_payment_auto_difference_line
                )
                if auto_lines:
                    auto_line = auto_lines[0]
                    other_deductions_amount = sum(wizard.deduction_ids.mapped('amount')) - auto_line.amount
                    auto_line.amount = wizard.payment_difference - other_deductions_amount
