# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools import float_compare


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    final_allowed_price = fields.Monetary(
        string="Allowed Price",
        currency_field="currency_id",
        compute="_compute_final_allowed_price",
        help="Reference ceiling derived from the product template Cost per Unit configuration.",
    )
    is_over_final_limit = fields.Boolean(
        string="Over Final Limit?",
        compute="_compute_is_over_final_limit",
        help="Indicates whether the unit price exceeds the product's configured final allowed price.",
    )

    def _get_limit_in_currency(self, currency):
        self.ensure_one()
        if not self.product_id or not self.order_id:
            return 0.0

        template = self.product_id.product_tmpl_id
        limit_company_currency = template.final_allowed_price or 0.0
        if not limit_company_currency:
            return 0.0

        company = self.order_id.company_id or self.env.company
        company_currency = company.currency_id
        target_currency = currency or self.currency_id or self.order_id.currency_id
        if not target_currency or target_currency == company_currency:
            return limit_company_currency

        date_ref = self.order_id.date_order or fields.Date.context_today(self)
        return company_currency._convert(
            limit_company_currency, target_currency, company, date_ref
        )

    def _is_price_over_limit(self, price, currency):
        limit = self._get_limit_in_currency(currency)
        if not limit:
            return False
        rounding = (currency and currency.rounding) or (
            self.order_id.currency_id.rounding if self.order_id else self.env.company.currency_id.rounding
        )
        return float_compare(price or 0.0, limit, precision_rounding=rounding or 0.01) > 0

    @api.depends(
        "product_id",
        "product_id.product_tmpl_id.final_allowed_price",
        "price_unit",
        "currency_id",
        "order_id.currency_id",
        "order_id.date_order",
        "display_type",
    )
    def _compute_is_over_final_limit(self):
        for line in self:
            if line.display_type:
                line.is_over_final_limit = False
                continue
            currency = line.currency_id or line.order_id.currency_id
            line.is_over_final_limit = line._is_price_over_limit(line.price_unit, currency)

    @api.depends(
        "product_id",
        "product_id.product_tmpl_id.final_allowed_price",
        "currency_id",
        "order_id.currency_id",
        "order_id.company_id",
        "order_id.date_order",
    )
    def _compute_final_allowed_price(self):
        for line in self:
            if not line.product_id or line.display_type:
                line.final_allowed_price = 0.0
                continue
            currency = line.currency_id or line.order_id.currency_id
            line.final_allowed_price = line._get_limit_in_currency(currency)

    @api.onchange("product_id", "price_unit")
    def _onchange_price_guard(self):
        warning = None
        for line in self:
            if line.display_type or not line.product_id or not line.price_unit:
                continue

            currency = line.currency_id or line.order_id.currency_id
            if line._is_price_over_limit(line.price_unit, currency):
                template = line.product_id.product_tmpl_id
                limit_currency_value = line._get_limit_in_currency(currency)
                warning = {
                    "title": _("Unit Price Exceeds Allowed Threshold"),
                    "message": _(
                        "Product: %(product)s\n"
                        "Cost per Unit: %(standard).2f\n"
                        "Upcharge (%%): %(percent).2f\n"
                        "Final Allowed: %(limit).2f\n"
                        "Entered Unit Cost: %(unit).2f\n\n"
                        "Please review. The entered price is higher than the configured limit.",
                        product=line.product_id.display_name,
                        standard=template.cost_per_unit or 0.0,
                        percent=template.upcharge_percent or 0.0,
                        limit=limit_currency_value,
                        unit=line.price_unit,
                    ),
                }
                break
        if warning:
            return {"warning": warning}


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    has_final_price_violation = fields.Boolean(
        compute="_compute_has_final_price_violation",
        help="Technical flag indicating that at least one order line exceeds the configured final price limit.",
    )

    @api.depends("order_line.is_over_final_limit")
    def _compute_has_final_price_violation(self):
        for order in self:
            order.has_final_price_violation = any(
                order.order_line.filtered(lambda l: not l.display_type and l.is_over_final_limit)
            )

    def button_confirm(self):
        for order in self:
            violating_lines = order.order_line.filtered(
                lambda l: not l.display_type and l.is_over_final_limit
            )
            if violating_lines:
                details = "<br/>".join(
                    _(
                        "%(product)s :: %(price).2f > %(limit).2f",
                        product=line.product_id.display_name,
                        price=line.price_unit or 0.0,
                        limit=line.final_allowed_price or 0.0,
                    )
                    for line in violating_lines
                )
                body = _(
                    "<p><strong>Price Guard Warning:</strong> some lines exceed the allowed price limit.</p>"
                    "<p>%s</p>"
                ) % details
                order.message_post(body=body, message_type="comment", subtype_xmlid="mail.mt_note")
        return super().button_confirm()


