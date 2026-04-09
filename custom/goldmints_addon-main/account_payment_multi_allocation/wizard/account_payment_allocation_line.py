from odoo import api, fields, models


class AccountPaymentAllocationLine(models.TransientModel):
    _name = 'account.payment.allocation.line'
    _description = 'Payment Allocation Line'

    wizard_id = fields.Many2one('account.payment.register', required=True, ondelete='cascade')
    move_line_id = fields.Many2one('account.move.line', string='Invoice Line', required=True)
    move_id = fields.Many2one('account.move', related='move_line_id.move_id', string='Invoice', readonly=True)
    currency_id = fields.Many2one('res.currency', related='wizard_id.currency_id')
    amount_total = fields.Monetary(string='Total Amount', currency_field='currency_id', compute='_compute_amounts')
    amount_residual_original = fields.Monetary(string='Current Residual', currency_field='currency_id', compute='_compute_amounts')
    amount_to_pay = fields.Monetary(string='Amount to Pay', currency_field='currency_id', readonly=False)
    amount_residual = fields.Monetary(string='Remaining Residual', currency_field='currency_id', readonly=False)


    @api.onchange('amount_to_pay')
    def _onchange_amount_to_pay(self):
        for line in self:
            line.amount_residual = line.amount_residual_original - line.amount_to_pay

    @api.onchange('amount_residual')
    def _onchange_amount_residual(self):
        for line in self:
            line.amount_to_pay = line.amount_residual_original - line.amount_residual

    @api.depends(
        'wizard_id.currency_id',
        'wizard_id.payment_date',
        'wizard_id.manual_currency_rate',
        'wizard_id.manual_currency_rate_active',
        'move_line_id'
    )
    def _compute_amounts(self):
        for line in self:
            wizard = line.wizard_id
            move_line = line.move_line_id
            previous_amount_to_pay = line.amount_to_pay
            previous_amount_residual = line.amount_residual
            previous_residual_original = line.amount_residual_original
            if not move_line or not wizard.currency_id:
                line.amount_total = 0.0
                line.amount_residual_original = 0.0
                if not line.amount_to_pay and not line.amount_residual:
                    line.amount_to_pay = 0.0
                    line.amount_residual = 0.0
                continue

            is_credit_note = move_line.move_id.move_type in ('out_refund', 'in_refund')
            sign = -1 if is_credit_note else 1

            company_currency = move_line.company_id.currency_id
            line_currency = move_line.currency_id or move_line.move_id.currency_id or company_currency
            payment_date = wizard.payment_date or fields.Date.context_today(wizard)
            manual_rate = getattr(wizard, 'manual_currency_rate', 1.0)
            manual_active = bool(getattr(wizard, 'manual_currency_rate_active', False) and manual_rate)

            if line_currency.id == wizard.currency_id.id:
                if move_line.currency_id:
                    amount_total = abs(move_line.amount_currency)
                    amount_residual = abs(move_line.amount_residual_currency)
                elif line_currency == company_currency:
                    amount_total = abs(move_line.balance)
                    amount_residual = abs(move_line.amount_residual)
                else:
                    # Some custom flows keep company-currency residuals without line currency;
                    # convert explicitly to avoid showing company amounts as foreign amounts.
                    amount_total = abs(company_currency._convert(
                        abs(move_line.balance), wizard.currency_id, move_line.company_id, payment_date
                    ))
                    amount_residual = abs(company_currency._convert(
                        abs(move_line.amount_residual), wizard.currency_id, move_line.company_id, payment_date
                    ))
            elif manual_active and line_currency == company_currency:
                is_inverted = self.env['ir.config_parameter'].sudo().get_param(
                    'bi_manual_currency_exchange_rate.inverted_rate'
                ) == 'True'
                if is_inverted:
                    amount_total = abs(move_line.balance) / manual_rate
                    amount_residual = abs(move_line.amount_residual) / manual_rate
                else:
                    amount_total = abs(move_line.balance) * manual_rate
                    amount_residual = abs(move_line.amount_residual) * manual_rate
            else:
                if move_line.currency_id and move_line.currency_id != company_currency:
                    amount_total = abs(move_line.currency_id._convert(
                        abs(move_line.amount_currency), wizard.currency_id, move_line.company_id, payment_date
                    ))
                    amount_residual = abs(move_line.currency_id._convert(
                        abs(move_line.amount_residual_currency), wizard.currency_id, move_line.company_id, payment_date
                    ))
                else:
                    amount_total = abs(company_currency._convert(
                        abs(move_line.balance), wizard.currency_id, move_line.company_id, payment_date
                    ))
                    amount_residual = abs(company_currency._convert(
                        abs(move_line.amount_residual), wizard.currency_id, move_line.company_id, payment_date
                    ))

            line.amount_total = sign * wizard.currency_id.round(amount_total)
            new_residual_original = sign * wizard.currency_id.round(amount_residual)
            line.amount_residual_original = new_residual_original

            # Keep allocation ratio when currency/rate/date changes in the payment wizard.
            allocation_total = previous_amount_to_pay + previous_amount_residual
            if not wizard.currency_id.is_zero(allocation_total):
                paid_ratio = abs(previous_amount_to_pay) / abs(allocation_total)
            elif not wizard.currency_id.is_zero(previous_residual_original):
                paid_ratio = abs(previous_amount_to_pay) / abs(previous_residual_original)
            else:
                paid_ratio = None

            if paid_ratio is not None:
                paid_ratio = min(max(paid_ratio, 0.0), 1.0)
                new_amount_to_pay = wizard.currency_id.round(
                    abs(new_residual_original) * paid_ratio
                )
                if new_residual_original < 0:
                    new_amount_to_pay *= -1
                line.amount_to_pay = new_amount_to_pay
                line.amount_residual = new_residual_original - new_amount_to_pay
