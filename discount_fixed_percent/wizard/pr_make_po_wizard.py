from odoo import models


class PRLineMakePO(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order"

    def _apply_pr_line_pricing(self, po_line, pr_line):
        """
        Applies pricing and discount details from a Purchase Request Line to a Purchase Order Line.

        Override:
            - Calls the super method to handle standard fields (price, taxes, etc.).
            - explicitly transfers 'fixed_discount' and 'percent_discount' from the PR line to the new PO line.
        """

        super()._apply_pr_line_pricing(po_line, pr_line)
        vals = {}
        if hasattr(pr_line, "fixed_discount"):
            vals["fixed_discount"] = pr_line.fixed_discount or 0.0

        if hasattr(pr_line, "percent_discount"):
            vals["percent_discount"] = pr_line.percent_discount or 0.0

        if hasattr(pr_line, "hidden_discount_amount"):
            vals["hidden_discount_amount"] = pr_line.hidden_discount_amount or 0.0

        if vals:
            po_line.write(vals)
