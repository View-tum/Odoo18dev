from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def action_show_details(self):
        self.mapped("picking_id")._sync_van_sales_operation_move_locations(reassign=True)
        return super().action_show_details()
