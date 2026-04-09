from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    enable_multi_invoice_allocation = fields.Boolean(
        related='company_id.enable_multi_invoice_allocation',
        readonly=False
    )
