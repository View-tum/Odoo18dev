from odoo import models


class StockValuationAdjustmentLines(models.Model):
    _inherit = "stock.valuation.adjustment.lines"

    def _get_cost_to_add_for_scrap(self, remaining_qty, move_qty):
        is_scrap_cost = getattr(self.cost_line_id.product_id, "is_scrap_cost", False)

        if is_scrap_cost and remaining_qty > 0:
            return self.additional_landed_cost

        if move_qty > 0:
            return (remaining_qty / move_qty) * self.additional_landed_cost
        return 0.0

    def _create_account_move_line(
        self, move, credit_account_id, debit_account_id, qty_out, already_out_account_id
    ):
        is_scrap_cost = getattr(self.cost_line_id.product_id, "is_scrap_cost", False)

        if is_scrap_cost:
            qty_out = 0

        return super()._create_account_move_line(
            move, credit_account_id, debit_account_id, qty_out, already_out_account_id
        )
