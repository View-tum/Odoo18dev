from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    enable_multi_invoice_allocation = fields.Boolean(
        string="Enable Multi-Invoice Allocation Table",
        default=True
    )
