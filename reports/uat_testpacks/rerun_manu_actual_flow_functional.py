import types
import json
import traceback
from pathlib import Path

from odoo import api


DATE_TAG = "20260407"
ROOT = Path.cwd()
REPORT_JSON = ROOT / "reports" / f"manu_actual_flow_functional_rerun_{DATE_TAG}.json"
REPORT_MD = ROOT / "reports" / f"manu_actual_flow_functional_rerun_{DATE_TAG}.md"


def load_module(name, path, stop_marker=None):
    source = path.read_text(encoding="utf-8")
    if stop_marker and stop_marker in source:
        source = source.split(stop_marker, 1)[0]
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(source, str(path), "exec"), module.__dict__)
    return module


FULLFLOW = load_module(
    "fullflow_local",
    ROOT / "custom" / "goldmints_addon-main" / "scripts" / "db11_live_fullflow_test.py",
    "\ndef _run():",
)
SHOPFLOOR = load_module(
    "shopfloor_auto_local",
    ROOT / "reports" / "shopfloor_auto_uat_suite.py",
    "\nTESTS = [",
)
LATE_BO = load_module(
    "late_backorder_local",
    ROOT / "reports" / "late_backorder_recovery_uat_test.py",
    "\nreport = {",
)


def fresh_env():
    return api.Environment(
        env.cr,
        env.uid,
        dict(
            env.context,
            tracking_disable=True,
            mail_create_nolog=True,
            mail_notrack=True,
        ),
    )


def json_safe(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(v) for v in value]
    return str(value)


def run_case(case_id, mu_ids, phase, name, runner):
    try:
        result = runner()
        return {
            "case_id": case_id,
            "mu_ids": mu_ids,
            "phase": phase,
            "name": name,
            "status": "passed",
            "result": json_safe(result),
        }
    except AssertionError as exc:
        return {
            "case_id": case_id,
            "mu_ids": mu_ids,
            "phase": phase,
            "name": name,
            "status": "failed",
            "error": str(exc),
            "traceback": traceback.format_exc(limit=8),
        }
    except Exception as exc:
        return {
            "case_id": case_id,
            "mu_ids": mu_ids,
            "phase": phase,
            "name": name,
            "status": "failed",
            "error": str(exc),
            "traceback": traceback.format_exc(limit=12),
        }
    finally:
        env.cr.rollback()


def get_route(shell_env, name):
    route = shell_env["stock.route"].search([("name", "=", name)], limit=1)
    assert route, f"Route not found: {name}"
    return route


def get_picking_type(shell_env, name):
    picking_type = shell_env["stock.picking.type"].search([("name", "=", name)], limit=1)
    assert picking_type, f"Operation type not found: {name}"
    return picking_type


def get_unit_uom(shell_env):
    return SHOPFLOOR.get_unit_uom(shell_env)


def create_temp_product(shell_env, name, route_names=None):
    unit = get_unit_uom(shell_env)
    vals = {
        "name": name,
        "type": "consu",
        "is_storable": True,
        "uom_id": unit.id,
        "uom_po_id": unit.id,
    }
    product = shell_env["product.template"].create(vals).product_variant_id
    tmpl = product.product_tmpl_id
    if "approval_state" in tmpl._fields:
        tmpl.approval_state = "approved"
    if "approval_state" in product._fields:
        product.approval_state = "approved"
    if route_names:
        route_ids = [get_route(shell_env, route_name).id for route_name in route_names]
        product.write({"route_ids": [(6, 0, route_ids)]})
    return product


def create_temp_vendor(shell_env, name):
    vals = {"name": name, "supplier_rank": 1}
    if "approval_state" in shell_env["res.partner"]._fields:
        vals["approval_state"] = "approved"
    return shell_env["res.partner"].create(vals)


