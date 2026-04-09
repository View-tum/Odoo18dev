from collections import defaultdict

from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _adjust_procure_method(self, picking_type_code=False):
        """Force procure_method on MO raw moves based on is_mto.

        - is_mto=True  -> only components WITHOUT BoM => make_to_order (auto RFQ/PO)
                          components WITH BoM stay make_to_stock
        - is_mto=False -> make_to_stock (manual replenishment)
        """
        res = super()._adjust_procure_method(picking_type_code=picking_type_code)

        raw_moves = self.filtered(lambda m: m.raw_material_production_id)
        if not raw_moves:
            return res

        mto_moves = raw_moves.filtered(lambda m: m.raw_material_production_id.is_mto)
        mts_moves = raw_moves - mto_moves

        if mto_moves:
            moves_by_company = defaultdict(lambda: self.env["stock.move"])
            for move in mto_moves:
                moves_by_company[move.company_id] |= move

            for company, moves in moves_by_company.items():
                products = moves.product_id
                bom_by_product = self.env["mrp.bom"]._bom_find(
                    products, company_id=company.id
                )
                moves_no_bom = moves.filtered(
                    lambda m: not bom_by_product.get(m.product_id)
                )
                moves_with_bom = moves - moves_no_bom
                if moves_no_bom:
                    moves_no_bom.procure_method = "make_to_order"
                if moves_with_bom:
                    moves_with_bom.procure_method = "make_to_stock"
        if mts_moves:
            mts_moves.procure_method = "make_to_stock"

        return res

    def _trigger_scheduler(self):
        """Skip auto scheduler for MTS MO raw moves."""
        allowed_moves = self.filtered(
            lambda m: not (m.raw_material_production_id and not m.raw_material_production_id.is_mto)
        )
        if not allowed_moves:
            return
        return super(StockMove, allowed_moves)._trigger_scheduler()
