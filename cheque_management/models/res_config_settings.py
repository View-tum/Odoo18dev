from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    is_reverse_cheque_entry = fields.Boolean(
        'Is Reverse Cheque Entry?', related='company_id.is_reverse_cheque_entry', readonly=False)
