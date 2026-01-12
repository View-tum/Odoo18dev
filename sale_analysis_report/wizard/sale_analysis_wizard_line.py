from odoo import models, fields


class SaleAnalysisReportLine(models.TransientModel):
    _name = "sale.analysis.report.line"
    _description = "Sale Analysis Detail Line"

    wizard_id = fields.Many2one("sale.analysis.report", string="Wizard")
    salesperson_id = fields.Many2one("res.users", string="Salesperson")

    # Common Fields
    sale_order_name = fields.Char("SO No.")
    customer_name = fields.Char("Customer")
    invoice_name = fields.Char("Invoice No.")
    credit_note_name = fields.Char("Credit Note No.")

    # Fields: Salesperson
    amount_sale_total = fields.Float("Sale Amount (Untaxed)")
    amount_invoice_total = fields.Float("Invoice Amount (Untaxed)")
    amount_payment_total = fields.Float("Payment Amount")
    amount_credit_note_total = fields.Float("Credit Note Amount")
    amount_commission = fields.Float("Commission Amount")

    # Fields: Market Region
    currency_name = fields.Char("Currency")
    exchange_rate = fields.Float("Exchange Rate", digits=(12, 4))
    amount_foreign = fields.Float("Amount (Foreign)")
    amount_thb = fields.Float("Amount (THB)")

    # Fields: Product & Top Ten
    product_name = fields.Char("Product Name")
    product_category_name = fields.Char("Product Category")
    product_uom_qty = fields.Float("Quantity")
    rank_type = fields.Selection(
        [("qty", "Top 10 (Qty)"), ("amount", "Top 10 (Sales)")], string="Rank Type"
    )
