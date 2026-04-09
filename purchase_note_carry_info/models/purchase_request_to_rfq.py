from odoo import api, models


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order"

    @api.model
    def _prepare_purchase_order(self, picking_type, company, origin, supplier):
        """Override to propagate purchase_note from Purchase Request to PO."""
        vals = super()._prepare_purchase_order(picking_type, company, origin, supplier)

        request_lines = self.item_ids.mapped("line_id").exists()
        if not request_lines:
            request_lines = self.env["purchase.request.line"].browse(
                self._context.get("active_ids", [])
            ).exists()
        requests = request_lines.mapped("request_id").exists()

        if requests:
            if len(requests) == 1:
                vals["purchase_note"] = requests.purchase_note
            else:
                notes = [r.purchase_note for r in requests if r.purchase_note]
                vals["purchase_note"] = "\n---\n".join(notes) if notes else False

        return vals
