from __future__ import annotations

import json
import traceback
from datetime import datetime, timedelta
from pathlib import Path


RUN_TAG = datetime.now().strftime("%Y%m%d%H%M%S")
REPORT_NAME = f"db11_live_fullflow_{RUN_TAG}.json"

PROMO_PRODUCT = "FG-PSS-TH-01002"
PROMO_FREE_PRODUCT = "FG-PSS-TH-01001"
FOC_PRODUCT = "FG-PNC-XX-01001"
MTO_PRODUCT = "FG-MTK-IL-01001"
MTS_PRODUCT = "FG-PNC-TH-01001"
MTS_INCREMENT_QTY = 250.0

SHOPFLOOR_PRODUCT = "SM-JOI-PK-01001"
SHOPFLOOR_MACHINE_ID = 565
SHOPFLOOR_MOLD_ID = 589
SHOPFLOOR_QTY = 12.0
SHOPFLOOR_GOOD_QTY = 11.0
SHOPFLOOR_SCRAP_QTY = 1.0
SHOPFLOOR_CYCLE_TIME = 30.0
SHOPFLOOR_MOLD_COST_HOUR = 60.0
SHOPFLOOR_MOLD_LIFE_LIMIT = 1000
SHOPFLOOR_LABOR_MINUTES = 30.0


def _root_dir() -> Path:
    script_file = globals().get("__file__")
    if script_file:
        return Path(script_file).resolve().parents[3]
    return Path.cwd()


def _report_path() -> Path:
    path = _root_dir() / "reports" / REPORT_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _round(value, digits=4):
    return round(float(value or 0.0), digits)


def _partner_defaults(env):
    vals = {}
    if "approval_state" in env["res.partner"]._fields:
        vals["approval_state"] = "approved"
    return vals


def _get_sale_defaults(env):
    order = env["sale.order"].search(
        [("warehouse_id.name", "ilike", "GMP"), ("partner_id", "!=", False)],
        order="id desc",
        limit=1,
    )
    if not order:
        order = env["sale.order"].search(
            [("warehouse_id", "!=", False), ("partner_id", "!=", False)],
            order="id desc",
            limit=1,
        )
    if not order:
        raise ValueError("No existing sale order found for defaults.")
    vals = {
        "warehouse_id": order.warehouse_id.id,
        "team_id": order.team_id.id or False,
        "pricelist_id": order.pricelist_id.id or False,
        "payment_term_id": order.payment_term_id.id or False,
    }
    if "so_type_id" in order._fields and order.so_type_id:
        vals["so_type_id"] = order.so_type_id.id
    return vals


def _make_customer(env, name, eligible=False):
    vals = {"name": name, "customer_rank": 1}
    vals.update(_partner_defaults(env))
    if "free_item_promo_eligible" in env["res.partner"]._fields:
        vals["free_item_promo_eligible"] = eligible
    return env["res.partner"].create(vals)


def _get_product(env, code):
    product = env["product.product"].search([("default_code", "=", code)], limit=1)
    if not product:
        raise ValueError(f"Product {code} not found.")
    return product


def _get_bom(env, product):
    return env["mrp.bom"]._bom_find(product)[product]


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
    kwargs = {}
    if lot:
        kwargs["lot_id"] = lot
    env["stock.quant"]._update_available_quantity(product, location, qty, **kwargs)


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


def _complete_mos(env, mos, product_lots, label_prefix, picking_before=False):
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
            if picking_before is not False:
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
            if picking_before is not False:
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


def _serialize_order(order):
    return {
        "name": order.name,
        "state": order.state,
        "invoice_status": order.invoice_status,
        "amount_total": _round(order.amount_total),
        "pickings": [p.name for p in order.picking_ids],
        "invoices": [m.name for m in order.invoice_ids],
    }


