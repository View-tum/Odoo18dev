from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_new_picking_values(self):
        values = super()._get_new_picking_values()
        if not values.get("partner_id"):
            partners = (
                self.move_orig_ids.mapped("picking_id.partner_id")
                or self.move_orig_ids.mapped("partner_id")
                or self.mapped("picking_id.partner_id")
                or self.mapped("partner_id")
            )
            if partners:
                values["partner_id"] = partners[0].id
        return values