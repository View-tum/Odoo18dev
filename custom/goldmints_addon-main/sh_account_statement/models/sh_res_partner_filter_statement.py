# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import fields, models

class FilterCustomerStateMent(models.Model):
    _name = "sh.res.partner.filter.statement"
    _description = "Filter Customer Statement"

    partner_id = fields.Many2one("res.partner", "Partner")
    name = fields.Char("Invoice Number")
    currency_id = fields.Many2one("res.currency", "Currency")
    sh_account = fields.Char("Account")
    sh_filter_invoice_date = fields.Date("Invoice Date")
    sh_filter_due_date = fields.Date("Invoice Due Date")
    sh_filter_amount = fields.Monetary("Total Amount")
    sh_filter_paid_amount = fields.Monetary("Paid Amount")
    sh_filter_balance = fields.Monetary("Balance")
