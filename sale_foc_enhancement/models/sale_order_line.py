from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    is_foc = fields.Boolean(string="Free of Charge")
    foc_price_unit = fields.Monetary(
        string="FOC Unit Price",
        currency_field="currency_id",
        help="Internal valuation unit price for FOC lines.",
    )

    @api.onchange("is_foc")
    def _onchange_is_foc(self):
        for line in self:
            if line.is_foc:
                # Save current price as FOC valuation if not already set
                if not line.foc_price_unit:
                    line.foc_price_unit = line.price_unit or line.product_id.lst_price
                # Customer sees zero price on the SO/invoice
                line.price_unit = 0.0
                line.discount = 0.0

    def _prepare_invoice_line(self, **optional_values):
        vals = super()._prepare_invoice_line(**optional_values)
        if self.is_foc:
            vals.update({
                "is_foc": True,
                "foc_price_unit": self.foc_price_unit or 0.0,
                "price_unit": 0.0,  # zero amount on invoice line
            })
        return vals
