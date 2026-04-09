# account_accrual_wizard/models/product.py
from odoo import fields, models


class ProductCategory(models.Model):
    _inherit = "product.category"

    property_account_accrual_id = fields.Many2one(
        "account.account",
        string="Accrual Account",
        company_dependent=True,
        domain="[('deprecated', '=', False)]",
        help="Account used for Accruals (Credit side) when creating accruals for products in this category.",
    )


class ProductTemplate(models.Model):
    _inherit = "product.template"

    property_account_accrual_id = fields.Many2one(
        "account.account",
        string="Accrual Account",
        company_dependent=True,
        domain="[('deprecated', '=', False)]",
        help="Account used for Accruals (Credit side). If empty, uses the category account.",
    )
