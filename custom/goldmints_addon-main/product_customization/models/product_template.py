from odoo import _, api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"
    
    gross_weight = fields.Float('Gross Weight Per Carton', help="(365 custom) Gross Weight")
    net_weight = fields.Float('Net Weight Per Carton', help="(365 custom) Net Weight")
    dimension = fields.Char('DIMS', help="(365 custom) Dimension")
    number_of_cartons = fields.Integer('Number of Cartons', help="(365 custom)Show total count of cartons")