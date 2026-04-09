from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    property_deferred_expense_journal_id = fields.Many2one(
        "account.journal",
        string="Deferred Expense Journal",
        domain="[('type', '=', 'general')]",
        company_dependent=True,
    )
    property_deferred_expense_account_id = fields.Many2one(
        "account.account",
        string="Deferred Expense Account",
        domain="[('deprecated', '=', False)]",
        company_dependent=True,
    )
    property_deferred_revenue_journal_id = fields.Many2one(
        "account.journal",
        string="Deferred Revenue Journal",
        domain="[('type', '=', 'general')]",
        company_dependent=True,
    )
    property_deferred_revenue_account_id = fields.Many2one(
        "account.account",
        string="Deferred Revenue Account",
        domain="[('deprecated', '=', False)]",
        company_dependent=True,
    )
