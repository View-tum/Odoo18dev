from odoo import api, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    def _get_vendor_billing_note_net_payment_amount(self):
        self.ensure_one()
        if not self.env.context.get("vendor_billing_note_id"):
            return False
        if not self.currency_id or not self.payment_date:
            return False

        valid_account_types = self.env["account.payment"]._get_valid_payment_account_types()
        lines = self.line_ids.filtered(
            lambda line: line.account_type in valid_account_types
            and line.move_id.move_type in ("in_invoice", "in_refund")
        )
        if not lines or len(lines.mapped("company_id.root_id")) > 1:
            return False

        amount = 0.0
        for line in lines:
            line_currency = line.currency_id or line.company_currency_id
            if line_currency == self.currency_id:
                amount += line.amount_residual_currency if line.currency_id else line.amount_residual
            elif line.currency_id:
                amount += line.currency_id._convert(
                    line.amount_residual_currency,
                    self.currency_id,
                    line.company_id,
                    self.payment_date,
                )
            else:
                amount += line.company_currency_id._convert(
                    line.amount_residual,
                    self.currency_id,
                    line.company_id,
                    self.payment_date,
                )
        return self.currency_id.round(abs(amount))

    @api.depends(
        "can_edit_wizard",
        "amount",
        "installments_mode",
        "line_ids",
        "currency_id",
        "payment_date",
    )
    def _compute_payment_difference(self):
        super()._compute_payment_difference()
        for wizard in self:
            net_amount = wizard._get_vendor_billing_note_net_payment_amount()
            if net_amount is not False:
                wizard.payment_difference = net_amount - wizard.amount

    def _create_payments(self):
        payments = super()._create_payments()
        billing_note_id = self.env.context.get("vendor_billing_note_id")
        if billing_note_id:
            self.env["vendor.billing.note"].browse(billing_note_id)._reconcile_bill_credit_residuals(payments)
        return payments
