from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    auto_local_journal_id = fields.Many2one('account.journal', domain=[('type', '=', 'sale')])
    auto_foreign_journal_id = fields.Many2one('account.journal', domain=[('type', '=', 'sale')])
