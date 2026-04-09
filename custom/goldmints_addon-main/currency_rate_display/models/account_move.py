from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    currency_rate_display = fields.Char(
        string="Rate Display",
        compute="_compute_currency_rate_display",
        store=False,
    )
    show_currency_rate = fields.Boolean(
        compute="_compute_currency_rate_display",
        store=False,
    )

    @api.depends('currency_id', 'company_id', 'date')
    def _compute_currency_rate_display(self):
        for move in self:
            is_foreign = move.currency_id and move.company_id and move.currency_id != move.company_id.currency_id
            move.show_currency_rate = is_foreign
            if is_foreign:
                rate = move.currency_id.with_context(date=move.date).rate
                if rate:
                    move.currency_rate_display = f"1 {move.company_id.currency_id.name} = {rate:.4f}"
                else:
                    move.currency_rate_display = False
            else:
                move.currency_rate_display = False
