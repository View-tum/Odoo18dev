from odoo import api, fields, models

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    manufacturing_type = fields.Selection([
        ('plastic', 'Plastic'),
        ('pharma', 'Pharma'),
        ('packaging', 'Packaging'),
    ], string='Manufacturing Type', readonly=True, copy=False)

    def _get_manufacturing_type_from_group(self, group_id):
        if not group_id:
            return False

        productions = self.env['mrp.production'].search([
            ('procurement_group_id', '=', group_id),
        ])
        manufacturing_types = {
            production.manufacturing_type
            for production in productions
            if production.manufacturing_type
        }
        return manufacturing_types.pop() if len(manufacturing_types) == 1 else False
