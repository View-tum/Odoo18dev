from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    promised_payment_date = fields.Date(
        string="Promised Date",
        tracking=True,
    )

    def write(self, vals):
        if "promised_payment_date" in vals and self.filtered(lambda m: m.state == "posted"):
            return super(AccountMove, self.with_context(skip_readonly_check=True)).write(vals)
        return super().write(vals)
