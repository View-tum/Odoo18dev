from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    auto_reconcile_reversals = fields.Boolean(
        related='company_id.auto_reconcile_reversals',
        readonly=False,
    )
