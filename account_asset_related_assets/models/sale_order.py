from odoo import _, api, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _check_related_asset_on_lines(self):
        """Block orders containing products whose asset models have linked assets."""
        for order in self:
            offending = []
            for line in order.order_line:
                product = line.product_template_id or line.product_id 
                asset_model = product.asset_model_id
                if not asset_model:
                    continue

                linked_assets = asset_model.related_asset_ids
                if linked_assets:
                    offending.append(
                        _(
                            "Product %(product)s uses asset model %(asset)s linked to: %(related)s"
                        )
                        % {
                            "product": product.display_name,
                            "asset": asset_model.display_name,
                            "related": ", ".join(linked_assets.mapped("display_name")),
                        }
                    )
            if offending:
                raise UserError(
                    _(
                        "You cannot save this sale order because some products are using asset models linked to other assets:\n%s"
                    )
                    % "\n".join(offending)
                )

    @api.model
    def create(self, vals):
        order = super().create(vals)
        order._check_related_asset_on_lines()
        return order

    def write(self, vals):
        res = super().write(vals)
        self._check_related_asset_on_lines()
        return res
