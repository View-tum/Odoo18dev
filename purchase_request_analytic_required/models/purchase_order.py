# -*- coding: utf-8 -*-
from odoo import api, models, _
from odoo.exceptions import UserError, ValidationError

from .analytic_distribution_mixin import AnalyticDistributionCheckMixin


class PurchaseOrderLine(AnalyticDistributionCheckMixin, models.Model):
    _inherit = "purchase.order.line"

    def _requires_pr_distribution(self):
        """Only enforce analytic rules when line originates from a Purchase Request."""
        self.ensure_one()
        return bool(self.purchase_request_lines)

    @api.constrains("analytic_distribution")
    def _check_po_line_analytic_required(self):
        tolerance = 0.01
        for line in self:
            if not line._requires_pr_distribution():
                continue
            total = line._analytic_distribution_total()
            if total <= 0.0:
                raise ValidationError(
                    _("Each Purchase Order line coming from a Purchase Request "
                      "must have an Analytic Distribution.")
                )
            if abs(total - 100.0) > tolerance:
                raise ValidationError(
                    _(
                        "Analytic Distribution must total 100%% (found %.2f%%) on line: %s"
                    )
                    % (total, line.display_name)
                )


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def _ensure_complete_analytic_distribution(self):
        tolerance = 0.01
        for order in self:
            for line in order.order_line:
                if not line._requires_pr_distribution():
                    continue
                total = line._analytic_distribution_total()
                if total <= 0.0:
                    raise UserError(
                        _("PO %s has a PR line without Analytic Distribution: %s")
                        % (order.name, line.display_name)
                    )
                if abs(total - 100.0) > tolerance:
                    raise UserError(
                        _(
                            "PO %s has a PR line with Analytic Distribution not equal to 100%% "
                            "(%.2f%%) on: %s"
                        )
                        % (order.name, total, line.display_name)
                    )
        return True

    def button_confirm(self):
        self._ensure_complete_analytic_distribution()
        return super().button_confirm()
