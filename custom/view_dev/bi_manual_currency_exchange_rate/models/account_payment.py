# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class account_payment(models.TransientModel):
    _inherit = 'account.payment.register'

    manual_currency_rate_active = fields.Boolean('Apply Manual Exchange')
    manual_currency_rate = fields.Float('Rate', digits=(12, 6))


    def _disable_manual_rate_same_currency_warning(self):
        return {
            'warning': {
                'title': _('Manual Exchange Rate Disabled'),
                'message': _(
                    'Company currency and Payment currency are the same. '
                    'Manual exchange rate has been disabled automatically.'
                ),
            }
        }

    @api.onchange('manual_currency_rate_active', 'currency_id')
    def check_currency_id(self):
        warning = False
        for payment in self:
            if not payment.manual_currency_rate_active:
                continue
            source_is_company = payment.source_currency_id == payment.company_id.currency_id
            payment_is_company = payment.currency_id == payment.company_id.currency_id
            if source_is_company and payment_is_company:
                payment.manual_currency_rate_active = False
                payment.manual_currency_rate = 0.0
                warning = payment._disable_manual_rate_same_currency_warning()
        return warning

    @api.model
    def default_get(self, fields_list):
        # OVERRIDE
        res = super().default_get(fields_list)
        if 'line_ids' in res:
            if self._context.get('active_model') == 'account.move':
                    lines = self.env['account.move'].browse(self._context.get('active_ids', [])).line_ids
            elif self._context.get('active_model') == 'account.move.line':
                lines = self.env['account.move.line'].browse(self._context.get('active_ids', []))

            if lines:
                invoices = lines.mapped('move_id')
                # Mixed/manual-inconsistent selections should start with manual FX off
                # and let the user choose explicitly in the wizard.
                if len(set(invoices.mapped('manual_currency_rate_active'))) > 1 or len(set(invoices.mapped('manual_currency_rate'))) > 1:
                    res.update({
                        'manual_currency_rate_active': False,
                        'manual_currency_rate': 0.0,
                    })
                    return res
                res.update({
                    'manual_currency_rate_active': lines[0].move_id.manual_currency_rate_active or False,
                    'manual_currency_rate': lines[0].move_id.manual_currency_rate
                })
        return res

    @api.model
    def _create_payment_vals_from_batch(self, batch_result):
        rec = super(account_payment, self)._create_payment_vals_from_batch(batch_result)
        active_ids = self._context.get('active_ids') or self._context.get('active_id')
        active_model = self._context.get('active_model')

        # Check for selected invoices ids
        if not active_ids or active_model != 'account.move':
            return rec

        account_move = self.env['account.move'].search([('name','=',rec.get('ref'))]).ids
        for active_id in active_ids:
            if active_id in account_move:
                invoices = self.env['account.move'].browse(active_id).filtered(
                    lambda move: move.is_invoice(include_receipts=True))

                for invoice in invoices:
                    rec.update({
                        'manual_currency_rate_active': invoice.manual_currency_rate_active,
                        'manual_currency_rate': invoice.manual_currency_rate
                    })

                return rec
        return rec

    @api.depends('source_amount', 'source_amount_currency', 'source_currency_id', 'company_id', 'currency_id', 'payment_date', 'manual_currency_rate', 'manual_currency_rate_active')
    def _compute_amount(self):
        super(account_payment, self)._compute_amount()
        pass


    @api.depends('amount','manual_currency_rate', 'manual_currency_rate_active', 'can_edit_wizard', 'installments_mode')
    def _compute_payment_difference(self):
        return super()._compute_payment_difference()

    def _create_payment_vals_from_wizard(self,batch_result):

        res = super(account_payment, self)._create_payment_vals_from_wizard(batch_result)
        if self.manual_currency_rate_active:
            res.update({'manual_currency_rate_active': self.manual_currency_rate_active, 'manual_currency_rate': self.manual_currency_rate,'check_active_currency':True})
        else:
            res.update({'manual_currency_rate_active': False, 'manual_currency_rate': 0.0,'check_active_currency':False})
        return res


