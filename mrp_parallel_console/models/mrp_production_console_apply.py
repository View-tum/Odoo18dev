# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare
from odoo.tools.safe_eval import safe_eval


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    workorder_count = fields.Integer(
        string="Workorder Count",
        compute="_compute_workorder_count",
        store=False,
    )

    def _compute_workorder_count(self):
        for mo in self:
            mo.workorder_count = len(mo.workorder_ids)

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
        workorders = workorders.filtered(lambda w: w.production_id in self)
        if not workorders:
            return False

        action = False
        for mo in self:
            wo_mo = workorders.filtered(lambda w, mo=mo: w.production_id == mo)
            if not wo_mo:
                continue

            mo._console_validate_before_apply()

            total_console_qty = mo._console_compute_total_qty(wo_mo)

            # 1) update qty_producing for internal MRP logic
            mo.qty_producing = total_console_qty

            # Ensure raw/component moves and finished moves carry the
            # necessary quantity_done values, otherwise button_mark_done
            # opens the Consumption Warning wizard and breaks the flow.
            mo._console_fill_move_quantities_for_close(
                finished_qty_map={mo.id: total_console_qty}
            )

            # 2) close each selected workorder with console_qty
            now = fields.Datetime.now()
            self._console_close_workorders(wo_mo, now)

            # 3) run standard logic (may return wizards)
            ctx = dict(self.env.context or {})
            ctx.pop("skip_backorder", None)
            ctx.pop("mo_ids_to_backorder", None)

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

    def _console_compute_total_qty(self, workorders):
        """Compute MO qty from console entries based on operation topology."""
        self.ensure_one()
        if not workorders:
            return 0.0

        qty_by_operation = {}
        for wo in workorders:
            op = wo.operation_id
            if not op:
                continue
            qty_by_operation.setdefault(op, [])
            qty_by_operation[op].append(wo.console_qty or 0.0)

        op_totals = []
        rounding = self.product_uom_id.rounding or 0.0001
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
        """Auto-fill stock move done quantities before closing the MO.

        When closing directly from the parallel console we do not run the
        manual consumption wizard, so stock moves may keep quantity_done=0
        and trigger the Consumption Warning dialog. This helper mirrors the
        manual close behavior by ensuring raw components consume their
        required quantities and the finished product move matches the
        console-reported quantity.
        """
        finished_qty_map = finished_qty_map or {}
        for mo in self:
            self._console_fill_component_moves(mo)
            target_finished_qty = finished_qty_map.get(mo.id)
            self._console_fill_finished_moves(mo, target_finished_qty)

    @staticmethod
    def _console_fill_component_moves(mo):
        for move in mo.move_raw_ids:
            MrpProduction._console_set_move_done_quantity(move, move.product_uom_qty)

    @staticmethod
    def _console_fill_finished_moves(mo, target_finished_qty=None):
        for move in mo.move_finished_ids:
            if target_finished_qty is not None and move.product_id == mo.product_id:
                target_qty = target_finished_qty
            else:
                target_qty = move.product_uom_qty
            MrpProduction._console_set_move_done_quantity(move, target_qty)

    @staticmethod
    def _console_set_move_done_quantity(move, target_qty):
        if not target_qty:
            return

        # Ensure target_qty respects product UoM rounding
        if move.product_uom:
            from odoo.tools import float_round

            target_qty = float_round(
                target_qty, precision_rounding=move.product_uom.rounding or 0.0001
            )

        # 1. พยายามจองของอัตโนมัติ (Reserve)
        if move.product_id.tracking in ("lot", "serial") and not move.move_line_ids:
            try:
                move._action_assign()
            except Exception:
                pass

        # 2. เติม lot แบบ best-effort (ให้ FG ไม่ติด แต่คุม stock component)
        if move.product_id.tracking in ("lot", "serial") and not move.move_line_ids:
            is_finished_move = bool(
                move.production_id and move.product_id == move.production_id.product_id
            )
            lot_id = False

            # หาจาก location ต้นทางก่อน
            quant = move.env["stock.quant"].search(
                [
                    ("product_id", "=", move.product_id.id),
                    ("location_id", "child_of", move.location_id.id),
                    ("quantity", ">=", 0),
                    ("lot_id", "!=", False),
                ],
                limit=1,
                order="in_date, id",
            )

            # สำหรับ FG ลองดูปลายทางด้วย (สต็อกจริงอยู่ปลายทาง)
            if not quant and is_finished_move and move.location_dest_id:
                quant = move.env["stock.quant"].search(
                    [
                        ("product_id", "=", move.product_id.id),
                        ("location_id", "child_of", move.location_dest_id.id),
                        ("quantity", ">=", 0),
                        ("lot_id", "!=", False),
                    ],
                    limit=1,
                    order="in_date, id",
                )

            if quant:
                lot_id = quant.lot_id.id
                if not is_finished_move:
                    available_qty = quant.quantity
                    rounding = move.product_uom.rounding or 0.0001
                    if (
                        float_compare(
                            available_qty, target_qty, precision_rounding=rounding
                        )
                        < 0
                    ):
                        raise UserError(
                            _(
                                "Not enough stock for %(product)s in %(location)s (needed %(needed).2f, available %(available).2f)."
                            )
                            % {
                                "product": move.product_id.display_name,
                                "location": quant.location_id.display_name,
                                "needed": target_qty,
                                "available": available_qty,
                            }
                        )
            elif is_finished_move:
                lot_id = (
                    move.production_id.lot_producing_id.id
                    if move.production_id.lot_producing_id
                    else False
                )
                if not lot_id:
                    finished_lot = move.production_id.workorder_ids.filtered(
                        "finished_lot_id"
                    )[:1].finished_lot_id
                    lot_id = finished_lot.id if finished_lot else False
            else:
                raise UserError(
                    _(
                        "No available lot/serial found for %s in location %s. Please reserve stock before closing."
                    )
                    % (move.product_id.display_name, move.location_id.display_name)
                )

            if lot_id:
                move.env["stock.move.line"].create(
                    {
                        "move_id": move.id,
                        "product_id": move.product_id.id,
                        "product_uom_id": move.product_uom.id,
                        "location_id": move.location_id.id,
                        "location_dest_id": move.location_dest_id.id,
                        "lot_id": lot_id,
                        "quantity": target_qty,
                    }
                )
                return

        if move.move_line_ids:
            qty_to_fill = target_qty
            last_line = False
            for line in move.move_line_ids:
                if qty_to_fill <= 0:
                    break

                last_line = line

                reserved = 0.0
                if "quantity_product_uom" in line._fields:
                    reserved = line.quantity_product_uom
                elif "product_uom_qty" in line._fields:
                    reserved = line.product_uom_qty

                fill = min(reserved, qty_to_fill) if reserved > 0 else qty_to_fill

                if "quantity" in line._fields:
                    line.quantity = fill
                else:
                    line.qty_done = fill

                qty_to_fill -= fill

            if qty_to_fill > 0 and last_line:
                if "quantity" in last_line._fields:
                    last_line.quantity += qty_to_fill
                else:
                    last_line.qty_done += qty_to_fill
            return

        field_name = "quantity_done" if "quantity_done" in move._fields else "quantity"
        current_qty = getattr(move, field_name) or 0.0
        rounding = getattr(move.product_uom, "rounding", 0.0) or 0.0001

        if float_compare(current_qty, target_qty, precision_rounding=rounding) < 0:
            setattr(move, field_name, target_qty)

    @staticmethod
    def _console_prepare_tracked_move(move, target_qty):
        if move.move_line_ids:
            return False

        try:
            move._action_assign()
        except Exception:
            pass

        if move.move_line_ids:
            return False

        quant = move.env["stock.quant"].search(
            [
                ("product_id", "=", move.product_id.id),
                ("location_id", "child_of", move.location_id.id),
                ("quantity", ">", 0),
                ("lot_id", "!=", False),
            ],
            limit=1,
            order="in_date, id",
        )
        lot = quant.lot_id if quant else False

        if not lot:
            lot = move.env["stock.lot"].search(
                [
                    ("product_id", "=", move.product_id.id),
                    ("company_id", "=", move.company_id.id),
                ],
                limit=1,
                order="id desc",
            )

        if not lot:
            return False

        move.env["stock.move.line"].create(
            {
                "move_id": move.id,
                "product_id": move.product_id.id,
                "product_uom_id": move.product_uom.id,
                "location_id": move.location_id.id,
                "location_dest_id": move.location_dest_id.id,
                "lot_id": lot.id,
                "quantity": target_qty,
            }
        )
        return True

    @staticmethod
    def _console_fill_move_lines(move, target_qty):
        qty_to_fill = target_qty
        for line in move.move_line_ids:
            if qty_to_fill <= 0:
                break
            reserved = (
                line.quantity_product_uom
                if "quantity_product_uom" in line._fields
                else line.product_uom_qty
            )
            fill = min(reserved, qty_to_fill) if reserved > 0 else qty_to_fill
            line.quantity = fill
            qty_to_fill -= fill

    @staticmethod
    def _console_set_move_quantity_field(move, target_qty):
        field_name = "quantity_done" if "quantity_done" in move._fields else "quantity"
        current_qty = getattr(move, field_name) or 0.0
        rounding = getattr(move.product_uom, "rounding", 0.0) or 0.0001
        if float_compare(current_qty, target_qty, precision_rounding=rounding) < 0:
            setattr(move, field_name, target_qty)

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
            lambda m: m.product_id == self.product_id and m.state == "done"
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
