# -*- coding: utf-8 -*-
from odoo import models


class PRLineMakePO(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order"

    def _apply_pr_line_pricing(self, po_line, pr_line):
        """Apply PR line discount & VATs to a PO line (created or reused)."""
        vals = {}
        if hasattr(pr_line, "discount"):
            vals["discount"] = pr_line.discount or 0.0
        if hasattr(pr_line, "taxes_id"):
            vals["taxes_id"] = [(6, 0, pr_line.taxes_id.ids)
                                ] if pr_line.taxes_id else [(6, 0, [])]
        if vals:
            po_line.write(vals)

    def make_purchase_order(self):
        # Run the standard logic first
        action = super().make_purchase_order()

        # Post-process the affected PO lines so our values "stick"
        order_ids = self.env[action["res_model"]].search(action["domain"]).ids
        if not order_ids:
            return action

        POL = self.env["purchase.order.line"]
        for item in self.item_ids:
            pr_line = item.line_id
            po_lines = POL.search([
                ("order_id", "in", order_ids),
                ("purchase_request_lines", "in", pr_line.id),
            ])
            for po_line in po_lines:
                self._apply_pr_line_pricing(po_line, pr_line)

        return action
