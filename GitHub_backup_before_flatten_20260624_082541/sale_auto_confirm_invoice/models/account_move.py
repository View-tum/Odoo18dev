from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.constrains("line_ids")
    def _check_date_maturity(self):
        today = fields.Date.context_today(self)
        for move in self:
            maturity = move.invoice_date_due or move.date or today
            partner_lines = move.line_ids.filtered(
                lambda l: l.account_id.account_type in ("asset_receivable", "liability_payable")
            )
            partner_lines_filtered = partner_lines.filtered(lambda l: not l.date_maturity)
            if partner_lines_filtered:
                partner_lines_filtered.write({"date_maturity": maturity})
            non_partner = move.line_ids.filtered(
                lambda l: l.account_id.account_type not in ("asset_receivable", "liability_payable")
                and l.date_maturity
            )
            if non_partner:
                non_partner.write({"date_maturity": False})
        return True
