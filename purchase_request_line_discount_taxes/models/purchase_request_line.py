# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PurchaseRequestLine(models.Model):
    _inherit = "purchase.request.line"

    # Mirror company on the line for tax domains
    company_id = fields.Many2one(
        related="request_id.company_id",
        store=True,
        readonly=True,
    )
    tax_country_id = fields.Many2one(
        related="company_id.account_fiscal_country_id",
        string="Tax Country",
        store=True,
        readonly=True,
    )

    discount = fields.Float(
        string="Discount (%)",
        help="Percentage discount applied to this request line.",
        digits="Discount",
        default=0.0,
    )

    taxes_id = fields.Many2many(
        "account.tax",
        "purchase_request_line_tax_rel",  # relation table
        "line_id",
        "tax_id",
        string="VATs",
        help="VATs to apply when creating RFQ/PO from this request line.",
    )

    # Amounts on PR line (computed from unit_cost, qty, discount, VATs)
    amount_untaxed = fields.Monetary(
        string="UnVATs Amount",
        currency_field="currency_id",
        compute="_compute_amounts",
        store=True,
    )
    amount_tax = fields.Monetary(
        string="VATs",
        currency_field="currency_id",
        compute="_compute_amounts",
        store=True,
    )
    amount_total = fields.Monetary(
        string="Total",
        currency_field="currency_id",
        compute="_compute_amounts",
        store=True,
    )

    # Keep estimated_cost aligned with discounted, VAT-excluded total
    estimated_cost = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_amounts",
        store=True,
        help="Estimated cost of Purchase Request Line (after discount, before VAT).",
    )

    @api.onchange("product_id")
    def _onchange_product_id_set_default_taxes(self):
        """Auto set VATs from supplier taxes matching company/country for purchases."""
        for line in self:
            if line.product_id:
                # Only keep active purchase VATs matching the company and country
                taxes = line.product_id.supplier_taxes_id.filtered(
                    lambda t: (not t.company_id or t.company_id == line.company_id)
                    and (not t.country_id or t.country_id == line.tax_country_id)
                    and t.type_tax_use == "purchase"
                    and t.active
                )
                line.taxes_id = [(6, 0, taxes.ids)]

    @api.depends(
        "product_qty",
        "unit_cost",
        "discount",
        "taxes_id",
        "taxes_id.amount",
        "taxes_id.price_include",
        "taxes_id.include_base_amount",
        "taxes_id.children_tax_ids",
        "currency_id",
        "product_id",
    )
    def _compute_amounts(self):
        for line in self:
            qty = line.product_qty or 0.0
            unit_cost = getattr(line, "unit_cost", 0.0) or 0.0
            discount = line.discount or 0.0
            # apply discount by reducing unit price
            price_unit = unit_cost * (1.0 - (discount / 100.0))
            currency = line.currency_id
            product = line.product_id
            partner = getattr(line, "vendor", False) or False
            taxes = line.taxes_id

            if taxes:
                res = taxes.compute_all(
                    price_unit,
                    currency=currency,
                    quantity=qty,
                    product=product,
                    partner=partner,
                )
                subtotal = res.get("total_excluded", price_unit * qty)
                total = res.get("total_included", subtotal)
            else:
                subtotal = price_unit * qty
                total = subtotal

            # assign amounts
            line.amount_untaxed = subtotal
            line.amount_total = total
            line.amount_tax = total - subtotal
            # keep estimated_cost aligned with untaxed total for document totals
            line.estimated_cost = subtotal
