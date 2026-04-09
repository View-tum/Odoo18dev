from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


PRODUCT_CODE = "FG-PNC-TH-01001"
TARGET_QTY = 100000.0
RUN_TAG = datetime.now().strftime("%Y%m%d%H%M%S")
REPORT_NAME = f"db11_real_mts_replenishment_{RUN_TAG}.json"


def _root_dir() -> Path:
    script_file = globals().get("__file__")
    if script_file:
        return Path(script_file).resolve().parents[3]
    return Path.cwd()


def _report_path() -> Path:
    path = _root_dir() / "reports" / REPORT_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _move_line_qty_field(model):
    if "quantity" in model._fields:
        return "quantity"
    if "qty_done" in model._fields:
        return "qty_done"
    return None


def _make_lot(env, product, prefix):
    if product.tracking not in ("lot", "serial"):
        return False
    return env["stock.lot"].create(
        {
            "name": f"{prefix}-{product.id}-{RUN_TAG}",
            "product_id": product.id,
            "company_id": (product.company_id or env.company).id,
        }
    )


def _put_stock(env, product, location, qty, lot=False):
    quant_model = env["stock.quant"]
    kwargs = {}
    if lot:
        kwargs["lot_id"] = lot
    quant_model._update_available_quantity(product, location, qty, **kwargs)


def _pin_move(move, qty, lot=False):
    move_line_model = move.env["stock.move.line"]
    qty_field = _move_line_qty_field(move_line_model)
    target_location = move.location_id
    if lot:
        quant = move.env["stock.quant"].search(
            [
                ("product_id", "=", move.product_id.id),
                ("lot_id", "=", lot.id),
                ("quantity", ">", 0),
            ],
            order="in_date, id",
            limit=1,
        )
        if quant:
            target_location = quant.location_id
    if move.move_line_ids:
        primary = move.move_line_ids[0]
        vals = {
            "location_id": target_location.id,
            "location_dest_id": move.location_dest_id.id,
        }
        if lot:
            vals["lot_id"] = lot.id
        if qty_field:
            vals[qty_field] = qty
        if "picked" in primary._fields:
            vals["picked"] = True
        primary.write(vals)
        if len(move.move_line_ids) > 1:
            move.move_line_ids[1:].unlink()
    else:
        vals = move._prepare_move_line_vals(quantity=qty, reserved_quant=False)
        vals.update(
            {
                "location_id": target_location.id,
                "location_dest_id": move.location_dest_id.id,
            }
        )
        if lot:
            vals["lot_id"] = lot.id
        if qty_field:
            vals[qty_field] = qty
        if "picked" in move_line_model._fields:
            vals["picked"] = True
        move_line_model.create(vals)
    move_vals = {}
    if "quantity" in move._fields:
        move_vals["quantity"] = qty
    elif "qty_done" in move._fields:
        move_vals["qty_done"] = qty
    if "picked" in move._fields:
        move_vals["picked"] = True
    if move_vals:
        move.write(move_vals)


def _validate_picking(env, picking, product_lots, label_prefix):
    if not picking or picking.state in ("done", "cancel"):
        return
    if picking.state == "draft":
        picking.action_confirm()
    picking.action_assign()
    for move in picking.move_ids.filtered(lambda m: m.state not in ("done", "cancel")):
        qty = move.product_uom_qty or getattr(move, "quantity", 0.0) or 0.0
        lot = product_lots.get(move.product_id.id)
        if move.product_id.tracking in ("lot", "serial") and not lot:
            lot = _make_lot(env, move.product_id, f"{label_prefix}-PK")
            product_lots[move.product_id.id] = lot
        _put_stock(env, move.product_id, move.location_id, qty, lot=lot)
        _pin_move(move, qty, lot=lot)
    result = picking.button_validate()
    if isinstance(result, dict) and result.get("res_model") == "stock.backorder.confirmation":
        env[result["res_model"]].browse(result["res_id"]).process()


