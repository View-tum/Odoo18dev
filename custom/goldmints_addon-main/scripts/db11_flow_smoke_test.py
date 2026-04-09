from __future__ import annotations

import json
import traceback
from collections import defaultdict
from datetime import datetime
from pathlib import Path


RUN_TAG = datetime.now().strftime("%Y%m%d%H%M%S")
REPORT_NAME = f"db11_flow_smoke_{RUN_TAG}.json"


def _root_dir() -> Path:
    script_file = globals().get("__file__")
    if script_file:
        return Path(script_file).resolve().parents[3]
    return Path.cwd()


def _report_path() -> Path:
    path = _root_dir() / "reports" / REPORT_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


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
    for _ in range(5):
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


def _collect_moves(invoice):
    return invoice.line_ids.filtered(lambda line: line.display_type == "cogs")


def _serialize_order(order):
    return {
        "name": order.name,
        "state": order.state,
        "invoice_status": order.invoice_status,
        "amount_total": float(order.amount_total),
        "pickings": [p.name for p in order.picking_ids],
        "invoices": [m.name for m in order.invoice_ids],
    }


def _run_promo_case(env):
    product = _get_product(env, "FG-PSS-TH-01002")
    partner = _make_customer(env, f"CODEx PROMO {RUN_TAG}", eligible=True)
    defaults = _get_sale_defaults(env)
    order_vals = {
        "partner_id": partner.id,
        "date_order": datetime.now(),
        "warehouse_id": defaults["warehouse_id"],
        "team_id": defaults["team_id"],
        "pricelist_id": defaults["pricelist_id"],
        "payment_term_id": defaults["payment_term_id"],
        "order_line": [(0, 0, {"product_id": product.id, "product_uom_qty": 1})],
    }
    if defaults.get("so_type_id"):
        order_vals["so_type_id"] = defaults["so_type_id"]
    order = env["sale.order"].create(order_vals)
    free_lines = order.order_line.filtered("is_free_item")
    return {
        "case": "promo_free_item",
        "pass": bool(free_lines and free_lines[0].product_id.default_code == "FG-PSS-TH-01001" and free_lines[0].product_uom_qty == 4),
        "order": _serialize_order(order),
        "base_lines": [
            {
                "product": line.product_id.default_code,
                "qty": float(line.product_uom_qty),
                "price_unit": float(line.price_unit),
                "is_free_item": bool(getattr(line, "is_free_item", False)),
            }
            for line in order.order_line
        ],
        "notes": [
            "Promo logic was tested on quotation creation only.",
            "This product is configured as pharma MTS, not MTO.",
        ],
    }


def _run_sales_flow_case(env, label, product_code, is_foc=False):
    product = _get_product(env, product_code)
    defaults = _get_sale_defaults(env)
    partner = _make_customer(env, f"CODEX {label} {RUN_TAG}", eligible=False)
    mo_before = env["mrp.production"].search([], order="id desc", limit=1).id or 0
    picking_before = env["stock.picking"].search([], order="id desc", limit=1).id or 0
    invoice_before = env["account.move"].search([("move_type", "=", "out_invoice")], order="id desc", limit=1).id or 0
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
    auto_invoice_after_confirm = env["account.move"].search(
        [("id", ">", invoice_before), ("move_type", "=", "out_invoice")],
        order="id",
    )

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
    invoice = order.invoice_ids.sorted("id")[-1] if order.invoice_ids else (
        auto_invoices.sorted("id")[-1] if auto_invoices else env["account.move"]
    )
    done_pickings = order.picking_ids.filtered(lambda p: p.state == "done")
    delivered_lines = [
        {
            "product": line.product_id.default_code,
            "qty_ordered": float(line.product_uom_qty),
            "qty_delivered": float(line.qty_delivered),
            "qty_invoiced": float(line.qty_invoiced),
            "is_foc": bool(getattr(line, "is_foc", False)),
        }
        for line in order.order_line
    ]
    cogs_lines = _collect_moves(invoice)
    foc_account = env.company.foc_cogs_adjust_account_id
    foc_account_used = bool(foc_account and foc_account.id in cogs_lines.mapped("account_id").ids)
    return {
        "case": label,
        "pass": bool(mos_after_confirm) and bool(done_pickings) and bool(invoice and invoice.state == "posted"),
        "order": _serialize_order(order),
        "mo_count_after_confirm": len(mos_after_confirm),
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
        "auto_invoice_after_confirm": [inv.name for inv in auto_invoice_after_confirm],
        "auto_invoice_after_processing": [inv.name for inv in auto_invoices],
        "invoice_state": invoice.state if invoice else False,
        "invoice_total": float(invoice.amount_total) if invoice else 0.0,
        "done_pickings": [p.name for p in done_pickings],
        "sale_line_delivery": delivered_lines,
        "invoice_line_flags": [
            {
                "product": line.product_id.default_code,
                "price_unit": float(line.price_unit),
                "is_foc": bool(getattr(line, "is_foc", False)),
                "foc_price_unit": float(getattr(line, "foc_price_unit", 0.0)),
            }
            for line in (invoice.invoice_line_ids if invoice else env["account.move.line"])
        ],
        "cogs_accounts": [line.account_id.code for line in cogs_lines],
        "foc_expected_account": foc_account.code if foc_account else False,
        "foc_expected_account_used": foc_account_used,
        "notes": [
            "Invoice creation is validated after delivery completion.",
            "The case passes only when the invoice is created and posted automatically.",
        ],
    }


