# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ProductTransformRule(models.Model):
    _name = "product.transform.rule"
    _description = "Product Transformation Rule"
    _rec_name = "name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)

    product_from_id = fields.Many2one(
        "product.product",
        string="From Product",
        required=True,
        help="Source product (e.g. big box).",
    )
    product_to_id = fields.Many2one(
        "product.product",
        string="To Product",
        required=True,
        help="Target product (e.g. small box, pack, piece).",
    )

    qty_to = fields.Float(
        string="Quantity To",
        required=True,
        default=1.0,
        help="How many 'To Product' are created from 1 'From Product'.",
    )

    uom_from_id = fields.Many2one(
        "uom.uom",
        string="From UoM",
        related="product_from_id.uom_id",
        store=True,
        readonly=True,
    )
    uom_to_id = fields.Many2one(
        "uom.uom",
        string="To UoM",
        related="product_to_id.uom_id",
        store=True,
        readonly=True,
    )

    next_rule_id = fields.Many2one(
        "product.transform.rule",
        string="Next Rule",
        help="Optional next transformation rule to apply after this one.",
    )