def full_mo_case():
    shell_env = fresh_env()
    pt = SHOPFLOOR.get_mrp_operation_type(shell_env)
    unit = get_unit_uom(shell_env)
    wc = SHOPFLOOR.create_workcenter(shell_env, "TMP ACTUAL MO WC")
    finished = SHOPFLOOR.create_product(shell_env, "TMP ACTUAL MO FG", unit)
    component = SHOPFLOOR.create_product(shell_env, "TMP ACTUAL MO COMP", unit)
    bom = SHOPFLOOR.create_bom(
        shell_env,
        finished,
        component,
        component_qty=2.0,
        operation_vals={
            "name": "ACTUAL MO OP",
            "workcenter_id": wc.id,
            "time_mode": "manual",
            "time_cycle_manual": 60.0,
        },
    )
    SHOPFLOOR.prepare_component_stock(shell_env, component, pt.default_location_src_id, 50.0)
    mo = SHOPFLOOR.create_mo(shell_env, "TMP ACTUAL MO", finished, bom, 5.0, pt)
    product_lots = {}
    FULLFLOW._complete_mo(shell_env, mo, product_lots, "ACTUALMO")
    mo.invalidate_recordset()
    raw_move = mo.move_raw_ids.filtered(lambda m: m.product_id == component)[:1]
    return {
        "mo": mo.name,
        "state": mo.state,
        "product_qty": mo.product_qty,
        "raw_required_qty": raw_move.product_uom_qty,
        "raw_done_qty": raw_move.quantity if "quantity" in raw_move._fields else raw_move.quantity_done,
        "finished_moves": mo.move_finished_ids.filtered(lambda m: m.state == "done").mapped("name"),
        "workorders": [
            {
                "name": wo.display_name,
                "state": wo.state,
                "qty_produced": wo.qty_produced,
            }
            for wo in mo.workorder_ids
        ],
    }


def partial_material_case():
    shell_env = fresh_env()
    pt = SHOPFLOOR.get_mrp_operation_type(shell_env)
    unit = get_unit_uom(shell_env)
    wc = SHOPFLOOR.create_workcenter(shell_env, "TMP PARTIAL MAT WC")
    finished = SHOPFLOOR.create_product(shell_env, "TMP PARTIAL MAT FG", unit)
    component = SHOPFLOOR.create_product(shell_env, "TMP PARTIAL MAT COMP", unit)
    bom = SHOPFLOOR.create_bom(
        shell_env,
        finished,
        component,
        component_qty=10.0,
        operation_vals={
            "name": "PARTIAL MAT OP",
            "workcenter_id": wc.id,
            "time_mode": "manual",
            "time_cycle_manual": 60.0,
        },
    )
    SHOPFLOOR.prepare_component_stock(shell_env, component, pt.default_location_src_id, 4.0)
    mo = SHOPFLOOR.create_mo(shell_env, "TMP PARTIAL MAT MO", finished, bom, 1.0, pt)
    mo.action_assign()
    raw_move = mo.move_raw_ids.filtered(lambda m: m.product_id == component)[:1]
    reserved = sum(raw_move.move_line_ids.mapped("quantity"))
    assert reserved < raw_move.product_uom_qty, "Raw material unexpectedly fully reserved."
    assert raw_move.state in ("partially_available", "confirmed", "waiting"), "Unexpected move state for partial material scenario."
    return {
        "mo": mo.name,
        "state": mo.state,
        "raw_required_qty": raw_move.product_uom_qty,
        "raw_reserved_qty": reserved,
        "forecast_availability": raw_move.forecast_availability if "forecast_availability" in raw_move._fields else None,
        "reservation_state": raw_move.state,
    }


def mts_live_case():
    shell_env = fresh_env()
    result = FULLFLOW._run_mts_live_case(shell_env)
    assert result["pass"], "MTS replenishment did not create completed supply."
    return result


