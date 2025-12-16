# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools import float_is_zero, float_round


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    workorder_id = fields.Many2one(
        "mrp.workorder",
        string="Work Order",
        help="Work order that consumed this component quantity.",
    )


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    def _console_update_component_qty_done_per_wo(self):
        """Adjust component move lines qty_done based on console quantities."""
        for mo in self:
            workorders = mo.workorder_ids.filtered(lambda w: w.console_qty > 0)
            if not workorders:
                continue

            wo_round = mo.product_uom_id.rounding or 0.0001

            for move in mo.move_raw_ids.filtered(lambda m: m.state != "cancel"):
                total_required = move.product_uom_qty or 0.0
                if float_is_zero(total_required, precision_rounding=move.product_uom.rounding or 0.0001):
                    continue
                if not mo.product_qty:
                    continue
                factor = total_required / mo.product_qty
                move_round = move.product_uom.rounding or 0.0001

                for wo in workorders:
                    produced_qty = wo.console_qty or 0.0
                    if float_is_zero(produced_qty, precision_rounding=wo_round):
                        continue

                    required_qty = factor * produced_qty
                    wo_lines = move.move_line_ids.filtered(lambda ml, w=wo: ml.workorder_id == w)
                    if not wo_lines:
                        continue

                    base_total = sum(line.quantity for line in wo_lines)
                    remaining = required_qty
                    for idx, line in enumerate(wo_lines):
                        if idx == len(wo_lines) - 1:
                            new_qty = remaining
                        else:
                            ratio = 0.0
                            if not float_is_zero(base_total, precision_rounding=move_round):
                                ratio = line.quantity / base_total
                            new_qty = float_round(required_qty * ratio, precision_rounding=move_round)
                            remaining -= new_qty

                        if new_qty < 0:
                            new_qty = 0.0
                        line.with_context(bypass_reservation_update=True).write(
                            {"quantity": new_qty}
                        )
