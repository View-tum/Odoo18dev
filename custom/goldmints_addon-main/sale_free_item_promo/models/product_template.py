# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class ProductTemplate(models.Model):
    _inherit = "product.template"

    free_item_product_id = fields.Many2one(
        "product.product",
        string="Free Item",
        help="(365 custom) When this product is sold, add this free product to the order (if the customer is eligible).",
    )
    buy_item_qty = fields.Float(
        string="Quantity to Buy",
        default=1.0,
        help="(365 custom) The quantity of this product a customer must purchase to be eligible for the free item.",
    )
    free_item_qty = fields.Float(
        string="Free Item Qty per Unit",
        default=1.0,
        help="(365 custom) Quantity of the free product to add per 1 unit of this product on the order.",
    )
    enable_free_item = fields.Boolean(
        string="Enable Free Item Promo",
        help="(365 custom) Enable/disable free item promotion for this product.",
    )