def mts_no_doc_case():
    shell_env = fresh_env()
    pt = SHOPFLOOR.get_mrp_operation_type(shell_env)
    unit = get_unit_uom(shell_env)
    finished = create_temp_product(shell_env, "TMP MTS ENOUGH FG", ["Manufacture"])
    component = create_temp_product(shell_env, "TMP MTS ENOUGH COMP")
    bom = SHOPFLOOR.create_bom(shell_env, finished, component, component_qty=1.0)
    orderpoint_location = pt.default_location_dest_id
    shell_env["stock.quant"]._update_available_quantity(finished, orderpoint_location, 10.0)
    orderpoint = shell_env["stock.warehouse.orderpoint"].create(
        {
            "product_id": finished.id,
            "location_id": orderpoint_location.id,
            "product_min_qty": 5.0,
            "product_max_qty": 5.0,
            "qty_multiple": 1.0,
            "trigger": "auto",
            "route_id": get_route(shell_env, "Manufacture").id,
        }
    )
    mo_before = shell_env["mrp.production"].search_count([])
    picking_before = shell_env["stock.picking"].search_count([])
    orderpoint.action_replenish(force_to_max=True)
    mo_after = shell_env["mrp.production"].search_count([])
    picking_after = shell_env["stock.picking"].search_count([])
    assert mo_after == mo_before, "Unexpected MO created while stock was already sufficient."
    assert picking_after == picking_before, "Unexpected picking created while stock was already sufficient."
    return {
        "product": finished.default_code or finished.display_name,
        "qty_available": finished.with_context(location=orderpoint_location.id).qty_available,
        "orderpoint_min": orderpoint.product_min_qty,
        "orderpoint_max": orderpoint.product_max_qty,
    }


def mts_chain_case():
    shell_env = fresh_env()
    product = FULLFLOW._get_product(shell_env, "FG-PSS-TH-01005")
    orderpoint = shell_env["stock.warehouse.orderpoint"].search(
        [("product_id", "=", product.id), ("location_id.complete_name", "=", "GMP/Stock")],
        order="id desc",
        limit=1,
    )
    assert orderpoint, "No orderpoint for FG-PSS-TH-01005"
    mo_before = shell_env["mrp.production"].search([], order="id desc", limit=1).id or 0
    picking_before = shell_env["stock.picking"].search([], order="id desc", limit=1).id or 0
    ctx_product = product.with_context(company_id=orderpoint.company_id.id, location=orderpoint.location_id.id)
    target = max(float(ctx_product.virtual_available), 0.0) + 10.0
    original = {
        "product_min_qty": float(orderpoint.product_min_qty),
        "product_max_qty": float(orderpoint.product_max_qty),
        "qty_multiple": float(orderpoint.qty_multiple),
        "trigger": orderpoint.trigger,
    }
    orderpoint.write({"product_min_qty": target, "product_max_qty": target, "qty_multiple": 1.0, "trigger": "auto"})
    try:
        orderpoint.action_replenish(force_to_max=True)
        mos = shell_env["mrp.production"].search([("id", ">", mo_before)], order="id")
        pickings = shell_env["stock.picking"].search([("id", ">", picking_before)], order="id")
        codes = set(mos.mapped("picking_type_id.sequence_code"))
        picking_names = pickings.mapped("picking_type_id.name")
        assert mos, "No MOs created for child chain product."
        assert len(mos) > 1, "Expected child MOs for deep MTS chain."
        assert any(name in ("Transfer Plastic", "Transfer Pharma") for name in picking_names), "Expected internal transfer pickings in child chain."
        return {
            "product": product.default_code,
            "mo_names": mos.mapped("name"),
            "operation_codes": sorted(codes),
            "pickings": [
                {"name": p.name, "type": p.picking_type_id.name, "state": p.state}
                for p in pickings
            ],
        }
    finally:
        orderpoint.write(original)


def mto_full_case():
    shell_env = fresh_env()
    result = FULLFLOW._run_sales_flow_case(shell_env, "local_mto_full", "FG-MTK-IL-01001", False)
    order = result.get("order", {})
    done_pickings = result.get("done_pickings") or []
    delivered = any(
        (line.get("qty_delivered") or 0) >= (line.get("qty_ordered") or 0)
        for line in result.get("sale_line_delivery") or []
    )
    # Local UAT currently completes this MTO-coded product from available stock, so a fresh
    # MO is not mandatory for the functional proof of the end-to-end sales flow.
    assert order.get("state") == "sale", "Sale order was not confirmed."
    assert done_pickings, "No completed picking found for local MTO flow."
    assert delivered, "MTO product was not fully delivered."
    return result