def _serialize_invoice(invoice):
    if not invoice:
        return {}
    return {
        "name": invoice.name,
        "state": invoice.state,
        "amount_total": _round(invoice.amount_total),
        "invoice_date": str(invoice.invoice_date or ""),
        "lines": [
            {
                "product": line.product_id.default_code,
                "price_unit": _round(line.price_unit),
                "quantity": _round(line.quantity),
                "is_foc": bool(getattr(line, "is_foc", False)),
                "foc_price_unit": _round(getattr(line, "foc_price_unit", 0.0)),
            }
            for line in invoice.invoice_line_ids
        ],
    }


def _mo_cost_snapshot(mo, standard_before=False):
    finished_moves = mo.move_finished_ids.filtered(
        lambda move: move.product_id == mo.product_id and move.state == "done"
    )
    finished_qty = sum(finished_moves.mapped("quantity")) or sum(
        finished_moves.mapped("product_uom_qty")
    ) or mo.product_qty
    finished_value = sum(
        finished_moves.mapped("stock_valuation_layer_ids").mapped("value")
    )
    raw_cost = -sum(
        mo.move_raw_ids.filtered(lambda move: move.state == "done")
        .mapped("stock_valuation_layer_ids")
        .mapped("value")
    )
    labor_svl = mo.env["stock.valuation.layer"]
    mold_svl = mo.env["stock.valuation.layer"]
    if mo.labor_move_id:
        labor_svl = mo.env["stock.valuation.layer"].search(
            [("account_move_id", "=", mo.labor_move_id.id)]
        )
    if mo.mold_move_id:
        mold_svl = mo.env["stock.valuation.layer"].search(
            [("account_move_id", "=", mo.mold_move_id.id)]
        )
    labor_cost = sum(labor_svl.mapped("value"))
    mold_cost = sum(mold_svl.mapped("value"))
    calculated_total = raw_cost + labor_cost + mold_cost
    variance = finished_value - calculated_total
    account_moves = (
        mo.move_raw_ids.mapped("account_move_ids")
        | finished_moves.mapped("account_move_ids")
        | mo.labor_move_id
        | mo.mold_move_id
    )
    return {
        "mo_name": mo.name,
        "product_code": mo.product_id.default_code,
        "state": mo.state,
        "product_qty": _round(mo.product_qty),
        "finished_qty": _round(finished_qty),
        "cost_method": mo.product_id.categ_id.property_cost_method,
        "valuation": mo.product_id.categ_id.property_valuation,
        "standard_price_before": _round(standard_before if standard_before is not False else mo.product_id.standard_price),
        "standard_price_after": _round(mo.product_id.standard_price),
        "raw_cost_total": _round(raw_cost),
        "labor_cost_total": _round(labor_cost),
        "mold_cost_total": _round(mold_cost),
        "employee_cost_total": _round(getattr(mo, "employee_cost_total", 0.0)),
        "mold_cost_field_total": _round(getattr(mo, "mold_cost_total", 0.0)),
        "finished_value_total": _round(finished_value),
        "actual_unit_cost": _round(finished_value / finished_qty if finished_qty else 0.0),
        "calculated_total_cost": _round(calculated_total),
        "valuation_variance": _round(variance),
        "valuation_logic_ok": abs(variance) <= 0.05,
        "journal_entries": account_moves.sorted("id").mapped("name"),
        "labor_move": mo.labor_move_id.name if mo.labor_move_id else False,
        "mold_move": mo.mold_move_id.name if mo.mold_move_id else False,
    }


def _collect_cogs_lines(invoice):
    if not invoice:
        return invoice.env["account.move.line"] if hasattr(invoice, "env") else []
    return invoice.line_ids.filtered(lambda line: line.display_type == "cogs")


