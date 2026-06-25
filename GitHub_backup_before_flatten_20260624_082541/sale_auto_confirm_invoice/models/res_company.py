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
    mobile_cash_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Cash Journal",
        domain=[("type", "=", "cash")],
        help="Journal used when mobile warehouse invoices use the Cash payment method.",
        check_company=True,
    )
    mobile_cheque_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Cheque Journal",
        domain=[("type", "in", ("bank", "cash"))],
        help="Journal used when mobile warehouse invoices use the Cheque payment method.",
        check_company=True,
    )
    mobile_bank_transfer_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Bank Transfer Journal",
        domain=[("type", "in", ("bank", "cash"))],
        help="Journal used when mobile warehouse invoices use the Bank Transfer payment method.",
        check_company=True,
    )


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    downpayment_account_id = fields.Many2one(
        related="company_id.downpayment_account_id", readonly=False
    )
    mobile_cash_journal_id = fields.Many2one(related="company_id.mobile_cash_journal_id", readonly=False)
    mobile_cheque_journal_id = fields.Many2one(related="company_id.mobile_cheque_journal_id", readonly=False)
    mobile_bank_transfer_journal_id = fields.Many2one(related="company_id.mobile_bank_transfer_journal_id", readonly=False)