def mto_shortage_buy_case():
    shell_env = fresh_env()
    defaults = FULLFLOW._get_sale_defaults(shell_env)
    unit = get_unit_uom(shell_env)
    vendor = create_temp_vendor(shell_env, "TMP MTO BUY VENDOR")
    component = create_temp_product(shell_env, "TMP MTO BUY COMP", ["Buy"])
    component.write(
        {
            "seller_ids": [
                (
                    0,
                    0,
                    {
                        "partner_id": vendor.id,
                        "price": 10.0,
                        "min_qty": 1.0,
                    },
                )
            ]
        }
    )
    finished = create_temp_product(
        shell_env,
        "TMP MTO BUY FG",
        ["Replenish on Order (MTO)", "Manufacture (Pharma)"],
    )
    mrp_type = SHOPFLOOR.get_mrp_operation_type(shell_env)
    bom = shell_env["mrp.bom"].create(
        {
            "product_tmpl_id": finished.product_tmpl_id.id,
            "product_id": finished.id,
            "product_qty": 1.0,
            "type": "normal",
            "bom_line_ids": [
                (0, 0, {"product_id": component.id, "product_qty": 2.0, "product_uom_id": component.uom_id.id})
            ],
        }
    )
    partner = FULLFLOW._make_customer(shell_env, "TMP MTO BUY CUSTOMER", eligible=False)
    mo_before = shell_env["mrp.production"].search([], order="id desc", limit=1).id or 0
    po_before = shell_env["purchase.order"].search([], order="id desc", limit=1).id or 0
    order = shell_env["sale.order"].create(
        {
            "partner_id": partner.id,
            "warehouse_id": defaults["warehouse_id"],
            "team_id": defaults["team_id"],
            "pricelist_id": defaults["pricelist_id"],
            "payment_term_id": defaults["payment_term_id"],
            "so_type_id": defaults.get("so_type_id"),
            "client_order_ref": "TMP-MTO-BUY",
            "order_line": [(0, 0, {"product_id": finished.id, "product_uom_qty": 1.0})],
        }
    )
    order.action_confirm()
    mos = shell_env["mrp.production"].search([("id", ">", mo_before)], order="id")
    pos = shell_env["purchase.order"].search([("id", ">", po_before)], order="id")
    assert mos, "No MO created for temp MTO shortage case."
    assert pos, "No RFQ/PO created for temp MTO shortage case."
    return {
        "order": order.name,
        "mo_names": mos.mapped("name"),
        "po_names": pos.mapped("name"),
        "component": component.display_name,
    }


def transfer_full_case(op_name):
    shell_env = fresh_env()
    picking_type = get_picking_type(shell_env, op_name)
    unit = get_unit_uom(shell_env)
    product = SHOPFLOOR.create_product(shell_env, f"TMP {op_name} FULL PROD", unit)
    parent = picking_type.warehouse_id.lot_stock_id
    src = shell_env["stock.location"].create({"name": f"TMP {op_name} SRC", "usage": "internal", "location_id": parent.id})
    dst = shell_env["stock.location"].create({"name": f"TMP {op_name} DST", "usage": "internal", "location_id": parent.id})
    shell_env["stock.quant"]._update_available_quantity(product, src, 10.0)
    picking = shell_env["stock.picking"].create(
        {
            "picking_type_id": picking_type.id,
            "location_id": src.id,
            "location_dest_id": dst.id,
            "move_ids": [(0, 0, {
                "name": product.display_name,
                "product_id": product.id,
                "product_uom_qty": 10.0,
                "product_uom": product.uom_id.id,
                "location_id": src.id,
                "location_dest_id": dst.id,
            })],
        }
    )
    picking.action_confirm()
    picking.action_assign()
    for ml in picking.move_line_ids:
        ml.quantity = 10.0
    picking.button_validate()
    picking.invalidate_recordset()
    assert picking.state == "done", f"{op_name} full transfer not done."
    return {"picking": picking.name, "state": picking.state}


