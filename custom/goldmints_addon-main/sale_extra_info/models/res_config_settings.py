from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    proforma_sequence_id = fields.Many2one(
        related='company_id.proforma_sequence_id',
        readonly=False,
        string="Proforma Sequence"
    )
