# -*- coding: utf-8 -*-
from odoo import models, fields


class AccountAgedReceiveableExtensionLine(models.TransientModel):
    _name = "account.aged.receiveable.extension.line"
    _description = "Aged Receivable Report Line"
    _order = "days_overdue desc, invoice_date desc"

    wizard_id = fields.Many2one(
        "account.aged.receiveable.extension", string="Wizard", ondelete="cascade"
    )
    invoice_id = fields.Many2one("account.move", string="Invoice")
    partner_id = fields.Many2one("res.partner", string="Partner")
    invoice_date = fields.Date(string="Invoice Date")
    date_maturity = fields.Date(string="Due Date")
    invoice_currency_id = fields.Many2one("res.currency", string="Inv. Currency")
    payment_term_id = fields.Many2one("account.payment.term", string="Payment Term")
    amount_residual = fields.Monetary(string="Balance")
    currency_id = fields.Many2one("res.currency", string="Currency")
    days_overdue = fields.Integer(string="Days Overdue")
    amount_not_due = fields.Monetary(string="Current")
    amount_1_30 = fields.Monetary(string="1-30 Days")
    amount_31_60 = fields.Monetary(string="31-60 Days")
    amount_61_90 = fields.Monetary(string="61-90 Days")
    amount_over_90 = fields.Monetary(string="Over 90 Days")