def transfer_partial_standard_case(op_name):
    shell_env = fresh_env()
    picking_type = get_picking_type(shell_env, op_name)
    original = picking_type.create_backorder
    picking_type.create_backorder = "ask"
    try:
        unit = get_unit_uom(shell_env)
        product = SHOPFLOOR.create_product(shell_env, f"TMP {op_name} PART PROD", unit)
        parent = picking_type.warehouse_id.lot_stock_id
        src = shell_env["stock.location"].create({"name": f"TMP {op_name} PART SRC", "usage": "internal", "location_id": parent.id})
        dst = shell_env["stock.location"].create({"name": f"TMP {op_name} PART DST", "usage": "internal", "location_id": parent.id})
        shell_env["stock.quant"]._update_available_quantity(product, src, 10.0)
        picking = shell_env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "location_id": src.id,
                "location_dest_id": dst.id,
                "move_ids": [(0, 0, {
                    "name": product.display_name,
                    "product_id": product.id,
                    "product_uom_qty": 10.0,
                    "product_uom": product.uom_id.id,
                    "location_id": src.id,
                    "location_dest_id": dst.id,
                })],
            }
        )
        picking.action_confirm()
        picking.action_assign()
        for ml in picking.move_line_ids:
            ml.quantity = 4.0
        action = picking.button_validate()
        assert action and action.get("res_model") == "stock.backorder.confirmation", "Expected stock backorder wizard."
        wiz = shell_env["stock.backorder.confirmation"].with_context(action["context"]).create({"pick_ids": [(6, 0, picking.ids)]})
        wiz.process()
        picking.invalidate_recordset()
        backorders = picking.backorder_ids
        assert backorders, "No standard backorder created."
        return {
            "original_picking": picking.name,
            "backorder": backorders[:1].name,
            "backorder_qty": backorders.move_ids[:1].product_uom_qty,
        }
    finally:
        picking_type.create_backorder = original


def transfer_late_recovery_case(op_name):
    shell_env = fresh_env()
    picking_type = get_picking_type(shell_env, op_name)
    original = picking_type.create_backorder
    picking_type.create_backorder = "ask"
    try:
        unit = get_unit_uom(shell_env)
        product = SHOPFLOOR.create_product(shell_env, f"TMP {op_name} LATE PROD", unit)
        parent = picking_type.warehouse_id.lot_stock_id
        src = shell_env["stock.location"].create({"name": f"TMP {op_name} LATE SRC", "usage": "internal", "location_id": parent.id})
        dst = shell_env["stock.location"].create({"name": f"TMP {op_name} LATE DST", "usage": "internal", "location_id": parent.id})
        shell_env["stock.quant"]._update_available_quantity(product, src, 10.0)
        picking = shell_env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "location_id": src.id,
                "location_dest_id": dst.id,
                "move_ids": [(0, 0, {
                    "name": product.display_name,
                    "product_id": product.id,
                    "product_uom_qty": 10.0,
                    "product_uom": product.uom_id.id,
                    "location_id": src.id,
                    "location_dest_id": dst.id,
                })],
            }
        )
        picking.action_confirm()
        picking.action_assign()
        for ml in picking.move_line_ids:
            ml.quantity = 4.0
        action = picking.button_validate()
        assert action and action.get("res_model") == "stock.backorder.confirmation", "Expected stock backorder wizard."
        wiz = shell_env["stock.backorder.confirmation"].with_context(action["context"]).create({"pick_ids": [(6, 0, picking.ids)]})
        wiz.process_cancel_backorder()
        picking.invalidate_recordset()
        assert picking.can_create_late_backorder, "Late backorder button not available."
        late_action = picking.action_create_late_backorder()
        late = shell_env["stock.picking"].browse(late_action["res_id"])
        return {
            "original_picking": picking.name,
            "late_backorder": late.name,
            "late_qty": late.move_ids[:1].product_uom_qty,
        }
    finally:
        picking_type.create_backorder = original


