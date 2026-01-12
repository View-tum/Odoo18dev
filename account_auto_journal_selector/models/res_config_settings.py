from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    auto_local_journal_id = fields.Many2one(
        'account.journal',
        related='company_id.auto_local_journal_id',
        readonly=False,
        domain=[('type', '=', 'sale')]
    )
    auto_foreign_journal_id = fields.Many2one(
        'account.journal',
        related='company_id.auto_foreign_journal_id',
        readonly=False,
        domain=[('type', '=', 'sale')]
    )
