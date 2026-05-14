from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _is_sm_component_move(self):
        self.ensure_one()
        return bool(
            self.raw_material_production_id
            and (self.product_id.default_code or "").upper().startswith("SM")
        )

    def _find_sm_transfer_rule(self):
        """Find the pull rule that replenishes an SM component into the MO source location."""
        self.ensure_one()
        if not self._is_sm_component_move() or not self.location_id:
            return self.env["stock.rule"]

        domain = [
            ("location_dest_id", "=", self.location_id.id),
            ("action", "!=", "push"),
        ]
        return self.env["procurement.group"]._search_rule(
            False,
            self.product_packaging_id,
            self.product_id,
            self.warehouse_id,
            domain,
        )

    def _adjust_procure_method(self, picking_type_code=False):
        """Force procure_method on MO raw moves based on is_mto.

        - is_mto=True  -> make_to_order for every component, including sub-assemblies
                          with BoM, so the MTO chain can create child MOs/POs.
        - is_mto=False -> make_to_stock (manual replenishment)
        """
        res = super()._adjust_procure_method(picking_type_code=picking_type_code)

        raw_moves = self.filtered(lambda m: m.raw_material_production_id)
        if not raw_moves:
            return res

        mto_moves = raw_moves.filtered(lambda m: m.raw_material_production_id.is_mto)
        mts_moves = raw_moves - mto_moves

        if mto_moves:
            mto_moves.procure_method = "make_to_order"
        if mts_moves:
            mts_moves.procure_method = "make_to_stock"

        # SM semi components are produced by Plastic but replenished through the
        # Pharma transfer route into the MO source location. Keep the raw move as
        # MTS, but attach the mts_else_mto rule so standard Odoo creates a
        # transfer only for the shortage.
        for move in mts_moves:
            rule = move._find_sm_transfer_rule()
            if rule and rule.procure_method == "mts_else_mto":
                move.rule_id = rule
                move.procure_method = "make_to_stock"

        return res

    def _trigger_scheduler(self):
        """Skip orderpoint auto-scheduler for MO raw moves.

        MTO raw moves already create their upstream supply in core
        ``stock.move._action_confirm``. Letting them also trigger automatic
        orderpoints creates duplicate ``OP/...`` replenishments inside the same
        SO confirmation and can spin into a large procurement loop.
        """
        allowed_moves = self.filtered(
            lambda m: not m.raw_material_production_id
        )
        if not allowed_moves:
            return
        return super(StockMove, allowed_moves)._trigger_scheduler()
