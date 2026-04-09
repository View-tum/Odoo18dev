from odoo import api, fields, models

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    asset_model_id = fields.Many2one('account.asset', ' Asset Model', help='Asset category that will be used to create assets for this product.')
    
    
class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    asset_model_id = fields.Many2one('account.asset', ' Asset Model', help='Asset category that will be used to create assets for this product.')