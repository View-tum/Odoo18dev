from odoo import api, models, _
from odoo.exceptions import ValidationError

class AccountMove(models.Model):
    _inherit = "account.move"

    @api.constrains("date", "invoice_date", "move_type")
    def _check_accounting_date_not_before_invoice_date(self):
        for move in self:
            if move.move_type == "in_invoice":
                if not move.date or not move.invoice_date:
                    continue
                if move.date < move.invoice_date:
                    raise ValidationError(
                        _(
                            "Accounting Date must be equal to or later than the Bill Date for Vendor Bills.\n\n"
                            "Bill Date: %(invoice_date)s\n"
                            "Accounting Date: %(date)s"
                        ) % {
                            "invoice_date": move.invoice_date,
                            "date": move.date,
                        }
                    )