def _run_mts_case(env):
    product = _get_product(env, "FG-PNC-TH-01001")
    orderpoint = env["stock.warehouse.orderpoint"].search(
        [("product_id", "=", product.id), ("location_id.complete_name", "=", "GMP/Stock")],
        order="id desc",
        limit=1,
    )
    if not orderpoint:
        raise ValueError("No GMP orderpoint found for FG-PNC-TH-01001.")
    target_qty = 130.0
    product_ctx = product.with_context(
        company_id=orderpoint.company_id.id, location=orderpoint.location_id.id
    )
    qty_on_hand_before = float(product_ctx.qty_available)
    qty_forecast_before = float(product_ctx.virtual_available)
    target_level = max(qty_forecast_before, 0.0) + target_qty
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
    except Exception as exc:
        env.cr.rollback()
        return {
            "case": "mts_min_max",
            "pass": False,
            "stage": "action_replenish",
            "product_code": product.default_code,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }
    mos_after_replenish = env["mrp.production"].search([("id", ">", mo_before)], order="id")
    product_lots = {}
    completed_mos = _complete_mos(
        env, mos_after_replenish, product_lots, "MTS", picking_before=picking_before
    )
    all_pickings = _process_pending_pickings(env, picking_before, product_lots, "MTS")
    orderpoint.write(original_rule)
    product_ctx = product.with_context(
        company_id=orderpoint.company_id.id, location=orderpoint.location_id.id
    )
    qty_on_hand_after = float(product_ctx.qty_available)
    qty_forecast_after = float(product_ctx.virtual_available)
    return {
        "case": "mts_min_max",
        "pass": bool(mos_after_replenish) and qty_on_hand_after > qty_on_hand_before,
        "orderpoint_id": orderpoint.id,
        "orderpoint_route_id": orderpoint.route_id.id if orderpoint.route_id else False,
        "orderpoint_min_before": original_rule["product_min_qty"],
        "orderpoint_max_before": original_rule["product_max_qty"],
        "replenish_target_level": target_level,
        "qty_on_hand_before": qty_on_hand_before,
        "qty_forecast_before": qty_forecast_before,
        "qty_on_hand_after": qty_on_hand_after,
        "qty_forecast_after": qty_forecast_after,
        "mo_count_after_replenish": len(mos_after_replenish),
        "mo_names_after_replenish": mos_after_replenish.mapped("name"),
        "replenishment_created_from_orderpoint": [
            {
                "name": mo.name,
                "orderpoint_id": mo.orderpoint_id.id if mo.orderpoint_id else False,
                "origin": mo.origin,
            }
            for mo in mos_after_replenish
        ],
        "completed_mos": completed_mos,
        "pickings_after_run": [
            {"name": p.name, "type": p.picking_type_id.code, "state": p.state}
            for p in all_pickings
        ],
        "notes": [
            "This scenario validates true Min/Max replenishment from the orderpoint itself.",
            "The case passes only when the orderpoint creates manufacturing and stock increases after completion.",
        ],
    }


def _run():
    results = []
    cases = [
        ("promo_free_item", _run_promo_case),
        ("foc_zero_mto", lambda env: _run_sales_flow_case(env, "foc_zero_mto", "FG-PNC-XX-01001", is_foc=True)),
        ("mto_standard", lambda env: _run_sales_flow_case(env, "mto_standard", "FG-MTK-IL-01001", is_foc=False)),
        ("mts_min_max", _run_mts_case),
    ]
    for case_name, runner in cases:
        try:
            result = runner(env)
        except Exception as exc:
            result = {
                "case": case_name,
                "pass": False,
                "error": str(exc),
                "traceback": traceback.format_exc(),
            }
            env.cr.rollback()
        if not result.get("case"):
            result["case"] = case_name
        results.append(result)
    summary = {
        "database": env.cr.dbname,
        "run_tag": RUN_TAG,
        "run_at": datetime.now().isoformat(),
        "passed_cases": [res["case"] for res in results if res.get("pass")],
        "failed_cases": [res["case"] for res in results if not res.get("pass")],
        "cases": results,
    }
    report = _report_path()
    report.write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"REPORT|{report}")
    print(json.dumps({"passed": summary["passed_cases"], "failed": summary["failed_cases"]}, ensure_ascii=True))


_run()