def mo_partial_standard_case():
    shell_env = fresh_env()
    pt = SHOPFLOOR.get_mrp_operation_type(shell_env, ask_only=False)
    assert pt, "No manufacturing operation type found."
    original = pt.create_backorder
    pt.create_backorder = "ask"
    try:
        unit = get_unit_uom(shell_env)
        finished = SHOPFLOOR.create_product(shell_env, "TMP MO PART FG", unit)
        component = SHOPFLOOR.create_product(shell_env, "TMP MO PART COMP", unit)
        bom = shell_env["mrp.bom"].create(
            {
                "product_tmpl_id": finished.product_tmpl_id.id,
                "product_id": finished.id,
                "product_qty": 1.0,
                "type": "normal",
                "bom_line_ids": [(0, 0, {
                    "product_id": component.id,
                    "product_qty": 1.0,
                    "product_uom_id": component.uom_id.id,
                })],
            }
        )
        shell_env["stock.quant"]._update_available_quantity(component, pt.default_location_src_id, 100.0)
        mo = shell_env["mrp.production"].create(
            {
                "product_id": finished.id,
                "product_qty": 10.0,
                "product_uom_id": finished.uom_id.id,
                "bom_id": bom.id,
                "picking_type_id": pt.id,
                "location_src_id": pt.default_location_src_id.id,
                "location_dest_id": pt.default_location_dest_id.id,
            }
        )
        mo.action_confirm()
        mo.action_assign()
        mo.qty_producing = 4.0
        for ml in mo.move_raw_ids.move_line_ids:
            ml.quantity = 4.0
            if "picked" in ml._fields:
                ml.picked = True
        action = mo.button_mark_done()
        assert action and action.get("res_model") == "mrp.production.backorder", "Expected MRP backorder wizard."
        wiz = shell_env["mrp.production.backorder"].with_context(action["context"]).create({"mrp_production_ids": [(6, 0, mo.ids)]})
        for line in wiz.mrp_production_backorder_line_ids:
            line.to_backorder = True
        wiz.action_backorder()
        mo.invalidate_recordset()
        backorders = mo.backorder_ids
        if not backorders and hasattr(mo, "late_backorder_ids"):
            backorders = mo.late_backorder_ids
        assert backorders, "No MO backorder created."
        return {
            "original_mo": mo.name,
            "backorder_mo": backorders[:1].name,
            "backorder_qty": backorders[:1].product_qty,
        }
    finally:
        pt.create_backorder = original


def overproduction_case():
    SHOPFLOOR.env = env
    return SHOPFLOOR.test_overproduction_sync()


def leftover_return_case():
    shell_env = fresh_env()
    picking_type = get_picking_type(shell_env, "Transfer Pharma")
    unit = get_unit_uom(shell_env)
    product = SHOPFLOOR.create_product(shell_env, "TMP LEFTOVER PROD", unit)
    stock = picking_type.warehouse_id.lot_stock_id
    staging = stock.child_ids.filtered(lambda loc: loc.name == "คลังลอย")[:1]
    if not staging:
        staging = shell_env["stock.location"].search([("complete_name", "=", "GMP/Stock/คลังลอย")], limit=1)
    if not staging:
        fallback = shell_env["stock.location"].browse(176)
        if fallback.exists() and fallback.usage == "internal" and fallback.complete_name.startswith("GMP/Stock/"):
            staging = fallback
    assert staging and stock, "Required staging/stock locations not found."
    shell_env["stock.quant"]._update_available_quantity(product, staging, 5.0)
    picking = shell_env["stock.picking"].create(
        {
            "picking_type_id": picking_type.id,
            "location_id": staging.id,
            "location_dest_id": stock.id,
            "move_ids": [(0, 0, {
                "name": product.display_name,
                "product_id": product.id,
                "product_uom_qty": 5.0,
                "product_uom": product.uom_id.id,
                "location_id": staging.id,
                "location_dest_id": stock.id,
            })],
        }
    )
    picking.action_confirm()
    picking.action_assign()
    for ml in picking.move_line_ids:
        ml.quantity = 5.0
    picking.button_validate()
    picking.invalidate_recordset()
    assert picking.state == "done", "Leftover return picking not done."
    return {
        "picking": picking.name,
        "source": staging.complete_name,
        "destination": stock.complete_name,
    }


