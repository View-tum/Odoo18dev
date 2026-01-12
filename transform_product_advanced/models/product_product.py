from odoo import models, fields, api, _


class ProductProduct(models.Model):
    _inherit = "product.product"

    transform_move_count = fields.Integer(
        string="Transform Moves",
        compute="_compute_transform_move_count",
    )

    def _compute_transform_move_count(self):
        """Count stock moves created by transform operations for this product."""
        Move = self.env["stock.move"]
        for product in self:
            count = Move.search_count([
                "|",
                ("product_id", "=", product.id),
                ("move_orig_ids.product_id", "=", product.id),
            ])
            product.transform_move_count = count

    def action_view_transform_history(self):
        """Open stock moves related to this product for transform operations."""
        self.ensure_one()
        Move = self.env["stock.move"]
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "stock.stock_move_action"
        )
        domain = [
            "|",
            ("product_id", "=", self.id),
            ("move_orig_ids.product_id", "=", self.id),
        ]
        action["domain"] = domain
        action["context"] = {
            "default_product_id": self.id,
        }
        return action
