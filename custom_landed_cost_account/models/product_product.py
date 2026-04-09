from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    landed_cost_account_id = fields.Many2one(
        "account.account",
        string="Landed Cost Account",
        help="Account used for Landed Cost when this product is selected.",
        domain="[('deprecated', '=', False)]",
    )
