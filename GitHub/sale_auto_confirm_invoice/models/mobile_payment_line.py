from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleAdvancePaymentInvMobileLine(models.TransientModel):
    _name = "sale.advance.payment.inv.mobile.line"
    _description = "Mobile Invoice Payment Line"
    _order = "sequence, id"

    wizard_id = fields.Many2one(
        "sale.advance.payment.inv", required=True, ondelete="cascade"
    )
    sequence = fields.Integer(default=10)
    payment_type = fields.Selection(
        [
            ("bank", "Bank"),
            ("cash", "Cash"),
            ("cheque", "Cheque"),
            ("rounding", "ปัดเศษ"),
        ],
        string="Payment Type",
        required=True,
        default="cash",
    )
    is_rounding = fields.Boolean(compute="_compute_is_rounding")
    amount = fields.Monetary(required=True, currency_field="currency_id")
    currency_id = fields.Many2one(
        "res.currency", related="wizard_id.currency_id", readonly=True
    )
    cheque_number = fields.Char(string="Cheque Number")
    cheque_bank_id = fields.Many2one("res.bank", string="Cheque Bank")
    cheque_branch = fields.Char(string="Cheque Branch")
    cheque_date = fields.Date(
        string="Cheque Date", default=fields.Date.context_today
    )

    journal_account_name = fields.Char(compute="_compute_journal_account_name")

    @api.depends("payment_type")
    def _compute_is_rounding(self):
        for line in self:
            line.is_rounding = line.payment_type == "rounding"

    @api.depends("payment_type")
    def _compute_journal_account_name(self):
        for line in self:
            if not line.wizard_id or not line.payment_type:
                line.journal_account_name = ""
                continue
            if line.payment_type == "rounding":
                company = line.wizard_id._get_target_company()
                line.journal_account_name = (
                    company.auto_diff_account_id.display_name
                    if company.auto_diff_account_id
                    else _("ส่วนต่างรับชำระ / Auto Difference")
                )
            else:
                try:
                    journal = line.wizard_id._get_mobile_payment_journal_for_type(line.payment_type)
                    line.journal_account_name = journal.display_name if journal else ""
                except UserError:
                    line.journal_account_name = ""

    @api.constrains("amount")
    def _check_amount_positive(self):
        for line in self:
            if line.amount <= 0:
                raise UserError(_("Payment row amount must be greater than zero."))


class SaleAdvancePaymentInvCreditNoteLine(models.TransientModel):
    _name = "sale.advance.payment.inv.credit.note.line"
    _description = "Sale Payment Credit Note Line"
    _order = "date, move_id, id"

    wizard_id = fields.Many2one(
        "sale.advance.payment.inv", required=True, ondelete="cascade"
    )
    is_selected = fields.Boolean(string="Select")
    move_id = fields.Many2one("account.move", string="Credit Note")
    date = fields.Date(related="move_id.invoice_date", string="Date", readonly=True)
    account_id = fields.Many2one("account.account", string="Account", readonly=True)
    open_amount = fields.Monetary(string="Open Amount", currency_field="currency_id")
    amount = fields.Monetary(string="Apply Amount", currency_field="currency_id")
    currency_id = fields.Many2one(
        "res.currency", related="wizard_id.currency_id", readonly=True
    )

    @api.onchange("is_selected")
    def _onchange_is_selected(self):
        for line in self:
            line.amount = line.open_amount if line.is_selected else 0.0

    @api.constrains("amount")
    def _check_amount(self):
        for line in self:
            if not line.move_id:
                continue
            currency = line.currency_id or line.env.company.currency_id
            if currency.compare_amounts(line.amount, 0.0) < 0:
                raise UserError(_("Credit note apply amount cannot be negative."))
            if currency.compare_amounts(line.amount, line.open_amount) > 0:
                raise UserError(_("Credit note apply amount exceeds the open amount."))
