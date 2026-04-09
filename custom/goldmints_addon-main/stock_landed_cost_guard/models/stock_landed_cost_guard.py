from collections import defaultdict
from odoo import models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_is_zero


class StockLandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    def _guarded_ratio_components(self, line):
        """Return (ratio, remaining_qty, base_qty, move_qty).

        - ratio is clamped to [0, 1] to avoid over-allocation or negative allocations.
        - base_qty prefers the SVL quantity (authoritative for valuation) and falls back to move_qty.
        """
        line_svls = line.move_id._get_stock_valuation_layer_ids()
        remaining_qty = sum(line_svls.mapped('remaining_qty'))
        svl_qty = sum(line_svls.mapped('quantity'))

        move_qty = line.move_id.product_uom._compute_quantity(
            line.move_id.quantity, line.move_id.product_id.uom_id
        )

        base_qty = svl_qty or move_qty
        prec = line.move_id.product_id.uom_id.rounding or 0.0001

        if float_is_zero(base_qty, precision_rounding=prec):
            return 0.0, remaining_qty, base_qty, move_qty

        # Clamp to [0, 1] to prevent amplification and negative ratio on returns/corrections.
        raw_ratio = remaining_qty / base_qty
        ratio = max(0.0, min(1.0, raw_ratio))
        return ratio, remaining_qty, base_qty, move_qty

    def button_validate(self):
        # === Upstream pre-checks ===
        self._check_can_validate()
        costs_no_lines = self.filtered(lambda c: not c.valuation_adjustment_lines)
        if costs_no_lines:
            costs_no_lines.compute_landed_cost()
        if not self._check_sum():
            raise UserError(_('Cost and adjustments lines do not match. You should maybe recompute the landed costs.'))

        for cost in self:
            cost = cost.with_company(cost.company_id)
            move_model = self.env['account.move']
            move_vals = {
                'journal_id': cost.account_journal_id.id,
                'date': cost.date,
                'ref': cost.name,
                'line_ids': [],
                'move_type': 'entry',
            }
            valuation_layer_ids = []
            cost_to_add_byproduct = defaultdict(lambda: 0.0)             # for AVCO/FIFO product-level updates
            cost_to_add_bylot = defaultdict(lambda: defaultdict(float))  # for AVCO/FIFO lot-level updates

            for line in cost.valuation_adjustment_lines.filtered(lambda l: l.move_id):
                product = line.move_id.product_id
                linked_layer = line.move_id._get_stock_valuation_layer_ids()

                # Defensive: if no SVL found, skip allocation for this line (nothing to adjust)
                if not linked_layer:
                    continue

                ratio, remaining_qty, base_qty, move_qty = self._guarded_ratio_components(line)

                # Use guarded ratio (<=1 and >=0) to prevent amplification or negative allocation
                cost_to_add = ratio * line.additional_landed_cost

                if not cost.company_id.currency_id.is_zero(cost_to_add):
                    vals_list = []
                    if getattr(product, 'lot_valuated', False):
                        # Split allocation by lot, proportionally to each lot's remaining_qty
                        # 1) build per-lot weights and initial values
                        lot_quantities = []
                        total_lot_remaining = 0.0
                        # Expecting a helper 'grouped' on recordset; if your version lacks it,
                        # replace with a manual grouping by lot_id.
                        for lot_id, sml in line.move_id.move_line_ids.grouped('lot_id').items():
                            lot_remaining_qty = sum(
                                linked_layer.filtered(lambda svl: svl.lot_id == lot_id).mapped('remaining_qty')
                            )
                            # Skip empty lots
                            if float_is_zero(lot_remaining_qty, precision_rounding=lot_id.product_id.uom_id.rounding):
                                continue
                            lot_quantities.append((lot_id, lot_remaining_qty))
                            total_lot_remaining += lot_remaining_qty

                        if total_lot_remaining and base_qty:
                            # 2) compute proportional values and track rounding residue
                            provisional_vals = []
                            running_sum = 0.0
                            for idx, (lot_id, lot_remaining_qty) in enumerate(lot_quantities, start=1):
                                # Proportional to remaining vs base of the original move (stable with partial consumption)
                                value = (line.additional_landed_cost * lot_remaining_qty / base_qty)
                                # Keep for residue rebalancing
                                provisional_vals.append((lot_id, value))
                                running_sum += value

                            # Adjust rounding to ensure the sum equals cost_to_add exactly
                            residue = cost_to_add - running_sum
                            if provisional_vals:
                                # put residue on the lot with the largest remaining qty (or the last) to minimize distortion
                                pivot_index = max(range(len(lot_quantities)), key=lambda i: lot_quantities[i][1]) \
                                              if len(lot_quantities) > 1 else 0
                                lot_id_pivot, pivot_value = provisional_vals[pivot_index]
                                provisional_vals[pivot_index] = (lot_id_pivot, pivot_value + residue)

                            # 3) create SVLs and accumulate for AVCO/FIFO per-lot updates
                            for lot_id, value in provisional_vals:
                                lot_layer = linked_layer.filtered(lambda svl: svl.lot_id == lot_id)[:1]
                                if not lot_layer:
                                    # If we can’t find a lot-specific SVL, skip this lot safely
                                    continue
                                if product.cost_method in ['average', 'fifo']:
                                    cost_to_add_bylot[product][lot_id] += value
                                vals_list.append({
                                    'value': value,
                                    'unit_cost': 0,
                                    'quantity': 0,
                                    'remaining_qty': 0,
                                    'stock_valuation_layer_id': lot_layer.id,
                                    'description': cost.name,
                                    'stock_move_id': line.move_id.id,
                                    'product_id': product.id,
                                    'stock_landed_cost_id': cost.id,
                                    'company_id': cost.company_id.id,
                                    'lot_id': lot_id.id,
                                })
                                lot_layer.remaining_value += value
                        else:
                            # Edge: no total lot remaining or base_qty=0 => nothing to allocate at lot level
                            pass
                    else:
                        # Single SVL adjustment (non lot-valuated)
                        head_layer = linked_layer[:1]
                        vals_list.append({
                            'value': cost_to_add,
                            'unit_cost': 0,
                            'quantity': 0,
                            'remaining_qty': 0,
                            'stock_valuation_layer_id': head_layer.id,
                            'description': cost.name,
                            'stock_move_id': line.move_id.id,
                            'product_id': product.id,
                            'stock_landed_cost_id': cost.id,
                            'company_id': cost.company_id.id,
                        })
                        head_layer.remaining_value += cost_to_add

                    if vals_list:
                        valuation_layer = self.env['stock.valuation.layer'].create(vals_list)
                        valuation_layer_ids += valuation_layer.ids

                # AVCO/FIFO product-level accumulation (unchanged idea, safer ratio now)
                if product.cost_method in ['average', 'fifo']:
                    cost_to_add_byproduct[product] += cost_to_add

                # Accounting entries only for real-time valuation categories
                if product.valuation != "real_time":
                    continue

                qty_out = 0.0
                if line.move_id._is_in():
                    # Partially consumed incoming move: only the consumed part needs expense recognition
                    qty_out = move_qty - remaining_qty
                elif line.move_id._is_out():
                    # Outgoing move: full move quantity is out
                    qty_out = move_qty

                move_vals['line_ids'] += line._create_accounting_entries(move_model, qty_out)

            # === AVCO/FIFO standard price computations ===
            products = self.env['product.product'].browse(p.id for p in cost_to_add_byproduct.keys()).with_company(cost.company_id)
            for product in products:
                # Product-level standard price bump if there is stock
                if not float_is_zero(product.quantity_svl, precision_rounding=product.uom_id.rounding):
                    product.sudo().with_context(disable_auto_svl=True).standard_price += (
                        cost_to_add_byproduct[product] / product.quantity_svl
                    )
                # Lot-level price bump when lot valuation is enabled
                if getattr(product, 'lot_valuated', False):
                    for lot, value in cost_to_add_bylot[product].items():
                        if float_is_zero(lot.quantity_svl, precision_rounding=product.uom_id.rounding):
                            continue
                        lot.sudo().with_context(disable_auto_svl=True).standard_price += value / lot.quantity_svl

            # Link created valuation layers to the accounting move
            if valuation_layer_ids:
                move_vals['stock_valuation_layer_ids'] = [(6, 0, valuation_layer_ids)]

            # Finalize accounting move (create + post if needed)
            cost_vals = {'state': 'done'}
            am = False
            if move_vals.get('line_ids'):
                am = move_model.create(move_vals)
                cost_vals.update({'account_move_id': am.id})

            cost.write(cost_vals)

            if am:
                # BUGFIX: Post the actual created move, not the model
                am._post()

            # Reconcile landed cost after posting
            cost.reconcile_landed_cost()

        return True