def _run_promo_case(env):
    product = _get_product(env, PROMO_PRODUCT)
    partner = _make_customer(env, f"CODEX PROMO {RUN_TAG}", eligible=True)
    defaults = _get_sale_defaults(env)
    order_vals = {
        "partner_id": partner.id,
        "date_order": datetime.now(),
        "warehouse_id": defaults["warehouse_id"],
        "team_id": defaults["team_id"],
        "pricelist_id": defaults["pricelist_id"],
        "payment_term_id": defaults["payment_term_id"],
        "client_order_ref": f"CODEX-PROMO-{RUN_TAG}",
        "order_line": [(0, 0, {"product_id": product.id, "product_uom_qty": 1})],
    }
    if defaults.get("so_type_id"):
        order_vals["so_type_id"] = defaults["so_type_id"]
    order = env["sale.order"].create(order_vals)
    free_lines = order.order_line.filtered("is_free_item")
    return {
        "case": "promo_quote_creation",
        "pass": bool(
            free_lines
            and free_lines[0].product_id.default_code == PROMO_FREE_PRODUCT
            and _round(free_lines[0].product_uom_qty) == 4.0
        ),
        "order": _serialize_order(order),
        "lines": [
            {
                "product": line.product_id.default_code,
                "qty": _round(line.product_uom_qty),
                "price_unit": _round(line.price_unit),
                "is_free_item": bool(getattr(line, "is_free_item", False)),
            }
            for line in order.order_line
        ],
        "notes": [
            "Promo was verified with a real quotation on DB 11.",
            "This case validates the automatic free-item line only.",
        ],
    }


def _run_sales_flow_case(env, label, product_code, is_foc=False):
    product = _get_product(env, product_code)
    defaults = _get_sale_defaults(env)
    partner = _make_customer(env, f"CODEX {label} {RUN_TAG}", eligible=False)
    mo_before = env["mrp.production"].search([], order="id desc", limit=1).id or 0
    picking_before = env["stock.picking"].search([], order="id desc", limit=1).id or 0
    invoice_before = (
        env["account.move"]
        .search([("move_type", "=", "out_invoice")], order="id desc", limit=1)
        .id
        or 0
    )
    standard_before = _round(product.standard_price)
    line_vals = {
        "product_id": product.id,
        "product_uom_qty": 1,
    }
    if is_foc:
        line_vals.update(
            {
                "is_foc": True,
                "price_unit": 0.0,
                "foc_price_unit": product.lst_price or 0.0,
            }
        )
    order_vals = {
        "partner_id": partner.id,
        "date_order": datetime.now(),
        "warehouse_id": defaults["warehouse_id"],
        "team_id": defaults["team_id"],
        "pricelist_id": defaults["pricelist_id"],
        "payment_term_id": defaults["payment_term_id"],
        "client_order_ref": f"CODEX-{label}-{RUN_TAG}",
        "order_line": [(0, 0, line_vals)],
    }
    if defaults.get("so_type_id"):
        order_vals["so_type_id"] = defaults["so_type_id"]
    order = env["sale.order"].create(order_vals)
    order_name = order.name
    try:
        order.action_confirm()
    except Exception as exc:
        env.cr.rollback()
        return {
            "case": label,
            "pass": False,
            "stage": "action_confirm",
            "order_name": order_name,
            "product_code": product_code,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }

    mos_after_confirm = env["mrp.production"].search([("id", ">", mo_before)], order="id")
    pickings_after_confirm = env["stock.picking"].search([("id", ">", picking_before)], order="id")
    product_lots = {}
    completed_mos = _complete_mos(
        env, mos_after_confirm, product_lots, label, picking_before=picking_before
    )
    all_pickings = _process_pending_pickings(env, picking_before, product_lots, label)

    order.invalidate_recordset()
    auto_invoices = env["account.move"].search(
        [("id", ">", invoice_before), ("move_type", "=", "out_invoice")],
        order="id",
    )
    invoice = (
        order.invoice_ids.sorted("id")[-1]
        if order.invoice_ids
        else (auto_invoices.sorted("id")[-1] if auto_invoices else env["account.move"])
    )
    done_pickings = order.picking_ids.filtered(lambda picking: picking.state == "done")
    cogs_lines = _collect_cogs_lines(invoice)
    foc_account = env.company.foc_cogs_adjust_account_id
    foc_account_used = bool(
        foc_account and foc_account.id in cogs_lines.mapped("account_id").ids
    )
    costing = [_mo_cost_snapshot(mo, standard_before=standard_before) for mo in mos_after_confirm]
    return {
        "case": label,
        "pass": bool(mos_after_confirm) and bool(done_pickings) and bool(invoice and invoice.state == "posted"),
        "order": _serialize_order(order),
        "invoice": _serialize_invoice(invoice),
        "mo_names_after_confirm": mos_after_confirm.mapped("name"),
        "completed_mos": completed_mos,
        "pickings_after_confirm": [
            {"name": p.name, "type": p.picking_type_id.code, "state": p.state}
            for p in pickings_after_confirm
        ],
        "pickings_after_processing": [
            {"name": p.name, "type": p.picking_type_id.code, "state": p.state}
            for p in all_pickings
        ],
        "done_pickings": [p.name for p in done_pickings],
        "sale_line_delivery": [
            {
                "product": line.product_id.default_code,
                "qty_ordered": _round(line.product_uom_qty),
                "qty_delivered": _round(line.qty_delivered),
                "qty_invoiced": _round(line.qty_invoiced),
                "is_foc": bool(getattr(line, "is_foc", False)),
            }
            for line in order.order_line
        ],
        "cogs_accounts": [line.account_id.code for line in cogs_lines],
        "foc_expected_account": foc_account.code if foc_account else False,
        "foc_expected_account_used": foc_account_used,
        "costing": costing,
        "notes": [
            "Invoice must be auto-created and auto-posted after delivery.",
            "Costing is reported from the real MOs created by the sales flow.",
        ],
    }


