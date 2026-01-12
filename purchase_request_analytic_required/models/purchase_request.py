# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import UserError


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    def _ensure_complete_analytic_distribution(self):
        tolerance = 0.01
        for request in self:
            for line in request.line_ids:
                total = line._analytic_distribution_total()
                if total <= 0.0:
                    raise UserError(
                        _("PR %s has a line without Analytic Distribution: %s")
                        % (request.name, line.display_name)
                    )
                if abs(total - 100.0) > tolerance:
                    raise UserError(
                        _(
                            "PR %s has a line with Analytic Distribution not equal to 100%% "
                            "(%.2f%%) on: %s"
                        )
                        % (request.name, total, line.display_name)
                    )
        return True

    def button_to_approve(self):
        self._ensure_complete_analytic_distribution()
        return super().button_to_approve()

    def button_approved(self):
        self._ensure_complete_analytic_distribution()
        return super().button_approved()


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order"

    def _prepare_purchase_order_line(self, po, item):
        vals = super()._prepare_purchase_order_line(po, item)
        vals["analytic_distribution"] = item.line_id.analytic_distribution or False
        return vals
