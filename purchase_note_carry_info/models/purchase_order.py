from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    purchase_note = fields.Text(
        string="Purchase Note",
        help="(365 custom) Internal note for this Purchase Order. It may be pre-filled from the source Purchase Request(s)."
    )

    @api.onchange("order_line")
    def _onchange_order_line_fill_purchase_note_from_pr(self):
        """
        If PO's purchase_note is empty, try to prefill from linked Purchase Request(s).
        Works when lines are added from PR (via 'purchase_request' flow).
        """
        for order in self:
            if order.purchase_note:
                continue
            try:
                prs = order.order_line.mapped("purchase_request_lines.request_id")
            except Exception:
                prs = self.env["purchase.request"]
            order.purchase_note = prs[:1].purchase_note if prs else False