def _run_mts_live_case(env):
    product = _get_product(env, MTS_PRODUCT)
    orderpoint = env["stock.warehouse.orderpoint"].search(
        [("product_id", "=", product.id), ("location_id.complete_name", "=", "GMP/Stock")],
        order="id desc",
        limit=1,
    )
    if not orderpoint:
        raise ValueError(f"No GMP orderpoint found for {MTS_PRODUCT}.")
    product_ctx = product.with_context(
        company_id=orderpoint.company_id.id, location=orderpoint.location_id.id
    )
    qty_on_hand_before = float(product_ctx.qty_available)
    qty_forecast_before = float(product_ctx.virtual_available)
    target_level = max(qty_forecast_before, 0.0) + MTS_INCREMENT_QTY
    original_rule = {
        "product_min_qty": float(orderpoint.product_min_qty),
        "product_max_qty": float(orderpoint.product_max_qty),
        "qty_multiple": float(orderpoint.qty_multiple),
        "trigger": orderpoint.trigger,
    }
    mo_before = env["mrp.production"].search([], order="id desc", limit=1).id or 0
    picking_before = env["stock.picking"].search([], order="id desc", limit=1).id or 0
    standard_before = _round(product.standard_price)
    orderpoint.write(
        {
            "product_min_qty": target_level,
            "product_max_qty": target_level,
            "qty_multiple": 1.0,
            "trigger": "auto",
        }
    )
    try:
        orderpoint.action_replenish(force_to_max=True)
        mos_after_replenish = env["mrp.production"].search([("id", ">", mo_before)], order="id")
        product_lots = {}
        completed_mos = _complete_mos(
            env, mos_after_replenish, product_lots, "MTSLIVE", picking_before=picking_before
        )
        all_pickings = _process_pending_pickings(
            env, picking_before, product_lots, "MTSLIVE"
        )
        product_ctx = product.with_context(
            company_id=orderpoint.company_id.id, location=orderpoint.location_id.id
        )
        qty_on_hand_after = float(product_ctx.qty_available)
        qty_forecast_after = float(product_ctx.virtual_available)
        result = {
            "case": "mts_min_max_live",
            "pass": bool(mos_after_replenish) and qty_on_hand_after > qty_on_hand_before,
            "orderpoint_id": orderpoint.id,
            "original_rule": original_rule,
            "replenish_target_level": _round(target_level),
            "qty_on_hand_before": _round(qty_on_hand_before),
            "qty_forecast_before": _round(qty_forecast_before),
            "qty_on_hand_after": _round(qty_on_hand_after),
            "qty_forecast_after": _round(qty_forecast_after),
            "mo_names_after_replenish": mos_after_replenish.mapped("name"),
            "completed_mos": completed_mos,
            "pickings_after_run": [
                {"name": p.name, "type": p.picking_type_id.code, "state": p.state}
                for p in all_pickings
            ],
            "costing": [
                _mo_cost_snapshot(mo, standard_before=standard_before)
                for mo in mos_after_replenish
            ],
        }
    finally:
        orderpoint.write(original_rule)
    return result


