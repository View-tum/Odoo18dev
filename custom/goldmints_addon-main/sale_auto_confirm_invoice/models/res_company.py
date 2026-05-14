from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    downpayment_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Down Payment Account",
        domain=[
            ("deprecated", "=", False),
            ("account_type", "in", ("income", "income_other", "liability_current", "liability_non_current")),
        ],
        help="Default account used on down payment invoices (percentage or fixed amount).",
        check_company=True,
    )
    cash_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Cash Account",
        domain=[("deprecated", "=", False), ("account_type", "in", ("asset_cash", "asset_receivable"))],
        help=(
            "Account used when mobile warehouse invoices use the Cash payment method. "
            "Use a receivable account for Create Invoice (Posted) and a cash/bank account for Create Invoice Paid."
        ),
        check_company=True,
    )
    cheque_and_bank_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Cheque/Bank Account",
        domain=[("deprecated", "=", False), ("account_type", "in", ("asset_cash", "asset_receivable"))],
        help=(
            "Account used when mobile warehouse invoices use the Cheque/Bank payment method. "
            "Use a receivable account for Create Invoice (Posted) and a cash/bank account for Create Invoice Paid."
        ),
        check_company=True,
    )

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    downpayment_account_id = fields.Many2one(
        related="company_id.downpayment_account_id", readonly=False
    )
    cash_account_id = fields.Many2one(related="company_id.cash_account_id", readonly=False)
    cheque_and_bank_account_id = fields.Many2one(
        related="company_id.cheque_and_bank_account_id", readonly=False
    )
