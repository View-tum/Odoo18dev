from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    dynamic_cheque_id = fields.Many2many('dynamic.cheque', string="Cheque Form", tracking=True)
    is_cheque_incoming = fields.Boolean('Cheque Incoming')
    is_cheque_outgoing = fields.Boolean('Cheque Outgoing')
    is_bank_draft_incoming = fields.Boolean('Bank Draft Incoming')
    is_bank_draft_outgoing = fields.Boolean('Bank Draft Outgoing')


class AccountPaymentMethod(models.Model):
    _inherit = 'account.payment.method'

    @api.model
    def _get_payment_method_information(self):
        res = super(AccountPaymentMethod, self)._get_payment_method_information()
        update_cheque_data = {
            'cheque': {'mode': 'multi', 'type': ('bank', 'cash', 'credit')},
            'bank_draft': {'mode': 'multi', 'type': ('bank', 'cash', 'credit')},
        }
        res.update(update_cheque_data)
        return res


class AccountPaymentMethodLine(models.Model):
    _inherit = 'account.payment.method.line'

    filtered_payment_account_ids = fields.Many2many(
        'account.account',
        compute='_compute_filtered_payment_account_ids',
        string='Accounts',
        store=True
    )
    payment_account_id = fields.Many2one(
        'account.account',
        check_company=True,
        copy=False,
        ondelete='restrict',
        tracking=True,
        domain="[('id', 'in', filtered_payment_account_ids)]"
    )

    is_cheque_incoming = fields.Boolean('Cheque Incoming', related='journal_id.is_cheque_incoming')
    is_cheque_outgoing = fields.Boolean('Cheque Outgoing', related='journal_id.is_cheque_outgoing')
    is_bank_draft_incoming = fields.Boolean('Bank Draft Incoming', related='journal_id.is_bank_draft_incoming')
    is_bank_draft_outgoing = fields.Boolean('Bank Draft Outgoing', related='journal_id.is_bank_draft_outgoing')

    # Incoming Payments
    is_cheque_incoming_line = fields.Boolean('Is Cheque')
    incoming_cheque_account_id = fields.Many2one('account.account', 'Incoming Cheque Void')

    # Outgoing Payments
    is_cheque_outgoing_line = fields.Boolean('Is Cheque')
    outgoing_cheque_account_id = fields.Many2one('account.account', 'Outgoing Cheque Void')
    is_bank_draft_incoming_line = fields.Boolean('Is Bank Draft')
    is_bank_draft_outgoing_line = fields.Boolean('Is Bank Draft')

    @api.depends('payment_method_id')
    def _compute_filtered_payment_account_ids(self):
        # # , ('id', '=', rec.default_account_id.id)Pai comment for non cheque
        for rec in self:
            if rec.payment_method_id and rec.payment_method_id.code != 'cheque':
                account_ids = self.env['account.account'].search([
                    ('deprecated', '=', False),
                    ('account_type', 'in', ('asset_current', 'liability_current', 'asset_cash', 'asset_receivable', 'liability_payable')),
                ])
                rec.filtered_payment_account_ids = [(6, 0 , account_ids.ids)]
            else:
                account_ids = self.env['account.account'].search([('deprecated', '=', False)])
                rec.filtered_payment_account_ids = [(6, 0 , account_ids.ids)]
