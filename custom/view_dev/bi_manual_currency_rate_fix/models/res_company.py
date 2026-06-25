from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    auto_reconcile_reversals = fields.Boolean(
        string='Auto-reconcile Credit/Debit Notes',
        default=False,
    )
