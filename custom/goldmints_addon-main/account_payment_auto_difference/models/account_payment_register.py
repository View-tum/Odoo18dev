# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    @api.onchange('payment_difference')
    def _onchange_payment_difference_auto_deduction(self):
        for wizard in self:
            if not wizard.company_id.auto_diff_account_id:
                continue

            # If the difference is zero, optionally we could clear the auto-line,
            # but usually it's safer to let the user clear it if they want.
            if wizard.currency_id.is_zero(wizard.payment_difference):
                continue

            auto_account = wizard.company_id.auto_diff_account_id
            auto_label = wizard.company_id.auto_diff_label or 'Difference'
            auto_analytic = wizard.company_id.auto_diff_analytic_distribution or {}

            # Case 1: No deductions exist at all. Auto-populate a new one.
            if not wizard.deduction_ids:
                wizard.payment_difference_handling = 'reconcile_multi_deduct'
                wizard.deduction_ids = [(0, 0, {
                    'account_id': auto_account.id,
                    'name': auto_label,
                    'amount': wizard.payment_difference,
                    'analytic_distribution': auto_analytic,
                    'is_open': False,
                })]
            else:
                # Case 2: Deductions exist. If one matches our auto-account, update its amount
                # to absorb the remaining difference to keep it balanced.
                auto_lines = wizard.deduction_ids.filtered(lambda d: d.account_id == auto_account)
                if auto_lines:
                    auto_line = auto_lines[0]
                    other_deductions_amount = sum(wizard.deduction_ids.mapped('amount')) - auto_line.amount
                    new_amount = wizard.payment_difference - other_deductions_amount
                    auto_line.amount = new_amount
