# -*- coding: utf-8 -*-
from odoo import api, models, _
from odoo.exceptions import ValidationError

from .analytic_distribution_mixin import AnalyticDistributionCheckMixin


class PurchaseRequestLine(AnalyticDistributionCheckMixin, models.Model):
    _inherit = "purchase.request.line"

    @api.depends("product_id", "product_id.categ_id", "company_id", "supplier_id")
    def _compute_analytic_distribution(self):
        distribution_model = self.env["account.analytic.distribution.model"]
        for line in self:
            if not line.product_id:
                continue
            distribution = distribution_model._get_distribution(
                {
                    "product_id": line.product_id.id,
                    "product_categ_id": line.product_id.categ_id.id,
                    "partner_id": line.supplier_id.id,
                    "partner_category_id": line.supplier_id.category_id.ids,
                    "company_id": line.company_id.id,
                }
            )
            line.analytic_distribution = distribution or line.analytic_distribution

    @api.onchange("product_id")
    def onchange_product_id(self):
        res = super().onchange_product_id()
        if self.product_id:
            self._compute_analytic_distribution()
        else:
            self.analytic_distribution = False
        return res

    @api.constrains("analytic_distribution")
    def _check_pr_line_analytic_required(self):
        tolerance = 0.01
        for line in self:
            total = line._analytic_distribution_total()
            if total <= 0.0:
                raise ValidationError(
                    _("Each Purchase Request line must have an Analytic Distribution.")
                )
            if abs(total - 100.0) > tolerance:
                raise ValidationError(
                    _(
                        "Analytic Distribution must total 100%% (found %.2f%%) on line: %s"
                    )
                    % (total, line.display_name)
                )
