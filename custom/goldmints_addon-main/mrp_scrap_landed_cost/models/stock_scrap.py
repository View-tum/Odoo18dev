from odoo import fields, models


class StockScrap(models.Model):
    _inherit = "stock.scrap"

    landed_cost_id = fields.Many2one(
        "stock.landed.cost",
        string="Absorbed by Landed Cost",
        readonly=True,
        help="The Landed Cost that absorbed this scrap cost.",
    )