def _process_pending_pickings(
    env, picking_before, product_lots, label_prefix, allowed_codes=None
):
    last_snapshot = []
    for _ in range(10):
        pending = env["stock.picking"].search(
            [("id", ">", picking_before), ("state", "not in", ["done", "cancel"])],
            order="id",
        )
        if allowed_codes:
            pending = pending.filtered(
                lambda picking: picking.picking_type_id.code in allowed_codes
            )
        if not pending:
            break
        snapshot = [(p.id, p.state) for p in pending]
        if snapshot == last_snapshot:
            break
        last_snapshot = snapshot
        for picking in pending:
            _validate_picking(env, picking, product_lots, label_prefix)
    return env["stock.picking"].search([("id", ">", picking_before)], order="id")


def _complete_mo(env, mo, product_lots, label_prefix):
    if mo.state == "draft":
        mo.action_confirm()
    if mo.state in ("done", "cancel"):
        return product_lots.get(mo.product_id.id)
    mo.action_assign()
    fg_lot = product_lots.get(mo.product_id.id)
    if mo.product_id.tracking in ("lot", "serial") and not fg_lot:
        fg_lot = _make_lot(env, mo.product_id, f"{label_prefix}-FG")
        product_lots[mo.product_id.id] = fg_lot
    if fg_lot and "lot_producing_id" in mo._fields:
        mo.lot_producing_id = fg_lot.id
    mo.qty_producing = mo.product_qty
    for move in mo.move_raw_ids.filtered(lambda m: m.state not in ("done", "cancel")):
        qty = move.product_uom_qty or getattr(move, "quantity", 0.0) or 0.0
        lot = product_lots.get(move.product_id.id)
        if move.product_id.tracking in ("lot", "serial") and not lot:
            lot = _make_lot(env, move.product_id, f"{label_prefix}-RM")
            product_lots[move.product_id.id] = lot
        _put_stock(env, move.product_id, move.location_id, qty, lot=lot)
        _pin_move(move, qty, lot=lot)
    if hasattr(mo, "_console_fill_move_quantities_for_close"):
        mo._console_fill_move_quantities_for_close({mo.id: mo.product_qty})
    done_at = datetime.now()
    for workorder in mo.workorder_ids:
        duration = workorder.duration_expected or 1.0
        vals = {
            "state": "done",
            "qty_produced": mo.product_qty,
            "date_start": done_at,
            "date_finished": done_at,
            "duration_expected": duration,
            "duration": duration,
            "duration_unit": round(duration / max(mo.product_qty, 1), 4),
        }
        if "costs_hour" in workorder._fields:
            vals["costs_hour"] = workorder.workcenter_id.costs_hour
        workorder.with_context(bypass_duration_calculation=True).write(vals)
        if hasattr(workorder, "end_all"):
            workorder.end_all()
    result = mo.with_context(skip_consumption=True).button_mark_done()
    if isinstance(result, dict) and result.get("res_model") == "mrp.production.backorder":
        env[result["res_model"]].browse(result["res_id"]).action_close_mo()
    return fg_lot


def _complete_mos(env, mos, product_lots, label_prefix, picking_before):
    pending = mos.filtered(lambda m: m.state not in ("done", "cancel"))
    completed = []
    while pending:
        pending_product_ids = set(pending.mapped("product_id").ids)
        progressed = False
        for mo in pending.sorted(lambda m: (m.product_id.id, m.id)):
            deps = set(mo.move_raw_ids.mapped("product_id").ids) & pending_product_ids
            deps.discard(mo.product_id.id)
            if deps:
                continue
            fg_lot = _complete_mo(env, mo, product_lots, label_prefix)
            if fg_lot:
                product_lots[mo.product_id.id] = fg_lot
            _process_pending_pickings(
                env,
                picking_before,
                product_lots,
                label_prefix,
                allowed_codes={"internal"},
            )
            completed.append(mo.name)
            pending -= mo
            progressed = True
        if not progressed:
            mo = pending.sorted("id")[0]
            fg_lot = _complete_mo(env, mo, product_lots, label_prefix)
            if fg_lot:
                product_lots[mo.product_id.id] = fg_lot
            _process_pending_pickings(
                env,
                picking_before,
                product_lots,
                label_prefix,
                allowed_codes={"internal"},
            )
            completed.append(mo.name)
            pending -= mo
    return completed


