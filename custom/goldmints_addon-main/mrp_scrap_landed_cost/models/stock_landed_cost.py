import logging

from odoo import models

_logger = logging.getLogger(__name__)


class StockLandedCost(models.Model):
    _inherit = "stock.landed.cost"

    def _get_scrap_cost_by_mo(self, mo):

        domain = [
            "&",
            "&",
            "&",
            "|",
            ("production_id", "=", mo.id),
            ("workorder_id.production_id", "=", mo.id),
            ("state", "=", "done"),
            ("landed_cost_id", "=", False),
            ("company_id", "=", self.company_id.id),
        ]
        scraps = self.env["stock.scrap"].search(domain)
        _logger.info(
            "MO %s: Found %d scraps with domain %s", mo.name, len(scraps), domain
        )

        total_cost = 0.0
        for scrap in scraps:
            scrap_val = 0.0
            if scrap.move_ids:
                for move in scrap.move_ids:
                    if move.stock_valuation_layer_ids:
                        scrap_val += sum(
                            move.stock_valuation_layer_ids.mapped(
                                lambda layer: abs(layer.value)
                            )
                        )
                if scrap_val:
                    _logger.info("Scrap %s: Using SVL val=%.2f", scrap.name, scrap_val)

            if not scrap_val:
                scrap_val = scrap.product_id.standard_price * scrap.scrap_qty
                _logger.info(
                    "Scrap %s: Using Standard Price=%.2f * qty=%.2f = %.2f",
                    scrap.name,
                    scrap.product_id.standard_price,
                    scrap.scrap_qty,
                    scrap_val,
                )

            total_cost += scrap_val

        _logger.info("MO %s: Total scrap cost=%.2f", mo.name, total_cost)
        return total_cost

    def _get_scrap_cost_by_mo_and_product(self):
        result = {}
        for mo in self.mrp_production_ids:
            fg_product = mo.product_id
            scrap_cost = self._get_scrap_cost_by_mo(mo)
            if scrap_cost > 0:
                if fg_product.id not in result:
                    result[fg_product.id] = {
                        "product": fg_product,
                        "cost": 0.0,
                        "mos": self.env["mrp.production"],
                    }
                result[fg_product.id]["cost"] += scrap_cost
                result[fg_product.id]["mos"] |= mo
        return result

    def compute_landed_cost(self):
        for lc in self:
            if lc.mrp_production_ids:
                scrap_lines = lc.cost_lines.filtered(
                    lambda line: line.product_id.is_scrap_cost
                )
                if not scrap_lines:
                    scrap_lines = lc.cost_lines.filtered(
                        lambda line: any(
                            keyword in (line.product_id.name or "").lower()
                            for keyword in ["scrap", "scarp"]
                        )
                    )

                scrap_by_product = lc._get_scrap_cost_by_mo_and_product()
                total_scrap_cost = sum(v["cost"] for v in scrap_by_product.values())
                _logger.info(
                    "LC %s: total_scrap_cost=%.2f, scrap_by_product=%s",
                    lc.name,
                    total_scrap_cost,
                    {p: v["cost"] for p, v in scrap_by_product.items()},
                )

                if total_scrap_cost > 0 and scrap_lines:
                    scrap_lines[0].write({"price_unit": total_scrap_cost})

        res = super().compute_landed_cost()

        for lc in self:
            if lc.mrp_production_ids:
                scrap_by_product = lc._get_scrap_cost_by_mo_and_product()
                if not scrap_by_product:
                    continue

                scrap_lines = lc.cost_lines.filtered(
                    lambda line: line.product_id.is_scrap_cost
                )
                if not scrap_lines:
                    scrap_lines = lc.cost_lines.filtered(
                        lambda line: any(
                            keyword in (line.product_id.name or "").lower()
                            for keyword in ["scrap", "scarp"]
                        )
                    )
                if not scrap_lines:
                    continue

                scrap_cost_line = scrap_lines[0]
                adj_lines = lc.valuation_adjustment_lines.filtered(
                    lambda line: line.cost_line_id == scrap_cost_line
                )

                for adj_line in adj_lines:
                    fg_product_id = adj_line.product_id.id
                    if fg_product_id in scrap_by_product:
                        new_cost = scrap_by_product[fg_product_id]["cost"]
                        adj_line.write({"additional_landed_cost": new_cost})
                        _logger.info(
                            "LC %s: Updated adj_line for product %s, new_cost=%.2f",
                            lc.name,
                            adj_line.product_id.name,
                            new_cost,
                        )
                    else:
                        adj_line.write({"additional_landed_cost": 0.0})
                        _logger.info(
                            "LC %s: Zero adj_line for product %s (no scrap for this product)",
                            lc.name,
                            adj_line.product_id.name,
                        )

        return res

    def button_validate(self):
        from collections import defaultdict

        from odoo.tools.float_utils import float_is_zero

        self._check_can_validate()
        cost_without_adjusment_lines = self.filtered(
            lambda c: not c.valuation_adjustment_lines
        )
        if cost_without_adjusment_lines:
            cost_without_adjusment_lines.compute_landed_cost()
        if not self._check_sum():
            from odoo import _
            from odoo.exceptions import UserError

            raise UserError(
                _(
                    "Cost and adjustments lines do not match. You should maybe recompute the landed costs."
                )
            )

        for cost in self:
            cost = cost.with_company(cost.company_id)
            move = self.env["account.move"]
            move_vals = {
                "journal_id": cost.account_journal_id.id,
                "date": cost.date,
                "ref": cost.name,
                "line_ids": [],
                "move_type": "entry",
            }
            valuation_layer_ids = []
            cost_to_add_byproduct = defaultdict(lambda: 0.0)
            cost_to_add_bylot = defaultdict(lambda: defaultdict(float))

            for line in cost.valuation_adjustment_lines.filtered(
                lambda line: line.move_id
            ):
                remaining_qty = sum(
                    line.move_id._get_stock_valuation_layer_ids().mapped(
                        "remaining_qty"
                    )
                )
                linked_layer = line.move_id._get_stock_valuation_layer_ids()
                move_qty = line.move_id.product_uom._compute_quantity(
                    line.move_id.quantity, line.move_id.product_id.uom_id
                )

                # CUSTOM: Use full cost for scrap cost products (Option B)
                is_scrap_cost = getattr(
                    line.cost_line_id.product_id, "is_scrap_cost", False
                )
                if is_scrap_cost and remaining_qty > 0:
                    # Allocate FULL cost to remaining inventory
                    cost_to_add = line.additional_landed_cost
                    _logger.info(
                        "Scrap cost allocation: Full cost=%.2f to remaining_qty=%.2f",
                        cost_to_add,
                        remaining_qty,
                    )
                else:
                    # Standard proration
                    cost_to_add = (
                        (remaining_qty / move_qty) * line.additional_landed_cost
                        if move_qty
                        else 0
                    )

                product = line.move_id.product_id
                if not cost.company_id.currency_id.is_zero(cost_to_add):
                    vals_list = []
                    if line.move_id.product_id.lot_valuated:
                        for lot_id, sml in line.move_id.move_line_ids.grouped(
                            "lot_id"
                        ).items():
                            if not lot_id.quantity_svl:
                                continue
                            lot_layer = linked_layer.filtered(
                                lambda l: l.lot_id == lot_id
                            )[:1]
                            value = cost_to_add * lot_id.quantity_svl / remaining_qty
                            if product.cost_method in ["average", "fifo"]:
                                cost_to_add_bylot[product][lot_id] += value
                            vals_list.append(
                                {
                                    "value": value,
                                    "unit_cost": 0,
                                    "quantity": 0,
                                    "remaining_qty": 0,
                                    "stock_valuation_layer_id": lot_layer.id,
                                    "description": cost.name,
                                    "stock_move_id": line.move_id.id,
                                    "product_id": line.move_id.product_id.id,
                                    "stock_landed_cost_id": cost.id,
                                    "company_id": cost.company_id.id,
                                    "lot_id": lot_id.id,
                                }
                            )
                            lot_layer.remaining_value += value
                    else:
                        vals_list.append(
                            {
                                "value": cost_to_add,
                                "unit_cost": 0,
                                "quantity": 0,
                                "remaining_qty": 0,
                                "stock_valuation_layer_id": linked_layer[:1].id,
                                "description": cost.name,
                                "stock_move_id": line.move_id.id,
                                "product_id": line.move_id.product_id.id,
                                "stock_landed_cost_id": cost.id,
                                "company_id": cost.company_id.id,
                            }
                        )
                        linked_layer[:1].remaining_value += cost_to_add
                    valuation_layer = self.env["stock.valuation.layer"].create(
                        vals_list
                    )
                    valuation_layer_ids += valuation_layer.ids

                if product.cost_method in ["average", "fifo"]:
                    cost_to_add_byproduct[product] += cost_to_add

                if product.valuation != "real_time":
                    continue

                # CUSTOM: For scrap costs, skip "already out" by passing qty_out=0
                if is_scrap_cost:
                    qty_out = 0
                else:
                    qty_out = 0
                    if line.move_id._is_in():
                        qty_out = line.move_id.quantity - remaining_qty
                    elif line.move_id._is_out():
                        qty_out = line.move_id.quantity

                move_vals["line_ids"] += line._create_accounting_entries(move, qty_out)

            products = (
                self.env["product.product"]
                .browse(p.id for p in cost_to_add_byproduct.keys())
                .with_company(cost.company_id)
            )
            for product in products:
                if not float_is_zero(
                    product.quantity_svl, precision_rounding=product.uom_id.rounding
                ):
                    product.sudo().with_context(
                        disable_auto_svl=True
                    ).standard_price += (
                        cost_to_add_byproduct[product] / product.quantity_svl
                    )
                if product.lot_valuated:
                    for lot, value in cost_to_add_bylot[product].items():
                        if float_is_zero(
                            lot.quantity_svl, precision_rounding=product.uom_id.rounding
                        ):
                            continue
                        lot.sudo().with_context(
                            disable_auto_svl=True
                        ).standard_price += value / lot.quantity_svl

            move_vals["stock_valuation_layer_ids"] = [(6, None, valuation_layer_ids)]
            cost_vals = {"state": "done"}
            if move_vals.get("line_ids"):
                move = move.create(move_vals)
                cost_vals.update({"account_move_id": move.id})
            cost.write(cost_vals)
            if cost.account_move_id:
                move._post()
            cost.reconcile_landed_cost()

            # CUSTOM: Mark scraps as absorbed
            if cost.mrp_production_ids:
                for mo in cost.mrp_production_ids:
                    scraps = self.env["stock.scrap"].search(
                        [
                            "|",
                            ("production_id", "=", mo.id),
                            ("workorder_id.production_id", "=", mo.id),
                            ("state", "=", "done"),
                            ("landed_cost_id", "=", False),
                            ("company_id", "=", cost.company_id.id),
                        ]
                    )
                    scraps.write({"landed_cost_id": cost.id})
                    mo.write({"cost_finalized": True})

        return True
