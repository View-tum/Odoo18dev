from odoo import models


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order"

    def _prepare_purchase_order(self, picking_type, group_id, company, origin):
        data = super()._prepare_purchase_order(picking_type, group_id, company, origin)

        first_item = self.item_ids[:1]
        if first_item:
            pr = first_item.line_id.request_id
            currency = getattr(pr, 'vendor_currency_id', None) or pr.currency_id
            if currency:
                data["currency_id"] = currency.id

        return data