def stock_move_trace_case():
    shell_env = fresh_env()
    data = full_mo_case()
    # Recreate within same case to inspect move structure instead of relying on nested rollback.
    pt = SHOPFLOOR.get_mrp_operation_type(shell_env)
    unit = get_unit_uom(shell_env)
    wc = SHOPFLOOR.create_workcenter(shell_env, "TMP TRACE WC")
    finished = SHOPFLOOR.create_product(shell_env, "TMP TRACE FG", unit)
    component = SHOPFLOOR.create_product(shell_env, "TMP TRACE COMP", unit)
    bom = SHOPFLOOR.create_bom(
        shell_env,
        finished,
        component,
        component_qty=3.0,
        operation_vals={"name": "TRACE OP", "workcenter_id": wc.id, "time_mode": "manual", "time_cycle_manual": 60.0},
    )
    SHOPFLOOR.prepare_component_stock(shell_env, component, pt.default_location_src_id, 50.0)
    mo = SHOPFLOOR.create_mo(shell_env, "TMP TRACE MO", finished, bom, 2.0, pt)
    FULLFLOW._complete_mo(shell_env, mo, {}, "TRACE")
    raw_moves = mo.move_raw_ids.filtered(lambda m: m.state == "done")
    finished_moves = mo.move_finished_ids.filtered(lambda m: m.state == "done")
    assert raw_moves and finished_moves, "Expected done raw and finished moves for trace."
    return {
        "mo": mo.name,
        "raw_moves": [{"name": m.name, "qty": m.product_uom_qty, "state": m.state} for m in raw_moves],
        "finished_moves": [{"name": m.name, "qty": m.quantity if 'quantity' in m._fields else m.product_uom_qty, "state": m.state} for m in finished_moves],
        "from_manual_flow": data["mo"],
    }


def bom_vs_actual_case():
    shell_env = fresh_env()
    pt = SHOPFLOOR.get_mrp_operation_type(shell_env)
    unit = get_unit_uom(shell_env)
    finished = SHOPFLOOR.create_product(shell_env, "TMP BOM ACT FG", unit)
    component = SHOPFLOOR.create_product(shell_env, "TMP BOM ACT COMP", unit)
    bom = shell_env["mrp.bom"].create(
        {
            "product_tmpl_id": finished.product_tmpl_id.id,
            "product_id": finished.id,
            "product_qty": 1.0,
            "type": "normal",
            "bom_line_ids": [(0, 0, {"product_id": component.id, "product_qty": 2.0, "product_uom_id": component.uom_id.id})],
        }
    )
    shell_env["stock.quant"]._update_available_quantity(component, pt.default_location_src_id, 100.0)
    mo = shell_env["mrp.production"].create(
        {
            "product_id": finished.id,
            "product_qty": 3.0,
            "product_uom_id": finished.uom_id.id,
            "bom_id": bom.id,
            "picking_type_id": pt.id,
            "location_src_id": pt.default_location_src_id.id,
            "location_dest_id": pt.default_location_dest_id.id,
        }
    )
    mo.action_confirm()
    raw_move = mo.move_raw_ids.filtered(lambda m: m.product_id == component)[:1]
    expected = 6.0
    assert raw_move.product_uom_qty == expected, f"Expected {expected} component demand, got {raw_move.product_uom_qty}"
    return {
        "mo": mo.name,
        "bom_component_per_unit": 2.0,
        "fg_qty": 3.0,
        "expected_component_qty": expected,
        "move_component_qty": raw_move.product_uom_qty,
    }


