from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    mrp_scrap_landed_cost_product_id = fields.Many2one(
        related='company_id.mrp_scrap_landed_cost_product_id',
        readonly=False,
    )
