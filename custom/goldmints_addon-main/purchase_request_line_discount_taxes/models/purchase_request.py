# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    amount_untaxed = fields.Monetary(
        string="UnVATs Amount",
        currency_field="currency_id",
        compute="_compute_amount_totals",
        store=True,
    )
    amount_tax = fields.Monetary(
        string="VATs",
        currency_field="currency_id",
        compute="_compute_amount_totals",
        store=True,
    )

    @api.depends(
        "line_ids",
        "line_ids.amount_untaxed",
        "line_ids.amount_tax",
        "currency_id",
    )
    def _compute_amount_totals(self):
        for rec in self:
            rec.amount_untaxed = sum(rec.line_ids.mapped("amount_untaxed"))
            rec.amount_tax = sum(rec.line_ids.mapped("amount_tax"))

    @api.depends("line_ids", "line_ids.amount_total", "line_ids.estimated_cost")
    def _compute_estimated_cost(self):
        """Keep total estimated cost inclusive of VAT (sum of line totals)."""
        for rec in self:
            rec.estimated_cost = sum(
                line.amount_total if line.amount_total not in (False, None) else line.estimated_cost or 0.0
                for line in rec.line_ids
            )
