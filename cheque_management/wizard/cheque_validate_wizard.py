# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ChequeValidateWizard(models.TransientModel):
    _name = 'cheque.validate.wizard'
    _description = 'Cheque Validate Wizard'

    bank_account_journal_id = fields.Many2one('account.journal', 'Bank Account', domain=[('type', '=', 'bank')], copy=False, tracking=True)
    payment_method_line_id = fields.Many2one('account.payment.method.line', 'Payment Method')
    filtered_payment_method_line_ids = fields.Many2many(
        'account.payment.method.line',
        compute='_compute_filtered_payment_method_line_ids',
        string='Payment Methods',
        store=True
    )

    @api.model
    def default_get(self, fields):
        rec = super(ChequeValidateWizard, self).default_get(fields)
        cheque_in_out_bound_obj = self.env['cheque.inbound.outbound'].browse(self._context.get('active_ids'))
        rec['bank_account_journal_id'] = cheque_in_out_bound_obj.bank_account_journal_id.id
        rec['payment_method_line_id'] = cheque_in_out_bound_obj.payment_method_line_id.id
        return rec

    @api.depends('bank_account_journal_id')
    def _compute_filtered_payment_method_line_ids(self):
        for rec in self:
            cheque_in_out_bound_obj = self.env['cheque.inbound.outbound'].browse(self._context.get('active_ids'))
            if cheque_in_out_bound_obj.cheque_type == 'inbound':
                inbound_payment_method_line = self.env['account.payment.method.line'].search([('journal_id', '=', rec.bank_account_journal_id.id), ('payment_type', '=', 'outbound')])
                rec.filtered_payment_method_line_ids = [(6, 0 , inbound_payment_method_line.ids)]
            if cheque_in_out_bound_obj.cheque_type == 'outbound':
                outbound_payment_method_line = self.env['account.payment.method.line'].search([('journal_id', '=', rec.bank_account_journal_id.id), ('payment_type', '=', 'inbound')])
                rec.filtered_payment_method_line_ids = [(6, 0 , outbound_payment_method_line.ids)]

    def action_cheque_validate(self):
        cheque_in_out_bound_obj = self.env['cheque.inbound.outbound'].browse(self._context.get('active_ids'))
        payment_list = []
        payment_list.append(cheque_in_out_bound_obj.id)
        if cheque_in_out_bound_obj.cheque_type == 'inbound':

            if not self.payment_method_line_id.payment_account_id:
                raise UserError(_('Please set Outgoing Cheque Account first in Journal'))

            #Create Payment
            new_payment_id = self.env['account.payment'].create({
                'payment_type': 'outbound',
                'partner_type': 'customer',
                'partner_id': cheque_in_out_bound_obj.pay_partner_id.id,
                'journal_id': self.bank_account_journal_id.id,
                'amount': cheque_in_out_bound_obj.amount,
                'cheque_id': cheque_in_out_bound_obj.id,
                'destination_account_id': self.payment_method_line_id.payment_account_id.id,
                'date': cheque_in_out_bound_obj.clearing_date,
            })
            new_payment_id.cheque_inbound_outbound_ids = [(6, 0, payment_list)]
            new_payment_id.action_validate()

            for move in new_payment_id.move_id:
                for move_line in move.line_ids:
                    if move_line.debit > 0:
                        move_line.account_id = cheque_in_out_bound_obj.payment_method_line_account_id.id
                    move_line.name = move_line.name + ' - Confirm Cheque : ' + str(cheque_in_out_bound_obj.name)

        elif cheque_in_out_bound_obj.cheque_type == 'outbound':

            if not self.payment_method_line_id.payment_account_id:
                raise UserError(_('Please set Incoming Cheque Account first in Journal'))

            #Create Payment
            new_payment_id = self.env['account.payment'].create({
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'partner_id': cheque_in_out_bound_obj.pay_partner_id.id,
                'journal_id': self.bank_account_journal_id.id,
                'amount': cheque_in_out_bound_obj.amount,
                'cheque_id': cheque_in_out_bound_obj.id,
                'destination_account_id': self.payment_method_line_id.payment_account_id.id,
                'date': cheque_in_out_bound_obj.clearing_date,
            })
            new_payment_id.cheque_inbound_outbound_ids = [(6, 0, payment_list)]
            new_payment_id.action_validate()

            for move in new_payment_id.move_id:
                for move_line in move.line_ids:
                    if move_line.credit > 0:
                        move_line.account_id = cheque_in_out_bound_obj.payment_method_line_account_id.id
                    move_line.name = move_line.name + ' - Confirm Cheque : ' + str(cheque_in_out_bound_obj.name)

        cheque_in_out_bound_obj.state = 'paid'
        cheque_in_out_bound_obj.cheque_id.status = 'paid'

        if cheque_in_out_bound_obj.payment_id.move_id and new_payment_id.move_id:
            payment_lines = cheque_in_out_bound_obj.payment_id.move_id.line_ids.filtered_domain([('reconciled', '=', False)])
            cheque_lines = new_payment_id.move_id.line_ids.filtered_domain([('reconciled', '=', False)])
            for account in cheque_lines.account_id:
                (payment_lines + cheque_lines).filtered_domain([('account_id', '=', account.id), ('reconciled', '=', False)]).reconcile()
