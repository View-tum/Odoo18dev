from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    is_reverse_cheque_entry = fields.Boolean(
        'Is Reverse Cheque Entry?', related='company_id.is_reverse_cheque_entry', readonly=False)
    cheque_auto_reconcile_threshold = fields.Float(
        'Cheque Auto Reconcile Threshold', related='company_id.cheque_auto_reconcile_threshold', readonly=False)
    cheque_rounding_account_id = fields.Many2one(
        'account.account', string='Cheque Rounding Account', related='company_id.cheque_rounding_account_id', readonly=False)
