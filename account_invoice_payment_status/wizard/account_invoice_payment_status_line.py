# -*- coding: utf-8 -*-
from odoo import models, fields


class AccountInvoicePaymentStatusLine(models.TransientModel):
    _name = "account.invoice.payment.status.line"
    _description = "Account Invoice Payment Status Line"
    _order = "invoice_date desc"

    wizard_id = fields.Many2one(
        comodel_name="account.invoice.payment.status",
        ondelete="cascade",
        help="(365 custom) Reference to the parent payment status wizard.",
    )
    invoice_id = fields.Many2one(
        comodel_name="account.move",
        string="Invoice",
        required=True,
        help="(365 custom) The invoice record associated with this line.",
    )
    partner_id = fields.Many2one(
        related="invoice_id.partner_id",
        string="Customer",
        store=True,
        help="(365 custom) The customer associated with the invoice.",
    )
    currency_id = fields.Many2one(
        related="invoice_id.currency_id",
        readonly=True,
        help="(365 custom) The currency used for the invoice amount.",
    )
    invoice_name = fields.Char(
        related="invoice_id.name",
        string="Number",
        help="(365 custom) The invoice number.",
    )
    invoice_date = fields.Date(
        related="invoice_id.invoice_date",
        string="Invoice Date",
        help="(365 custom) The date when the invoice was issued.",
    )
    invoice_date_due = fields.Date(
        related="invoice_id.invoice_date_due",
        string="Due Date",
        help="(365 custom) The date by which the invoice should be paid.",
    )
    amount_total = fields.Monetary(
        related="invoice_id.amount_total",
        string="Total",
        currency_field="currency_id",
        help="(365 custom) The total amount of the invoice.",
    )
    amount_residual = fields.Monetary(
        related="invoice_id.amount_residual",
        string="Amount Due",
        currency_field="currency_id",
        help="(365 custom) The remaining amount to be paid on the invoice.",
    )
    payment_state = fields.Selection(
        related="invoice_id.payment_state",
        string="Payment Status",
        help="(365 custom) The current payment status of the invoice (e.g., Paid, Not Paid, In Payment).",
    )
    payment_date = fields.Date(
        related="invoice_id.date",
        string="Payment Date",
        help="(365 custom) The date of the last payment associated with this invoice.",
    )
    statement_date = fields.Date(
        string="Statement Date",
        help="(365 custom) The reconciled date from the bank statement.",
    )
