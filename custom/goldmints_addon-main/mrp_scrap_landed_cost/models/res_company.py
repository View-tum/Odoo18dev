from odoo import fields, models

class ResCompany(models.Model):
    _inherit = 'res.company'

    mrp_scrap_landed_cost_product_id = fields.Many2one(
        'product.product',
        string="Scrap Landed Cost Service",
        domain=[('landed_cost_ok', '=', True), ('type', '=', 'service')],
        help="Service product used to auto-allocate scrap value to Landed Costs."
    )
