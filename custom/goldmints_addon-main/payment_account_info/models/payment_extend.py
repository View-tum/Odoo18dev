from odoo import models, fields

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    journal_account_code = fields.Char(
        related='journal_id.default_account_id.code', 
        string='Account Code', 
        store=True
    )
    journal_account_name = fields.Char(
        related='journal_id.default_account_id.name', 
        string='Account Name', 
        store=True,
        translate=True
    )