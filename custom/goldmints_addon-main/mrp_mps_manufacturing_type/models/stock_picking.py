from odoo import models, fields, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    manufacturing_type = fields.Selection([
        ('plastic', 'Plastic'),
        ('pharma', 'Pharma'),
        ('packaging', 'Packaging'),
    ], string='Manufacturing Type', readonly=True, copy=False)
