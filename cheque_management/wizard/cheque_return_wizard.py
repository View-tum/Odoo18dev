# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ChequeReturnWizard(models.TransientModel):
    _name = 'cheque.return.wizard'
    _description = 'Cheque Return Wizard'

    partner_id = fields.Many2one('res.partner', 'Partner')
    return_account_id = fields.Many2one('account.account', 'Return Account')
    is_change_account_return = fields.Boolean("Change Account Return", default=False)
    void_reason = fields.Char("Void Reason")

    @api.model
    def default_get(self, fields):
        rec = super(ChequeReturnWizard, self).default_get(fields)
        cheque_in_out_bound_obj = self.env['cheque.inbound.outbound'].browse(self._context.get('active_ids'))
        rec['partner_id'] = cheque_in_out_bound_obj.pay_partner_id.id

        if cheque_in_out_bound_obj.cheque_type == 'inbound':
            if cheque_in_out_bound_obj.payment_method_line_id.outgoing_cheque_account_id:
                rec['return_account_id'] = cheque_in_out_bound_obj.payment_method_line_id.outgoing_cheque_account_id.id
            else:
                rec['return_account_id'] = cheque_in_out_bound_obj.pay_partner_id.property_account_payable_id.id

        if cheque_in_out_bound_obj.cheque_type == 'outbound':
            if cheque_in_out_bound_obj.payment_method_line_id.incoming_cheque_account_id:
                rec['return_account_id'] = cheque_in_out_bound_obj.payment_method_line_id.incoming_cheque_account_id.id
            else:
                rec['return_account_id'] = cheque_in_out_bound_obj.pay_partner_id.property_account_receivable_id.id
        return rec

    @api.onchange('is_change_account_return')
    def _onchange_is_change_account_return(self):
        cheque_in_out_bound_obj = self.env['cheque.inbound.outbound'].browse(self._context.get('active_ids'))
        if self.is_change_account_return:
            if cheque_in_out_bound_obj.cheque_type == 'inbound':
                self.return_account_id = self.partner_id.property_account_payable_id.id
            if cheque_in_out_bound_obj.cheque_type == 'outbound':
                self.return_account_id = self.partner_id.property_account_receivable_id.id
        else:
            if cheque_in_out_bound_obj.cheque_type == 'inbound':
                if cheque_in_out_bound_obj.payment_method_line_id.outgoing_cheque_account_id:
                    self.return_account_id = cheque_in_out_bound_obj.payment_method_line_id.outgoing_cheque_account_id.id
                else:
                    self.return_account_id = self.partner_id.property_account_payable_id.id

            if cheque_in_out_bound_obj.cheque_type == 'outbound':
                if cheque_in_out_bound_obj.payment_method_line_id.incoming_cheque_account_id:
                    self.return_account_id = cheque_in_out_bound_obj.payment_method_line_id.incoming_cheque_account_id.id
                else:
                    self.return_account_id = self.partner_id.property_account_receivable_id.id

    def action_confirm_cheque_return(self):
        cheque_in_out_bound_obj = self.env['cheque.inbound.outbound'].browse(self._context.get('active_ids'))
        cheque_in_out_bound_obj.state = 'return'
        cheque_in_out_bound_obj.cheque_id.status = 'return'
        cheque_in_out_bound_obj.void_reason = self.void_reason
        if not self.return_account_id:
            raise UserError(_('Please set Outgoing Cheque Account for Returned first from Journal'))

        # Create Journal Entries
        Move = self.env['account.move']
        if cheque_in_out_bound_obj.cheque_type == 'inbound':
            credit_line = {
                'account_id': self.return_account_id.id,
                'partner_id': cheque_in_out_bound_obj.pay_partner_id.id,
                'name': 'Return Cheque No ' + str(cheque_in_out_bound_obj.name),
                'debit': 0,
                'credit': cheque_in_out_bound_obj.amount,
                'date_maturity': cheque_in_out_bound_obj.return_date,
            }
            debit_line = {
                'account_id': cheque_in_out_bound_obj.payment_method_line_id.payment_account_id.id,
                'partner_id':  cheque_in_out_bound_obj.pay_partner_id.id,
                'name': 'Return Cheque No ' + str(cheque_in_out_bound_obj.name),
                'debit': cheque_in_out_bound_obj.amount,
                'credit': 0,
                'date_maturity': cheque_in_out_bound_obj.return_date,
            }
            move_vals = {
                'date': fields.Date.today(),
                'journal_id': cheque_in_out_bound_obj.bank_account_journal_id.id,
                'ref': 'Return Cheque No ' + str(cheque_in_out_bound_obj.name),
                'line_ids': [(0, 0, credit_line), (0, 0, debit_line)],
                'cheque_inbound_outbound_id': cheque_in_out_bound_obj.id
            }
            move_id = Move.create(move_vals)
            move_id.action_post()
            cheque_in_out_bound_obj.cheque_return_journal_move_id = move_id.id
        elif cheque_in_out_bound_obj.cheque_type == 'outbound':
            credit_line = {
                'account_id': cheque_in_out_bound_obj.payment_method_line_id.payment_account_id.id,
                'partner_id': cheque_in_out_bound_obj.pay_partner_id.id,
                'name': 'Return Cheque No ' + str(cheque_in_out_bound_obj.name),
                'debit': 0,
                'credit': cheque_in_out_bound_obj.amount,
                'date_maturity': cheque_in_out_bound_obj.return_date,
            }
            debit_line = {
                'account_id': self.return_account_id.id,
                'partner_id':  cheque_in_out_bound_obj.pay_partner_id.id,
                'name': 'Return Cheque No ' + str(cheque_in_out_bound_obj.name),
                'debit': cheque_in_out_bound_obj.amount,
                'credit': 0,
                'date_maturity': cheque_in_out_bound_obj.return_date,
            }
            move_vals = {
                'date': fields.Date.today(),
                'journal_id': cheque_in_out_bound_obj.bank_account_journal_id.id,
                'ref': 'Return Cheque No ' + str(cheque_in_out_bound_obj.name),
                'line_ids': [(0, 0, credit_line), (0, 0, debit_line)],
                'cheque_inbound_outbound_id': cheque_in_out_bound_obj.id
            }
            move_id = Move.create(move_vals)
            move_id.action_post()
            cheque_in_out_bound_obj.cheque_return_journal_move_id = move_id.id

        # Create Message
        if self.is_change_account_return:
            return_account = ''
            if cheque_in_out_bound_obj.cheque_type == 'inbound':
                return_account = cheque_in_out_bound_obj.bank_account_journal_id.default_account_id.display_name
            if cheque_in_out_bound_obj.cheque_type == 'outbound':
                return_account = cheque_in_out_bound_obj.bank_account_journal_id.default_account_id.display_name

            body_msg = 'Change Account Return by %s. <br/> Return Account : %s → %s.' % (
                self.env.user.name, return_account, self.return_account_id.display_name)
            cheque_in_out_bound_obj.message_post(body=body_msg,
                                                 message_type="notification",
                                                 subtype_id=self.env.ref("mail.mt_comment").id)
