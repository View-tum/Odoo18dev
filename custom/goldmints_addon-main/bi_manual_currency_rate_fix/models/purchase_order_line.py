from odoo import models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def _prepare_base_line_for_taxes_computation(self):
        self.ensure_one()

        if (
            self.order_id.purchase_manual_currency_rate_active
            and self.order_id.purchase_manual_currency_rate
        ):
            is_inverted_rate = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("bi_manual_currency_exchange_rate.inverted_rate") == 'True'
            )
            if is_inverted_rate:
                rate = 1.0 / self.order_id.purchase_manual_currency_rate
            else:
                rate = self.order_id.purchase_manual_currency_rate
        else:
            rate = self.order_id.currency_rate

        return self.env["account.tax"]._prepare_base_line_for_taxes_computation(
            self,
            tax_ids=self.taxes_id,
            quantity=self.product_qty,
            partner_id=self.order_id.partner_id,
            currency_id=self.order_id.currency_id or self.order_id.company_id.currency_id,
            rate=rate,
        )
