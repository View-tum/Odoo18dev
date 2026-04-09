# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import  fields, models

class VendorDueStateMent(models.Model):
    _name = "sh.vendor.due.statement"
    _description = "Vendor Due Statement"

    partner_id = fields.Many2one("res.partner", "Partner")
    name = fields.Char("Bill Number")
    currency_id = fields.Many2one("res.currency", "Currency")
    sh_account = fields.Char("Account")
    sh_due_vendor_invoice_date = fields.Date("Bill Date")
    sh_today = fields.Date("Today")
    sh_due_vendor_due_date = fields.Date("Bill Due Date")
    sh_due_vendor_amount = fields.Monetary("Total Amount")
    sh_due_vendor_paid_amount = fields.Monetary("Paid Amount")
    sh_due_vendor_balance = fields.Monetary("Balance")
