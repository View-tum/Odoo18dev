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
