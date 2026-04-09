from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    banker_info = fields.Text(
        string='Bank Details for Remittance',
        help='(365Custom)Bank information shown on reports'
    )
