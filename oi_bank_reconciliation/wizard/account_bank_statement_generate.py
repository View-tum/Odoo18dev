from odoo import models, fields
from odoo.fields import Command

class AccountBankStatementGenerate(models.TransientModel):
    _name = "account.bank.statement.generate"
    _description = 'Bank Statement Generate Wizard'
    
    statement_id = fields.Many2one('account.bank.statement', required = True, ondelete='cascade')
    journal_id = fields.Many2one(related='statement_id.journal_id')
    payment_ids = fields.Many2many('account.payment')
    move_line_ids = fields.Many2many('account.move.line')
    
    
    def process(self):
        for payment in self.payment_ids:
            self.env['account.bank.statement.line'].create({
                'statement_id' : self.statement_id.id,
                'payment_ref' : payment.name,
                'ref' : payment.payment_reference,
                'amount' : payment.currency_id._convert(payment.amount_signed, self.statement_id.currency_id, self.statement_id.company_id, payment.date or fields.Date.today()),
                'matched_payment_ids' : [Command.set(payment.ids)],
                'date' : payment.date,
                'partner_id' : payment.partner_id.id,
                'foreign_currency_id' : payment.currency_id.id if payment.currency_id != self.statement_id.currency_id else False,
                })
        
        for line in self.move_line_ids:                        
            amount_residual = line.currency_id._convert(line.amount_residual_currency, self.statement_id.currency_id, self.statement_id.company_id, self.statement_id.date or fields.Date.today())
            self.env['account.bank.statement.line'].create({
                'statement_id' : self.statement_id.id,
                'payment_ref' : line.move_id.name,
                'ref' : line.move_id.ref,
                'amount' : self.statement_id.currency_id.round(amount_residual),
                'matched_move_line_ids' : [Command.set(line.ids)],
                'date' : line.date,
                'partner_id' : line.partner_id.id,
                'foreign_currency_id' : line.currency_id.id if line.currency_id != self.statement_id.currency_id else False,                
                })
            