class AccountPayment(models.Model):
    _inherit = "account.payment"
    _description = "Payments"

    manual_currency_rate_active = fields.Boolean('Apply Manual Exchange')
    manual_currency_rate = fields.Float('Rate', digits=(12, 6))
    amount_currency = fields.Float('Amount Currency')
    check_active_currency = fields.Boolean('Check Active Currency')

    @api.onchange('manual_currency_rate_active', 'currency_id')
    def check_currency_id(self):
        warning = False
        for payment in self:
            if not payment.manual_currency_rate_active:
                continue
            move_currencies = payment.move_id.line_ids.mapped('currency_id')
            invoice_is_company = all(c == payment.company_id.currency_id for c in move_currencies) if move_currencies else True
            payment_is_company = payment.currency_id == payment.company_id.currency_id
            if invoice_is_company and payment_is_company:
                payment.manual_currency_rate_active = False
                payment.manual_currency_rate = 0.0
                warning = {
                    'warning': {
                        'title': _('Manual Exchange Rate Disabled'),
                        'message': _(
                            'Company currency and Payment currency are the same. '
                            'Manual exchange rate has been disabled automatically.'
                        ),
                    }
                }
        return warning

    def _get_trigger_fields_to_synchronize(self):
        res = super()._get_trigger_fields_to_synchronize()
        return res + ('manual_currency_rate', 'manual_currency_rate_active', 'amount_currency')

    @api.onchange('manual_currency_rate', 'manual_currency_rate_active')
    def _onchange_manual_currency_sync_move_lines(self):
        for pay in self:
            if pay.state == 'draft':
                pay._synchronize_to_moves({'manual_currency_rate', 'manual_currency_rate_active'})

    @api.model
    def default_get(self, default_fields):

        rec = super(AccountPayment, self).default_get(default_fields)
        active_ids = self._context.get('active_ids') or self._context.get('active_id')
        active_model = self._context.get('active_model')

        # Check for selected invoices ids
        if not active_ids or active_model != 'account.move':
            return rec

        invoices = self.env['account.move'].browse(active_ids).filtered(
            lambda move: move.is_invoice(include_receipts=True))


        if (len(invoices) == 1):
            rec.update({
                'manual_currency_rate_active': invoices.manual_currency_rate_active,
                'manual_currency_rate': invoices.manual_currency_rate,
            })
        return rec



    @api.depends('amount', 'currency_id', 'payment_type', 'manual_currency_rate')
    def _compute_payment_difference(self):
        return super()._compute_payment_difference()


    def _prepare_move_line_default_vals(self, write_off_line_vals=None,force_balance=None):
        return super()._prepare_move_line_default_vals(write_off_line_vals, force_balance)

    def write(self,vals):
        result = super().write(vals)
        if vals.get('amount') and vals.get('amount_currency'):
            for record in self:
                record.amount_currency = vals.get('amount')
        return result

    @api.model_create_multi
    def create(self, vals_list):
        prepared_vals_list = []
        for vals in vals_list:
            prepared_vals = dict(vals)
            # Legacy compatibility: if caller passes only custom amount_currency,
            # keep payment amount in sync before creating journal entry.
            if (
                prepared_vals.get('amount_currency') is not None
                and prepared_vals.get('amount') is None
            ):
                prepared_vals['amount'] = prepared_vals.get('amount_currency')
            prepared_vals_list.append(prepared_vals)

        records = super().create(prepared_vals_list)

        # Writing amount_currency triggers move synchronization.
        # But we just created the move correctly (with our custom FX line).
        # We must skip sync here or else Odoo rebuilds the JE and loses the FX line.
        records.with_context(skip_account_move_synchronization=True).sync_amount()
        return records

    @api.onchange('amount_currency')
    def onchange_amount_currency(self):
        for record in self:
            record.amount = record.amount_currency

    def _generate_journal_entry(self, write_off_line_vals=None, force_balance=None, line_ids=None):
        return super()._generate_journal_entry(
            write_off_line_vals=write_off_line_vals,
            force_balance=force_balance,
            line_ids=line_ids,
        )



    def sync_amount(self):
        for record in self:
            if record.manual_currency_rate_active and record.manual_currency_rate:
                if record.company_id.currency_id.id == record.currency_id.id:
                    if record.check_active_currency:
                        record.amount_currency = record.amount
                else:
                    record.amount_currency = record.amount
            else:
                record.amount_currency = record.amount