def _run_existing_100k_trace(env):
    product = _get_product(env, MTS_PRODUCT)
    mo = env["mrp.production"].search(
        [
            ("product_id", "=", product.id),
            ("state", "=", "done"),
            ("product_qty", "=", 100000.0),
        ],
        order="id desc",
        limit=1,
    )
    return {
        "case": "mts_100000_existing_trace",
        "pass": bool(mo),
        "found_mo": mo.name if mo else False,
        "costing": [_mo_cost_snapshot(mo)] if mo else [],
        "notes": [
            "This case traces the existing real 100000-qty production already executed on DB 11.",
        ],
    }


def _ensure_mold_mapping(env, product):
    machine = env["mrp.workcenter"].browse(SHOPFLOOR_MACHINE_ID)
    mold = env["mrp.workcenter"].browse(SHOPFLOOR_MOLD_ID)
    if not machine or not mold:
        raise ValueError("Required machine or mold for the shopfloor mold test was not found.")
    if mold.id not in machine.allowed_mold_ids.ids:
        machine.write({"allowed_mold_ids": [(4, mold.id)]})
    line = env["mrp.mold.product.line"].search(
        [("mold_id", "=", mold.id), ("product_id", "=", product.id)],
        limit=1,
    )
    if not line:
        line = env["mrp.mold.product.line"].create(
            {
                "mold_id": mold.id,
                "product_id": product.id,
                "cycle_time": SHOPFLOOR_CYCLE_TIME,
            }
        )
    elif not line.cycle_time:
        line.cycle_time = SHOPFLOOR_CYCLE_TIME
    mold_updates = {}
    if mold.mold_cost_hour <= 0:
        mold_updates["mold_cost_hour"] = SHOPFLOOR_MOLD_COST_HOUR
    if mold.mold_life_limit <= 0:
        mold_updates["mold_life_limit"] = SHOPFLOOR_MOLD_LIFE_LIMIT
    if mold_updates:
        mold.write(mold_updates)
    matrix_line = env["mrp.mold.matrix.report"].search(
        [
            ("machine_id", "=", machine.id),
            ("mold_id", "=", mold.id),
            ("product_id", "=", product.id),
        ],
        limit=1,
    )
    return {
        "machine_id": machine.id,
        "machine_name": machine.name,
        "mold_id": mold.id,
        "mold_name": mold.name,
        "matrix_line_id": matrix_line.id if matrix_line else False,
        "cycle_time": _round(line.cycle_time),
        "units_per_hour": _round(line.units_per_hour),
        "mold_cost_hour": _round(mold.mold_cost_hour),
        "mold_life_limit": mold.mold_life_limit,
        "mold_life_current_before": mold.mold_life_current,
    }


