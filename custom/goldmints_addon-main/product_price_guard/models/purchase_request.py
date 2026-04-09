# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools import float_compare


class PurchaseRequestLine(models.Model):
    _inherit = "purchase.request.line"

    final_allowed_price = fields.Monetary(
        string="Allowed Price",
        currency_field="currency_id",
        compute="_compute_final_allowed_price",
        help="Reference ceiling derived from the product template Cost per Unit configuration.",
    )
    is_over_final_limit = fields.Boolean(
        string="Over Final Limit?",
        compute="_compute_is_over_final_limit",
        help="Indicates whether the unit cost exceeds the product's configured final allowed price.",
    )

    def _get_guard_price(self):
        """Return the price to validate (unit_cost if available, otherwise estimated_cost)."""
        self.ensure_one()
        if "unit_cost" in self._fields:
            return self.unit_cost or 0.0
        return self.estimated_cost or 0.0

    def _get_limit_in_currency(self, currency):
        self.ensure_one()
        if not self.product_id:
            return 0.0

        template = self.product_id.product_tmpl_id
        limit_company_currency = template.final_allowed_price or 0.0
        if not limit_company_currency:
            return 0.0

        company = self.company_id or self.env.company
        company_currency = company.currency_id
        target_currency = currency or company_currency

        if target_currency == company_currency:
            return limit_company_currency

        date_ref = self.request_id.date_start or fields.Date.context_today(self)
        return company_currency._convert(
            limit_company_currency, target_currency, company, date_ref
        )

    def _is_price_over_limit(self, price, currency):
        limit = self._get_limit_in_currency(currency)
        if not limit:
            return False
        rounding = (currency and currency.rounding) or self.company_id.currency_id.rounding
        return float_compare(price or 0.0, limit, precision_rounding=rounding or 0.01) > 0

    @api.depends(
        "product_id",
        "product_id.product_tmpl_id.final_allowed_price",
        "estimated_cost",
        "currency_id",
        "company_id",
    )
    def _compute_is_over_final_limit(self):
        for line in self:
            currency = line.currency_id or line.company_id.currency_id
            guard_price = line._get_guard_price()
            line.is_over_final_limit = line._is_price_over_limit(guard_price, currency)

    @api.depends(
        "product_id",
        "product_id.product_tmpl_id.final_allowed_price",
        "currency_id",
        "company_id",
    )
    def _compute_final_allowed_price(self):
        for line in self:
            if not line.product_id:
                line.final_allowed_price = 0.0
                continue
            currency = line.currency_id or line.company_id.currency_id
            line.final_allowed_price = line._get_limit_in_currency(currency)

    @api.onchange("product_id", "estimated_cost")
    def _onchange_price_guard(self):
        warning = None
        for line in self:
            guard_price = line._get_guard_price()
            if not line.product_id or not guard_price:
                continue

            currency = line.currency_id or line.company_id.currency_id
            if line._is_price_over_limit(guard_price, currency):
                template = line.product_id.product_tmpl_id
                limit_currency_value = line._get_limit_in_currency(currency)
                warning = {
                    "title": _("Unit Cost Exceeds Allowed Threshold"),
                    "message": _(
                        "Product: %(product)s\n"
                        "Cost per Unit: %(standard).2f\n"
                        "Upcharge (%%): %(percent).2f\n"
                        "Final Allowed: %(limit).2f\n"
                        "Entered Unit Cost: %(unit).2f\n\n"
                        "Please review. The unit cost is higher than the configured limit.",
                        product=line.product_id.display_name,
                        standard=template.cost_per_unit or 0.0,
                        percent=template.upcharge_percent or 0.0,
                        limit=limit_currency_value,
                        unit=guard_price,
                    ),
                }
                break
        if warning:
            return {"warning": warning}


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    has_final_price_violation = fields.Boolean(
        compute="_compute_has_final_price_violation",
        help="Technical flag indicating that at least one request line exceeds the configured final price limit.",
    )

    @api.depends("line_ids.is_over_final_limit")
    def _compute_has_final_price_violation(self):
        for req in self:
            req.has_final_price_violation = any(
                req.line_ids.filtered(lambda l: l.is_over_final_limit)
            )

    def button_to_approve(self):
        for req in self:
            violating_lines = req.line_ids.filtered(lambda l: l.is_over_final_limit)
            if violating_lines:
                details = "<br/>".join(
                    _(
                        "%(product)s :: %(price).2f > %(limit).2f",
                        product=line.product_id.display_name,
                        price=line._get_guard_price(),
                        limit=line.final_allowed_price or 0.0,
                    )
                    for line in violating_lines
                )
                body = _(
                    "<p><strong>Price Guard Warning:</strong> some lines exceed the allowed price limit.</p>"
                    "<p>%s</p>"
                ) % details
                req.message_post(body=body, message_type="comment", subtype_xmlid="mail.mt_note")
        return super().button_to_approve()

    def action_view_receipt(self):
        """Fallback for custom stat button that expects this name; reuse stock picking action."""
        return self.action_view_stock_picking()
