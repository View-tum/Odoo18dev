# account_accrual_wizard/models/account_move_inherit.py
from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_post(self):
        res = super().action_post()
        accrual_obj = self.env["account.accrual"]
        for move in self:
            if move.move_type == "in_invoice" and move.state == "posted":
                accrual_obj._auto_match_accrual_for_bill(move)
        return res