CASES = [
    ("F01", ["MU06-01"], "01_ตรวจสต็อกและวางแผน", "MTS shortage creates MO", mts_live_case),
    ("F02", ["MU06-02"], "01_ตรวจสต็อกและวางแผน", "MTS enough stock creates no document", mts_no_doc_case),
    ("F03", ["MU06-03", "MU02-03"], "01_ตรวจสต็อกและวางแผน", "MTS child chain creates child MOs and transfers", mts_chain_case),
    ("F04", ["MU02-01", "MU07-01"], "02_เปิดงานผลิต", "Manual MO full flow closes successfully", full_mo_case),
    ("F05", ["MU02-02"], "02_เปิดงานผลิต", "Manual MO with partial materials stays short", partial_material_case),
    ("F06", ["MU05-01"], "02_เปิดงานผลิต", "MTO sales flow creates and completes supply", mto_full_case),
    ("F07", ["MU05-02"], "02_เปิดงานผลิต", "MTO shortage traces upstream purchase supply", mto_shortage_buy_case),
    ("F08", ["MU03-01"], "03_โอนและBackorder", "Transfer Plastic full", lambda: transfer_full_case("Transfer Plastic")),
    ("F09", ["MU03-02"], "03_โอนและBackorder", "Transfer Plastic partial standard backorder", lambda: transfer_partial_standard_case("Transfer Plastic")),
    ("F10", ["MU03-03"], "03_โอนและBackorder", "Transfer Plastic late backorder recovery", lambda: transfer_late_recovery_case("Transfer Plastic")),
    ("F11", ["MU04-01"], "03_โอนและBackorder", "Transfer Pharma full", lambda: transfer_full_case("Transfer Pharma")),
    ("F12", ["MU04-02"], "03_โอนและBackorder", "Transfer Pharma partial standard backorder", lambda: transfer_partial_standard_case("Transfer Pharma")),
    ("F13", ["MU04-03"], "03_โอนและBackorder", "Transfer Pharma late backorder recovery", lambda: transfer_late_recovery_case("Transfer Pharma")),
    ("F14", ["MU07-02"], "05_ปิดงานและแก้ไข", "MO partial standard backorder", mo_partial_standard_case),
    ("F15", ["MU07-04"], "05_ปิดงานและแก้ไข", "Overproduction sync updates demand", overproduction_case),
    ("F16", ["MU08-02"], "05_ปิดงานและแก้ไข", "Return leftovers from staging to stock", leftover_return_case),
    ("F17", ["MU10-02"], "07_รายงานต้นทุนUoM", "Stock movement trace from MO raw to FG", stock_move_trace_case),
    ("F18", ["MU10-03"], "07_รายงานต้นทุนUoM", "BOM demand equals actual component demand on MO", bom_vs_actual_case),
]


results = [run_case(case_id, mu_ids, phase, name, runner) for case_id, mu_ids, phase, name, runner in CASES]
summary = {
    "database": env.cr.dbname,
    "date": DATE_TAG,
    "total_cases": len(results),
    "passed": sum(1 for item in results if item["status"] == "passed"),
    "failed": sum(1 for item in results if item["status"] != "passed"),
}

REPORT_JSON.write_text(
    json.dumps({"summary": summary, "cases": results}, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

lines = [
    "# Local UAT Manufacturing Functional Rerun",
    "",
    f"- Database: `{summary['database']}`",
    f"- Date tag: `{DATE_TAG}`",
    f"- Passed: `{summary['passed']}/{summary['total_cases']}`",
    "",
]
for item in results:
    lines.append(f"## {item['case_id']} - {item['name']}")
    lines.append(f"- Phase: `{item['phase']}`")
    lines.append(f"- MU IDs: `{', '.join(item['mu_ids'])}`")
    lines.append(f"- Status: `{item['status']}`")
    if item["status"] == "passed":
        lines.append("- Result:")
        lines.append("```json")
        lines.append(json.dumps(item["result"], ensure_ascii=False, indent=2))
        lines.append("```")
    else:
        lines.append(f"- Error: `{item.get('error')}`")
    lines.append("")

REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
print(json.dumps({"summary": summary, "report_json": str(REPORT_JSON), "report_md": str(REPORT_MD)}, ensure_ascii=False, indent=2))
