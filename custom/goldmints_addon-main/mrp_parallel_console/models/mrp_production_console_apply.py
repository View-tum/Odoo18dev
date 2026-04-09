# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from collections import defaultdict

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero, float_round, groupby as tools_groupby
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    mpc_supervisor_checked = fields.Boolean(
        string="Supervisor Checked",
        default=False,
        help="Indicates if the supervisor has verified this MO.",
        copy=False,
    )
    mpc_supervisor_id = fields.Many2one(
        "res.users",
        string="Supervisor",
        copy=False,
    )
    mpc_supervisor_check_date = fields.Datetime(
        string="Supervisor Check Date",
        copy=False,
    )

    workorder_count = fields.Integer(
        string="Workorder Count",
        compute="_compute_workorder_count",
        store=False,
    )

    def _compute_workorder_count(self):
        for mo in self:
            mo.workorder_count = len(mo.workorder_ids)

    def _post_inventory(self, cancel_backorder=False):
        moves_to_do, moves_not_to_do, moves_to_cancel = set(), set(), set()
        for move in self.move_raw_ids:
            if move.state == 'done':
                moves_not_to_do.add(move.id)
            elif not move.picked:
                moves_to_cancel.add(move.id)
            elif move.state != 'cancel':
                moves_to_do.add(move.id)

        self.with_context(skip_mo_check=True).env['stock.move'].browse(moves_to_do)._action_done(cancel_backorder=cancel_backorder)
        self.with_context(skip_mo_check=True).env['stock.move'].browse(moves_to_cancel)._action_cancel()
        moves_to_do = self.move_raw_ids.filtered(lambda x: x.state == 'done') - self.env['stock.move'].browse(moves_not_to_do)

        moves_to_do_by_order = defaultdict(lambda: self.env['stock.move'], [
            (key, self.env['stock.move'].concat(*values))
            for key, values in tools_groupby(moves_to_do, key=lambda m: m.raw_material_production_id.id)
        ])
        for order in self:
            finish_moves = order.move_finished_ids.filtered(lambda m: m.product_id == order.product_id and m.state not in ('done', 'cancel'))
            for move in finish_moves:
                # ODOO FIX: 'qty_produced' sums all moves where 'picked=True'.
                # The Shopfloor Console pre-sets 'picked=True', causing 'qty_produced' to include the current move.
                # Standard Odoo calculates move.quantity = qty_producing - qty_produced, which results in 0
                # and wipes out the move lines. We calculate the strictly 'done' qty instead.
                strictly_done_qty = sum(order.move_finished_ids.filtered(
                    lambda m: m.state == 'done' and m.product_id == order.product_id
                ).mapped('quantity'))
                
                new_qty = float_round(order.qty_producing - strictly_done_qty, precision_rounding=order.product_uom_id.rounding, rounding_method='HALF-UP')
                if float_compare(move.quantity, new_qty, precision_rounding=order.product_uom_id.rounding) != 0:
                    move.quantity = new_qty
                
                extra_vals = order._prepare_finished_extra_vals()
                if extra_vals:
                    move.move_line_ids.write(extra_vals)
            for workorder in order.workorder_ids:
                if workorder.state not in ('done', 'cancel'):
                    workorder.duration_expected = workorder._get_duration_expected()
                if workorder.duration == 0.0:
                    workorder.duration = workorder.duration_expected
                    workorder.duration_unit = round(workorder.duration / max(workorder.qty_produced, 1), 2)
            order._cal_price(moves_to_do_by_order[order.id])

        moves_to_finish = self.move_finished_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
        moves_to_finish.picked = True

        for move in moves_to_finish:
            unpicked = move.move_line_ids.filtered(lambda ml: not ml.picked)
            if unpicked:
                unpicked.write({'picked': True})
            lotless = move.move_line_ids.filtered(lambda ml: not ml.lot_id)
            if lotless and move.production_id and move.production_id.lot_producing_id:
                lotless.write({'lot_id': move.production_id.lot_producing_id.id})

        moves_to_finish = moves_to_finish._action_done(cancel_backorder=cancel_backorder)
        for order in self:
            consume_move_lines = moves_to_do_by_order[order.id].mapped('move_line_ids')
            order.move_finished_ids.move_line_ids.consume_line_ids = [(6, 0, consume_move_lines.ids)]
        return True

    def action_open_parallel_console(self):
        self.ensure_one()
        action = self.env.ref(
            "mrp_parallel_console.mrp_parallel_console_action_workorder_console"
        ).read()[0]

        ctx = action.get("context") or {}
        if isinstance(ctx, str):
            ctx = safe_eval(ctx)
        ctx = dict(ctx or {})
        ctx.update(
            self.env.context,
            default_production_id=self.id,
        )
        action["context"] = ctx
        action["res_id"] = self.id
        action["res_model"] = self._name
        params = action.get("params") or {}
        params.update({"production_id": self.id})
        action["params"] = params
        return action

    def action_open_mo_chain_cost_analysis(self):
        """Open Production Analysis filtered to this MO + its backorders."""
        self.ensure_one()
        try:
            action = self.env.ref(
                "mrp_account_enterprise.mrp_report_dashboard_action"
            ).read()[0]
        except Exception:
            raise UserError(
                _(
                    "Production Analysis is not available. "
                    "Please ensure the Manufacturing Costing module is installed."
                )
            )

        mo_ids = (
            self.procurement_group_id.mrp_production_ids.ids
            if self.procurement_group_id
            else [self.id]
        )
        if self.id not in mo_ids:
            mo_ids.append(self.id)

        ctx = action.get("context") or {}
        if isinstance(ctx, str):
            ctx = safe_eval(ctx)
        ctx = dict(ctx or {})
        # Disable default period filter to avoid hiding older MO chains.
        ctx["search_default_filter_date_finished"] = 0
        action["context"] = ctx
        action["domain"] = [("production_id", "in", mo_ids)]
        action["name"] = _("Production Analysis: %s") % (self.name or self.display_name)
        return action

    def _console_apply_quantities_and_backorder(self, workorders):
        """Apply console quantities for the given workorders and close MO.

        Flow per MO:
        - Sum console_qty of the selected workorders.
        - Set qty_producing on the MO to that sum.
        - For each selected WO:
          * set qty_produced = console_qty
          * mark as done, close productivity lines.
        - Call button_mark_done() so the standard wizards (consumption, backorder)
          can run when necessary.
        """
        workorders = workorders.filtered(
            lambda wo_rec: wo_rec.production_id in self and wo_rec.state != "cancel"
        )
        if not workorders:
            return False

        action = False
        for mo in self:
            wo_mo = workorders.filtered(lambda wo_rec, mo_rec=mo: wo_rec.production_id == mo_rec)
            if not wo_mo:
                continue

            mo._console_validate_before_apply()

            total_console_qty = mo._console_compute_total_qty(wo_mo)

            # For overproduction: sync demands BEFORE setting qty_producing
            # so Odoo's _set_qty_producing() calculates consumption based on updated demands
            rounding = mo.product_uom_id.rounding or 0.000001
            if float_compare(total_console_qty, mo.product_qty, precision_rounding=rounding) > 0:
                mo._console_sync_demand_and_replenish(total_console_qty)

            # Now set qty_producing - this triggers Odoo's _set_qty_producing()
            # which handles component filling automatically
            mo.qty_producing = total_console_qty

            # 2) close each selected workorder with console_qty
            now = fields.Datetime.now()
            self._console_close_workorders(wo_mo, now)

            # Force "Set Quantities & Validate" behavior to keep consumption aligned with BOM.
            mo._console_fill_move_quantities_for_close({mo.id: total_console_qty})

            # 3) run standard logic (may return wizards)
            ctx = dict(self.env.context or {})
            ctx.pop("skip_backorder", None)
            ctx.pop("mo_ids_to_backorder", None)
            ctx.update({"skip_consumption": True})

            res = mo.with_context(ctx).button_mark_done()

            if res and not action:
                if (
                    isinstance(res, dict)
                    and res.get("type") == "ir.actions.act_window"
                    and not res.get("views")
                ):
                    res["views"] = [(False, "form")]
                action = res

        return action

    def _console_sync_demand_and_replenish(self, total_console_qty):
        self.ensure_one()
        rounding = self.product_uom_id.rounding or 0.000001

        is_overproduction = float_compare(total_console_qty, self.product_qty, precision_rounding=rounding) > 0

        if not is_overproduction:
            return False

        param_key = "mrp_parallel_console.auto_replenish_overproduction"
        if self.env["ir.config_parameter"].sudo().get_param(param_key, "True") != "True":
            return False

        self.write({"product_qty": total_console_qty})

        bom = self.bom_id
        bom_qty = bom.product_qty if bom else 1.0

        bom_line_map = {}
        if bom:
            for bom_line in bom.bom_line_ids:
                bom_line_map[bom_line.product_id.id] = bom_line

        for move in self.move_raw_ids.filtered(lambda move_rec: move_rec.state not in ("done", "cancel")):
            move_rounding = move.product_uom.rounding or 0.000001

            bom_line = bom_line_map.get(move.product_id.id)
            if bom_line and bom_qty:
                bom_qty_per_unit = bom_line.product_qty / bom_qty
                new_demand = float_round(bom_qty_per_unit * total_console_qty, precision_rounding=move_rounding)
            else:
                mo_qty = self.product_qty or 1.0
                ratio = total_console_qty / mo_qty
                new_demand = float_round(move.product_uom_qty * ratio, precision_rounding=move_rounding)

            if float_compare(new_demand, move.product_uom_qty, precision_rounding=move_rounding) != 0:
                move.write({"product_uom_qty": new_demand})

            if move.procure_method == "make_to_order":
                move._action_confirm()
            else:
                move._action_assign()

        return True


    def _console_sync_component_overconsumption(self):
        return self.action_sync_picked_quantities()

    def action_sync_picked_quantities(self):
        """Sync component quantities from validated pickings.

        For each raw material move, calculate the total quantity from validated
        original moves (pickings) and update the move's quantity.
        """
        updated = False
        from collections import defaultdict

        for mo in self:
            for move in mo.move_raw_ids.filtered(lambda move_rec: move_rec.state not in ("done", "cancel")):
                rounding = move.product_uom.rounding or 0.000001
                orig_moves = move.move_orig_ids.filtered(lambda m_orig: m_orig.state == "done")
                if not orig_moves:
                    continue

                total_picked = sum(orig_moves.mapped("quantity"))
                if not total_picked:
                    continue

                # Cap at product_uom_qty to avoid over-filling from shared or large batch pickings.
                # Calculate a ratio to scale down lot quantities proportionally.
                max_sync = move.product_uom_qty
                ratio = min(1.0, max_sync / total_picked) if total_picked > 0 else 1.0

                # 1. Sync Move Lines (Lots)
                needed_lines = defaultdict(float)
                for orig_line in orig_moves.move_line_ids:
                    needed_lines[(orig_line.lot_id, orig_line.location_dest_id)] += orig_line.quantity

                current_lines = move.move_line_ids
                for (lot, location), qty in needed_lines.items():
                    # Apply ratio and round
                    capped_qty = float_round(qty * ratio, precision_rounding=rounding)
                    if float_is_zero(capped_qty, precision_rounding=rounding):
                        continue

                    matched_line = current_lines.filtered(
                        lambda line: line.lot_id == lot and line.location_id == location
                    )
                    if matched_line:
                        if float_compare(matched_line[0].quantity, capped_qty, precision_rounding=rounding) != 0:
                            matched_line[0].write({'quantity': capped_qty})
                            updated = True
                    else:
                        move.move_line_ids.create({
                            'move_id': move.id,
                            'product_id': move.product_id.id,
                            'product_uom_id': move.product_uom.id,
                            'location_id': location.id,
                            'location_dest_id': move.location_dest_id.id,
                            'lot_id': lot.id if lot else False,
                            'quantity': capped_qty,
                        })
                        updated = True

                # 2. Update total quantity if needed
                total_to_sync = float_round(total_picked * ratio, precision_rounding=rounding)
                current_qty = move.quantity if 'quantity' in move._fields else move.quantity_done
                if float_compare(total_to_sync, current_qty, precision_rounding=rounding) > 0:
                    if 'quantity' in move._fields:
                        move.write({'quantity': total_to_sync})
                    else:
                        move.write({'quantity_done': total_to_sync})
                    updated = True
        return updated


    def _console_compute_total_qty(self, workorders):
        """Compute MO qty from console entries based on operation topology."""
        self.ensure_one()
        workorders = workorders.filtered(lambda wo: wo.state != "cancel")
        if not workorders:
            return 0.0

        qty_by_operation = {}
        for wo in workorders:
            op = wo.operation_id
            if not op:
                continue
            qty_by_operation.setdefault(op, [])

            # Use sum of logs if available to match UI "effective" quantity
            logs = self.env["mrp.workorder.qty.log"].search([("workorder_id", "=", wo.id)])
            effective_qty = sum(logs.mapped("qty")) if logs else wo.console_qty
            qty_by_operation[op].append(effective_qty or 0.0)

        op_totals = []
        rounding = self.product_uom_id.rounding or 0.000001
        for op, qty_list in qty_by_operation.items():
            if not qty_list:
                continue
            if op.parallel_mode == "parallel":
                op_qty = sum(qty_list)
            else:
                base = qty_list[0]
                for qty in qty_list[1:]:
                    if float_compare(qty, base, precision_rounding=rounding) != 0:
                        raise UserError(
                            _(
                                "Workorders for operation %s have inconsistent quantities (%s vs %s). "
                                "Please review the console entries."
                            )
                            % (op.display_name, base, qty)
                        )
                op_qty = base
            op_totals.append(op_qty)

        # Use the bottleneck quantity (minimum across the operation chain).
        # This ensures that if downstream operations report fewer finished units
        # than upstream steps, the MO is closed at the lower quantity and the
        # remainder is pushed to a backorder.
        total_good_qty = min(op_totals) if op_totals else 0.0

        # Add FG Scrap quantities (Draft) to the total
        # This ensures Odoo considers "Scrap" as "Processed", preventing Backorders
        # for quantities that were actually produced but rejected.
        scraps = self.env["stock.scrap"].search(
            [
                ("production_id", "=", self.id),
                ("product_id", "=", self.product_id.id),
                ("state", "=", "draft"),
            ]
        )
        total_scrap_qty = sum(scraps.mapped("scrap_qty"))

        return total_good_qty + total_scrap_qty

    def _console_fill_move_quantities_for_close(self, finished_qty_map=None):
        finished_qty_map = finished_qty_map or {}
        for mo in self:
            target_finished_qty = finished_qty_map.get(mo.id)
            self._console_fill_component_moves(mo, target_producing_qty=target_finished_qty)
            self._console_fill_finished_moves(mo, target_finished_qty)




    @staticmethod
    def _console_fill_component_moves(mo, target_producing_qty=None):
        if target_producing_qty is None:
            target_producing_qty = mo.qty_producing or mo.product_qty

        rounding = mo.product_uom_id.rounding or 0.000001
        is_overproduction = float_compare(target_producing_qty, mo.product_qty, precision_rounding=rounding) >= 0

        for move in mo.move_raw_ids:
            if move.state in ("done", "cancel"):
                continue

            if is_overproduction:
                target_qty = move.product_uom_qty
            else:
                ratio = target_producing_qty / mo.product_qty if mo.product_qty else 1.0
                move_rounding = move.product_uom.rounding or 0.000001
                target_qty = float_round(move.product_uom_qty * ratio, precision_rounding=move_rounding)

            MrpProduction._console_set_move_done_quantity(move, target_qty)



    @staticmethod
    def _console_set_move_done_quantity(move, target_qty):
        if target_qty is None or target_qty < 0:
            target_qty = 0.0

        rounding = move.product_uom.rounding or 0.000001
        target_qty = float_round(target_qty, precision_rounding=rounding)
        tracked = move.product_id.tracking in ("lot", "serial")
        remaining_qty = target_qty

        lines_with_lots = move.move_line_ids.filtered(lambda ln: ln.lot_id or ln.lot_name)
        lines_without_lots = move.move_line_ids.filtered(lambda ln: not (ln.lot_id or ln.lot_name))

        if tracked:
            if lines_without_lots:
                lines_without_lots.unlink()

            if lines_with_lots:
                zero_lines = move.env["stock.move.line"]
                for line in lines_with_lots.sorted("id"):
                    line_qty = min(line.quantity or 0.0, remaining_qty)
                    line.write(
                        {
                            "quantity": line_qty,
                            "picked": not float_is_zero(line_qty, precision_rounding=rounding),
                        }
                    )
                    remaining_qty = float_round(
                        remaining_qty - line_qty,
                        precision_rounding=rounding,
                    )
                    if float_is_zero(line_qty, precision_rounding=rounding):
                        zero_lines |= line
                if zero_lines:
                    zero_lines.unlink()

            if not float_is_zero(remaining_qty, precision_rounding=rounding):
                existing_line_ids = set(move.move_line_ids.ids)
                try:
                    move._action_assign()
                except Exception:
                    pass
                new_lot_lines = move.move_line_ids.filtered(
                    lambda ln, existing_ids=existing_line_ids: (ln.lot_id or ln.lot_name)
                    and ln.id not in existing_ids
                )
                if new_lot_lines:
                    zero_lines = move.env["stock.move.line"]
                    for line in new_lot_lines.sorted("id"):
                        if float_is_zero(remaining_qty, precision_rounding=rounding):
                            zero_lines |= line
                            continue
                        candidate_qty = line.quantity or remaining_qty
                        line_qty = min(candidate_qty, remaining_qty)
                        line.write(
                            {
                                "quantity": line_qty,
                                "picked": not float_is_zero(line_qty, precision_rounding=rounding),
                            }
                        )
                        remaining_qty = float_round(
                            remaining_qty - line_qty,
                            precision_rounding=rounding,
                        )
                        if float_is_zero(line_qty, precision_rounding=rounding):
                            zero_lines |= line
                    if zero_lines:
                        zero_lines.unlink()

            if not float_is_zero(remaining_qty, precision_rounding=rounding):
                lot_id = False
                if move.production_id and move.production_id.lot_producing_id:
                    lot_id = move.production_id.lot_producing_id.id

                if lot_id:
                    move.env["stock.move.line"].create({
                        "move_id": move.id,
                        "product_id": move.product_id.id,
                        "product_uom_id": move.product_uom.id,
                        "location_id": move.location_id.id,
                        "location_dest_id": move.location_dest_id.id,
                        "lot_id": lot_id,
                        "quantity": remaining_qty,
                        "picked": True,
                    })
                else:
                    quant = move.env["stock.quant"].search([
                        ("product_id", "=", move.product_id.id),
                        ("quantity", ">", 0),
                        ("lot_id", "!=", False),
                        ("location_id", "child_of", move.location_id.id),
                    ], limit=1, order="in_date, id")
                    if quant:
                        move.env["stock.move.line"].create({
                            "move_id": move.id,
                            "product_id": move.product_id.id,
                            "product_uom_id": move.product_uom.id,
                            "location_id": move.location_id.id,
                            "location_dest_id": move.location_dest_id.id,
                            "lot_id": quant.lot_id.id,
                            "quantity": remaining_qty,
                            "picked": True,
                        })
        else:
            if move.move_line_ids:
                move.move_line_ids[0].write({"quantity": target_qty, "picked": True})
                if len(move.move_line_ids) > 1:
                    move.move_line_ids[1:].unlink()
            else:
                move.write({"quantity": target_qty, "picked": True})

        if "picked" in move._fields:
            move.write({"picked": True})


    @staticmethod
    def _console_fill_finished_moves(mo, target_finished_qty=None):
        for move in mo.move_finished_ids:
            if move.state in ("done", "cancel"):
                continue
            if target_finished_qty is not None and move.product_id == mo.product_id:
                target_qty = target_finished_qty
            else:
                target_qty = move.product_uom_qty
            MrpProduction._console_set_move_done_quantity(move, target_qty)


    def _console_validate_before_apply(self):
        for mo in self:
            if mo.state not in ("confirmed", "progress", "to_close"):
                raise UserError(
                    _(
                        "You can only apply console quantities for manufacturing orders "
                        "in Confirmed, In Progress or To Close state."
                    )
                )
            mo._check_console_finished_lot()

    @staticmethod
    def _console_close_workorders(workorders, timestamp):
        for wo in workorders:
            if wo.state in ("cancel",):
                continue

            vals = {
                "qty_produced": wo.console_qty,
                "state": "done",
                "date_finished": timestamp,
                "costs_hour": wo.workcenter_id.costs_hour,
            }
            if not wo.date_start:
                vals["date_start"] = timestamp

            wo.with_context(bypass_duration_calculation=True).write(vals)
            wo.end_all()
            if hasattr(wo, "_on_finish_calculate_mold_shots"):
                try:
                    wo._on_finish_calculate_mold_shots()
                except Exception:
                    _logger.exception(
                        "Failed to update mold shots from parallel console for workorder %s",
                        wo.id,
                    )

    def _check_console_finished_lot(self):
        for mo in self:
            if mo.product_tracking not in ("lot", "serial"):
                continue

            if mo.lot_producing_id:
                continue

            # Try to auto-fill from workorders finished lots (Set Qty / WO form).
            finished_lot = mo.workorder_ids.filtered(lambda w: w.finished_lot_id)[
                :1
            ].finished_lot_id
            if finished_lot:
                mo.lot_producing_id = finished_lot
                continue

            raise UserError(
                _(
                    "Manufacturing order %s requires a finished lot/serial number before closing. "
                    "Use Set Qty or the workorder form to assign one."
                )
                % mo.display_name
            )

    def button_mark_done(self):
        for mo in self:
            if mo.lot_producing_id:
                fin_moves = mo.move_finished_ids.filtered(
                    lambda m: m.product_id == mo.product_id and m.state not in ('done', 'cancel')
                )
                for move in fin_moves:
                    if not move.move_line_ids:
                        move.env['stock.move.line'].create({
                            'move_id': move.id,
                            'product_id': move.product_id.id,
                            'product_uom_id': move.product_uom.id,
                            'location_id': move.location_id.id,
                            'location_dest_id': move.location_dest_id.id,
                            'lot_id': mo.lot_producing_id.id,
                            'quantity': mo.qty_producing,
                            'picked': True,
                        })
                    else:
                        for ml in move.move_line_ids:
                            vals = {}
                            if not ml.lot_id:
                                vals['lot_id'] = mo.lot_producing_id.id
                            if not ml.picked:
                                vals['picked'] = True
                            if vals:
                                ml.write(vals)

        res = super(MrpProduction, self).button_mark_done()
        for mo in self:
            if mo.state == "done":
                mo._mpc_validate_fg_scraps()
        return res

    def _mpc_validate_fg_scraps(self):
        """Identify draft FG scraps for this production, correct their location, and validate."""
        self.ensure_one()
        summary = {"validated": 0, "skipped": []}

        finished_move = self.move_finished_ids.filtered(
            lambda move_rec: move_rec.product_id == self.product_id and move_rec.state == "done"
        )[:1]

        final_location = False
        if finished_move:
            final_lines = finished_move.move_line_ids.filtered(
                lambda line: line.state == "done" and line.location_dest_id
            )
            if final_lines:
                final_location = final_lines[-1].location_dest_id

        if not final_location:
            final_location = self.location_dest_id

        if not final_location:
            return summary

        draft_fg_scraps = self.scrap_ids.filtered(
            lambda s: s.product_id == self.product_id and s.state == "draft"
        )

        for scrap in draft_fg_scraps:
            try:
                if scrap.location_id != final_location:
                    scrap.sudo().write({"location_id": final_location.id})

                res = scrap.sudo().action_validate()
                if scrap.state == "done":
                    summary["validated"] += 1
                else:
                    reason = "Resulting state: %s" % scrap.state
                    if (
                        isinstance(res, dict)
                        and res.get("type") == "ir.actions.act_window"
                    ):
                        reason = "Validation wizard triggered (Insufficient stock?)"
                    summary["skipped"].append({"id": scrap.id, "reason": reason})
            except Exception as exc:
                summary["skipped"].append({"id": scrap.id, "reason": str(exc)})

        if summary["validated"] or summary["skipped"]:
            msg = (
                _("MPC Auto-Validation: %s FG scraps validated.") % summary["validated"]
            )
            if summary["skipped"]:
                msg += _(" %s skipped.") % len(summary["skipped"])
            self.message_post(body=msg)

        return summary
