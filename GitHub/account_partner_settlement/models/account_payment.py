from odoo import fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    same_side_credit_note_embedded = fields.Boolean(copy=False)

    def _synchronize_to_moves(self, changed_fields):
        protected_payments = self.filtered("same_side_credit_note_embedded")
        remaining_payments = self - protected_payments
        if remaining_payments:
            return super(AccountPayment, remaining_payments)._synchronize_to_moves(changed_fields)
        return True
