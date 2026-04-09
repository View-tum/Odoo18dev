from odoo import api, fields, models


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    currency_rate_display = fields.Char(
        string="Rate Display",
        compute="_compute_currency_rate_display",
        store=False,
    )
    show_currency_rate = fields.Boolean(
        compute="_compute_currency_rate_display",
        store=False,
    )

    @api.depends('currency_id', 'company_id', 'date_start')
    def _compute_currency_rate_display(self):
        for request in self:
            is_foreign = request.currency_id and request.company_id and request.currency_id != request.company_id.currency_id
            request.show_currency_rate = is_foreign
            if is_foreign:
                rate = request.currency_id.with_context(date=request.date_start).rate
                if rate:
                    request.currency_rate_display = f"1 {request.company_id.currency_id.name} = {rate:.4f}"
                else:
                    request.currency_rate_display = False
            else:
                request.currency_rate_display = False
