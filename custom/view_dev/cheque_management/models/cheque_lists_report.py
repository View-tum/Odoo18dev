from odoo import fields, models, api


class ChequeListsHistory(models.Model):
    _name = "cheque.lists.history"
    _description = " Helps to track cheque book Data"
    _order = 'date'
    _rec_name = "cheque_book_no"

    cheque_book_no = fields.Char('Cheque Book No')
    bank_account_journal_id = fields.Many2one('account.journal', 'Bank Account', domain=[('type', '=', 'bank')])
    date = fields.Date('Date')

    cheque_book_id = fields.Many2one('cheque.book', 'Cheque Book')
    cheque_no = fields.Char('Cheque No')
    cheque_date = fields.Date('Cheque Date')
    pay_to = fields.Many2one('res.partner', 'Pay To')
    amount = fields.Monetary('Amount')
    currency_id = fields.Many2one('res.currency', string='Currency')
    memo = fields.Char('Memo')
    status = fields.Selection([('draft', 'Available'),
                               ('waiting_confirm', 'Waiting Confirm'),
                               ('confirmed', 'Confirmed'),
                               ('return', 'Return'),
                               ('paid', 'Paid'),
                               ('cancelled', 'Cancelled')], string='Status')
    company_id = fields.Many2one('res.company', string='Company')