def _run():
    product = env["product.product"].search([("default_code", "=", PRODUCT_CODE)], limit=1)
    if not product:
        raise ValueError(f"Product {PRODUCT_CODE} not found.")
    orderpoint = env["stock.warehouse.orderpoint"].search(
        [("product_id", "=", product.id), ("location_id.complete_name", "=", "GMP/Stock")],
        order="id desc",
        limit=1,
    )
    if not orderpoint:
        raise ValueError(f"No GMP orderpoint found for {PRODUCT_CODE}.")
    product_ctx = product.with_context(
        company_id=orderpoint.company_id.id, location=orderpoint.location_id.id
    )
    qty_on_hand_before = float(product_ctx.qty_available)
    qty_forecast_before = float(product_ctx.virtual_available)
    target_level = max(qty_forecast_before, 0.0) + TARGET_QTY
    original_rule = {
        "product_min_qty": float(orderpoint.product_min_qty),
        "product_max_qty": float(orderpoint.product_max_qty),
        "qty_multiple": float(orderpoint.qty_multiple),
        "trigger": orderpoint.trigger,
    }
    mo_before = env["mrp.production"].search([], order="id desc", limit=1).id or 0
    picking_before = env["stock.picking"].search([], order="id desc", limit=1).id or 0
    try:
        orderpoint.write(
            {
                "product_min_qty": target_level,
                "product_max_qty": target_level,
                "qty_multiple": 1.0,
                "trigger": "auto",
            }
        )
        orderpoint.action_replenish(force_to_max=True)
        mos_after_replenish = env["mrp.production"].search(
            [("id", ">", mo_before)], order="id"
        )
        product_lots = {}
        completed_mos = _complete_mos(
            env, mos_after_replenish, product_lots, "REALMTS", picking_before
        )
        all_pickings = _process_pending_pickings(
            env, picking_before, product_lots, "REALMTS"
        )
        orderpoint.write(original_rule)
        product_ctx = product.with_context(
            company_id=orderpoint.company_id.id, location=orderpoint.location_id.id
        )
        result = {
            "database": env.cr.dbname,
            "run_tag": RUN_TAG,
            "product_code": PRODUCT_CODE,
            "target_qty": TARGET_QTY,
            "orderpoint_id": orderpoint.id,
            "replenish_target_level": target_level,
            "qty_on_hand_before": qty_on_hand_before,
            "qty_forecast_before": qty_forecast_before,
            "qty_on_hand_after": float(product_ctx.qty_available),
            "qty_forecast_after": float(product_ctx.virtual_available),
            "mo_count_after_replenish": len(mos_after_replenish),
            "mo_names_after_replenish": mos_after_replenish.mapped("name"),
            "completed_mos": completed_mos,
            "pickings_after_run": [
                {
                    "name": picking.name,
                    "type": picking.picking_type_id.code,
                    "state": picking.state,
                }
                for picking in all_pickings
            ],
            "original_rule": original_rule,
            "status": "done",
        }
        env.cr.commit()
    except Exception as exc:
        env.cr.rollback()
        result = {
            "database": env.cr.dbname,
            "run_tag": RUN_TAG,
            "product_code": PRODUCT_CODE,
            "target_qty": TARGET_QTY,
            "status": "failed",
            "error": str(exc),
        }
        raise
    finally:
        report = _report_path()
        report.write_text(
            json.dumps(result, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        print(f"REPORT|{report}")
        print(json.dumps(result, ensure_ascii=True, default=str))


_run()
