from odoo import api, models


class StockLandedCostLine(models.Model):
    _inherit = "stock.landed.cost.lines"

    def _get_custom_account(self):
        """Return the account configured on the product if available."""
        self.ensure_one()
        if self.product_id.landed_cost_account_id:
            return self.product_id.landed_cost_account_id
        return False

    @api.onchange("product_id")
    def onchange_product_id(self):
        super().onchange_product_id()
        for line in self:
            account = line._get_custom_account()
            if account:
                line.account_id = account.id
    