def _run_shopfloor_mold_case(env):
    product = _get_product(env, SHOPFLOOR_PRODUCT)
    bom = _get_bom(env, product)
    if not bom:
        raise ValueError(f"No BoM found for {SHOPFLOOR_PRODUCT}.")
    employee = env["hr.employee"].search(
        [("company_id", "in", [env.company.id, False])], order="id", limit=1
    )
    if not employee:
        raise ValueError("No employee found for the shopfloor timer test.")
    mold_setup = _ensure_mold_mapping(env, product)
    picking_before = env["stock.picking"].search([], order="id desc", limit=1).id or 0
    standard_before = _round(product.standard_price)
    picking_type = bom.picking_type_id or env["stock.picking.type"].search(
        [("name", "=", "Manufacturing Plastic")],
        limit=1,
    )
    if not picking_type:
        raise ValueError("No Manufacturing Plastic operation type found.")
    mo = env["mrp.production"].create(
        {
            "product_id": product.id,
            "product_qty": SHOPFLOOR_QTY,
            "product_uom_id": product.uom_id.id,
            "bom_id": bom.id,
            "origin": f"CODEX-SHOPFLOOR-MOLD-{RUN_TAG}",
            "picking_type_id": picking_type.id,
            "location_src_id": picking_type.default_location_src_id.id,
            "location_dest_id": picking_type.default_location_dest_id.id,
        }
    )
    mo.action_confirm()
    mo.action_assign()
    fg_lot = _make_lot(env, product, "SHOPMOLD-FG")
    if fg_lot and "lot_producing_id" in mo._fields:
        mo.lot_producing_id = fg_lot.id
    product_lots = {}
    if fg_lot:
        product_lots[product.id] = fg_lot

    for move in mo.move_raw_ids.filtered(lambda move: move.state not in ("done", "cancel")):
        qty = move.product_uom_qty or getattr(move, "quantity", 0.0) or 0.0
        lot = product_lots.get(move.product_id.id)
        if move.product_id.tracking in ("lot", "serial") and not lot:
            lot = _make_lot(env, move.product_id, "SHOPMOLD-RM")
            product_lots[move.product_id.id] = lot
        _put_stock(env, move.product_id, move.location_id, qty, lot=lot)
        _pin_move(move, qty, lot=lot)

    workorders = mo.workorder_ids
    for workorder in workorders:
        workorder.action_console_set_employees([employee.id])
        workorder.action_console_start_timer()
        open_lines = env["mrp.workcenter.productivity"].search(
            [("workorder_id", "=", workorder.id), ("date_end", "=", False)]
        )
        backdated_start = datetime.now() - timedelta(minutes=SHOPFLOOR_LABOR_MINUTES)
        open_lines.write({"date_start": backdated_start})
        workorder.write({"console_qty": SHOPFLOOR_GOOD_QTY})
        env["mrp.workorder.qty.log"].create(
            {
                "workorder_id": workorder.id,
                "qty": SHOPFLOOR_GOOD_QTY,
                "note": f"CODEX-SHOPFLOOR-{RUN_TAG}",
                "employee_ids": [(6, 0, [employee.id])],
            }
        )
        workorder.action_console_stop_timer()

    scrap_loc = env["stock.location"].search(
        [("scrap_location", "=", True), ("company_id", "in", [mo.company_id.id, False])],
        limit=1,
    )
    if not scrap_loc:
        raise ValueError("No scrap location available for the shopfloor test.")
    scrap_vals = {
        "product_id": product.id,
        "scrap_qty": SHOPFLOOR_SCRAP_QTY,
        "product_uom_id": product.uom_id.id,
        "location_id": mo.location_dest_id.id,
        "scrap_location_id": scrap_loc.id,
        "company_id": mo.company_id.id,
        "production_id": mo.id,
    }
    if fg_lot and "lot_id" in env["stock.scrap"]._fields:
        scrap_vals["lot_id"] = fg_lot.id
    if "workorder_id" in env["stock.scrap"]._fields and workorders:
        scrap_vals["workorder_id"] = workorders[0].id
    scrap = env["stock.scrap"].create(scrap_vals)

    result = mo._console_apply_quantities_and_backorder(workorders)
    if isinstance(result, dict) and result.get("res_model") == "mrp.production.backorder":
        env[result["res_model"]].browse(result["res_id"]).action_close_mo()
    pending_pickings = _process_pending_pickings(
        env, picking_before, product_lots, "SHOPMOLD"
    )
    mold = env["mrp.workcenter"].browse(SHOPFLOOR_MOLD_ID)
    scrap.invalidate_recordset()
    mo.invalidate_recordset()
    workorders.invalidate_recordset()
    return {
        "case": "shopfloor_scrap_mold_live",
        "pass": bool(
            mo.state == "done"
            and scrap.state == "done"
            and mo.employee_cost_total > 0
            and mo.mold_cost_total > 0
            and bool(mo.labor_move_id)
            and bool(mo.mold_move_id)
            and mold.mold_life_current > mold_setup["mold_life_current_before"]
        ),
        "mo_name": mo.name,
        "mold_setup": {
            **mold_setup,
            "mold_life_current_after": mold.mold_life_current,
        },
        "result_action": result if isinstance(result, dict) else False,
        "workorders": [
            {
                "name": wo.name,
                "state": wo.state,
                "console_qty": _round(wo.console_qty),
                "qty_produced": _round(wo.qty_produced),
                "employee_names": wo.employee_ids.mapped("name"),
                "molds": wo.mold_ids.mapped("name"),
                "duration_expected": _round(wo.duration_expected),
                "duration": _round(wo.duration),
                "mold_cost": _round(getattr(wo, "mold_cost", 0.0)),
            }
            for wo in workorders
        ],
        "scrap": {
            "name": scrap.name,
            "state": scrap.state,
            "qty": _round(scrap.scrap_qty),
            "lot": scrap.lot_id.name if getattr(scrap, "lot_id", False) else False,
        },
        "productivity_lines": [
            {
                "employee": line.employee_id.name,
                "date_start": str(line.date_start),
                "date_end": str(line.date_end),
                "hours": _round(
                    (line.date_end - line.date_start).total_seconds() / 3600.0
                    if line.date_start and line.date_end
                    else 0.0
                ),
            }
            for line in env["mrp.workcenter.productivity"].search(
                [("workorder_id", "in", workorders.ids), ("employee_id", "!=", False)],
                order="id",
            )
        ],
        "pickings_after_run": [
            {"name": p.name, "type": p.picking_type_id.code, "state": p.state}
            for p in pending_pickings
        ],
        "costing": [_mo_cost_snapshot(mo, standard_before=standard_before)],
        "notes": [
            "This case uses the parallel shopfloor flow with a real draft FG scrap on DB 11.",
            "An existing mold was mapped to the plastic machine/product before the MO was run.",
        ],
    }


