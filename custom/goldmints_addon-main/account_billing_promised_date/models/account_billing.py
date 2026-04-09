from odoo import fields, models


class AccountBilling(models.Model):
    _inherit = "account.billing"

    billing_line_ids = fields.One2many(
        readonly=False,
    )


class AccountBillingLine(models.Model):
    _inherit = "account.billing.line"

    promised_payment_date = fields.Date(
        related="move_id.promised_payment_date",
        readonly=False,
    )
