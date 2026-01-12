from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    precision_sale = fields.Integer(
        string="Sale Order Precision",
        config_parameter='precision_control.precision_sale',
        default=2,
    )
    precision_purchase = fields.Integer(
        string="Purchase Order Precision",
        config_parameter='precision_control.precision_purchase',
        default=3,
    )
    precision_mrp = fields.Integer(
        string="Manufacturing Order Precision",
        config_parameter='precision_control.precision_mrp',
        default=4,
    )
    precision_account = fields.Integer(
        string="Accounting Precision",
        config_parameter='precision_control.precision_account',
        default=2,
    )
    precision_stock = fields.Integer(
        string="Stock Precision",
        config_parameter='precision_control.precision_stock',
        default=6,
    )
    precision_product = fields.Integer(
        string="Product Precision",
        config_parameter='precision_control.precision_product',
        default=6,
    )