def _run_case(env, case_name, runner):
    try:
        result = runner(env)
        env.cr.commit()
        if hasattr(env, "invalidate_all"):
            env.invalidate_all()
    except Exception as exc:
        env.cr.rollback()
        result = {
            "case": case_name,
            "pass": False,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }
    if not result.get("case"):
        result["case"] = case_name
    return result


def _run():
    cases = [
        ("promo_quote_creation", _run_promo_case),
        ("foc_zero_mto_live", lambda env: _run_sales_flow_case(env, "foc_zero_mto_live", FOC_PRODUCT, is_foc=True)),
        ("mto_standard_live", lambda env: _run_sales_flow_case(env, "mto_standard_live", MTO_PRODUCT, is_foc=False)),
        ("mts_min_max_live", _run_mts_live_case),
        ("mts_100000_existing_trace", _run_existing_100k_trace),
        ("shopfloor_scrap_mold_live", _run_shopfloor_mold_case),
    ]
    results = []
    for case_name, runner in cases:
        results.append(_run_case(env, case_name, runner))
    summary = {
        "database": env.cr.dbname,
        "run_tag": RUN_TAG,
        "run_at": datetime.now().isoformat(),
        "passed_cases": [res["case"] for res in results if res.get("pass")],
        "failed_cases": [res["case"] for res in results if not res.get("pass")],
        "cases": results,
    }
    report = _report_path()
    report.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    print(f"REPORT|{report}")
    print(
        json.dumps(
            {
                "passed": summary["passed_cases"],
                "failed": summary["failed_cases"],
            },
            ensure_ascii=True,
        )
    )


_run()
