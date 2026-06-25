from odoo import models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def _auto_create_wht_cert(self):
        for payment in self:
            if payment.payment_type != "outbound" or payment.wht_cert_ids:
                continue
            if payment.state == "canceled":
                continue
            if not payment.wht_move_ids:
                continue
            if payment.wht_move_ids.filtered(
                lambda move: not move.wht_cert_income_type
            ):
                continue
            payment.create_wht_cert()

    def action_post(self):
        res = super().action_post()
        self._auto_create_wht_cert()
        return res
