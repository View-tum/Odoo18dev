from odoo import models


class MrpWorkorder(models.Model):
    _inherit = "mrp.workorder"

    def button_scrap(self):
        self.ensure_one()
        action = super().button_scrap()
        raw_moves = self.production_id.move_raw_ids.filtered(lambda m: m.state != 'cancel' and m.product_id)
        finished_moves = self.production_id.move_finished_ids.filtered(lambda m: m.state != 'cancel' and m.product_id)
        allowed_products = (raw_moves | finished_moves).mapped("product_id") or self.production_id.product_id
        ctx = dict(action.get("context") or {})
        ctx.update({
            "product_ids": allowed_products.ids,
            "allowed_product_ids": allowed_products.ids,
            "default_product_id": allowed_products[:1].id,
            "default_location_id": self.production_id.location_src_id.id,
            "default_company_id": self.production_id.company_id.id,
            "default_production_id": self.production_id.id,
            "default_workorder_id": self.id,
        })
        action["context"] = ctx
        return action






