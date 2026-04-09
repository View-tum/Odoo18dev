# -*- coding: utf-8 -*-
import math

from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_linked_mrp_production(self):
        self.ensure_one()
        if self.raw_material_production_id:
            return self.raw_material_production_id

        for dest_move in self.move_dest_ids:
            res = dest_move._get_linked_mrp_production()
            if res:
                return res
        return self.env['mrp.production']

    def _prepare_procurement_qty(self):
        res = super(StockMove, self)._prepare_procurement_qty()

        enabled = self.env['ir.config_parameter'].sudo().get_param('mrp_step_consumption.enabled', default='True')
        if enabled == 'False':
            return res

        new_res = []
        for move, qty in zip(self, res):
            if move.bom_line_id and move.bom_line_id.step_coverage_qty > 0 and move.bom_line_id.step_batch_qty > 0:
                mo = move._get_linked_mrp_production()
                if mo:
                    is_physical_consumption = bool(move.raw_material_production_id)
                    is_final_staging = False
                    mo_src_loc = mo.location_src_id

                    if move.location_dest_id == mo_src_loc:
                        is_final_staging = True
                    elif mo_src_loc.parent_path and move.location_dest_id.parent_path:
                        if move.location_dest_id.parent_path.startswith(mo_src_loc.parent_path):
                            is_final_staging = True

                    if not (is_physical_consumption or is_final_staging):
                        mo_qty = mo.product_qty
                        if mo.product_uom_id != mo.bom_id.product_uom_id:
                            mo_qty = mo.product_uom_id._compute_quantity(mo_qty, mo.bom_id.product_uom_id)

                        from odoo.tools import float_round
                        rounding = move.product_uom.rounding or 0.01
                        batches_needed = math.ceil(mo_qty / move.bom_line_id.step_coverage_qty)
                        step_qty = float_round(batches_needed * move.bom_line_id.step_batch_qty, precision_rounding=rounding)

                        if step_qty > qty:
                            qty = step_qty
            new_res.append(qty)

        return new_res



