from __future__ import annotations

import json
import re
import sys
import traceback
from datetime import datetime, timedelta
from pathlib import Path

if globals().get("__file__"):
    ROOT = Path(__file__).resolve().parents[3]
else:
    ROOT = Path.cwd()
SERVER_PATH = ROOT / "server"
if str(SERVER_PATH) not in sys.path:
    sys.path.insert(0, str(SERVER_PATH))

import odoo
import odoo.service.server
from odoo import SUPERUSER_ID, api
from odoo.modules.registry import Registry
from odoo.tools import config

DB_NAME = "11"
RUN_TAG = datetime.now().strftime("%Y%m%d%H%M%S")
REPORT_NAME = f"db11_mold_validation_live_{RUN_TAG}.json"
DOC_INDEX_NAME = f"db11_mold_validation_live_doc_index_{RUN_TAG}.csv"

CASES = [
    {
        "name": "pls_up_w01",
        "product_code": "SM-PLS-UP-01001",
        "machine_id": 567,
        "mold_id": 579,
        "qty": 12.0,
        "good_qty": 11.0,
        "scrap_qty": 1.0,
        "labor_minutes": 10.0,
    },
    {
        "name": "joi_pk_w02",
        "product_code": "SM-JOI-PK-02001",
        "machine_id": 565,
        "mold_id": 590,
        "qty": 12.0,
        "good_qty": 11.0,
        "scrap_qty": 1.0,
        "labor_minutes": 10.0,
    },
    {
        "name": "pnc_bt_bottle",
        "product_code": "SM-PNC-BT-03001",
        "machine_id": 568,
        "mold_id": 594,
        "qty": 12.0,
        "good_qty": 11.0,
        "scrap_qty": 1.0,
        "labor_minutes": 10.0,
    },
    {
        "name": "ppr_th_cap",
        "product_code": "SM-PPR-TH-02001",
        "machine_id": 567,
        "mold_id": 591,
        "qty": 12.0,
        "good_qty": 11.0,
        "scrap_qty": 1.0,
        "labor_minutes": 10.0,
    },
    {
        "name": "pnf_ca_cap",
        "product_code": "SM-PNF-CA-02001",
        "machine_id": 570,
        "mold_id": 596,
        "qty": 12.0,
        "good_qty": 11.0,
        "scrap_qty": 1.0,
        "labor_minutes": 10.0,
    },
]


def _report_path() -> Path:
    path = ROOT / "reports" / REPORT_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _doc_index_path() -> Path:
    path = ROOT / "reports" / DOC_INDEX_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _round(value, digits=4):
    return round(float(value or 0.0), digits)


def _load_env():
    config.parse_config(["-c", str(ROOT / "server" / "odoo.conf"), "-d", DB_NAME])
    odoo.service.server.load_server_wide_modules()
    registry = Registry(DB_NAME)
    cr = registry.cursor()
    return api.Environment(cr, SUPERUSER_ID, {}), cr


def _load_flow_helpers():
    helper_path = ROOT / "custom" / "goldmints_addon-main" / "scripts" / "db11_live_fullflow_test.py"
    source = helper_path.read_text(encoding="utf-8-sig")
    source = re.sub(r"\n_run\(\)\s*$", "\n", source)
    namespace = {"__file__": str(helper_path), "__name__": "db11_live_fullflow_helper"}
    exec(compile(source, str(helper_path), "exec"), namespace)
    namespace["RUN_TAG"] = RUN_TAG
    return namespace


def _serialize_workorders(workorders):
    rows = []
    for wo in workorders:
        rows.append(
            {
                "id": wo.id,
                "name": wo.name,
                "state": wo.state,
                "workcenter_id": wo.workcenter_id.id,
                "workcenter_name": wo.workcenter_id.name,
                "duration_expected": _round(wo.duration_expected),
                "duration": _round(wo.duration),
                "qty_production": _round(wo.qty_production),
                "qty_produced": _round(wo.qty_produced),
                "console_qty": _round(getattr(wo, "console_qty", 0.0)),
                "mold_ids": wo.mold_ids.ids,
                "mold_names": wo.mold_ids.mapped("name"),
                "mold_cost": _round(getattr(wo, "mold_cost", 0.0)),
                "employee_names": wo.employee_ids.mapped("name"),
            }
        )
    return rows


def _extended_cost_snapshot(env, mo, helper_ns, standard_before):
    base = helper_ns["_mo_cost_snapshot"](mo, standard_before=standard_before)
    productivity_lines = env["mrp.workcenter.productivity"].search(
        [("workorder_id", "in", mo.workorder_ids.ids)],
        order="id",
    )
    machine_actual = sum(
        ((wo.duration or 0.0) / 60.0) * (wo.workcenter_id.costs_hour or 0.0)
        for wo in mo.workorder_ids
    )
    machine_std = sum(
        ((wo.duration_expected or 0.0) / 60.0) * (wo.workcenter_id.costs_hour or 0.0)
        for wo in mo.workorder_ids
    )
    core_labor_actual = sum(productivity_lines.mapped("total_cost"))
    core_labor_std = sum(
        ((wo.duration_expected or 0.0) / 60.0)
        * (wo.workcenter_id.employee_costs_hour or 0.0)
        * (wo.operation_id.employee_ratio or 1.0)
        for wo in mo.workorder_ids
    )
    finished_minus_raw = base["finished_value_total"] - base["raw_cost_total"]
    residual_after_custom = (
        finished_minus_raw - base["labor_cost_total"] - base["mold_cost_total"]
    )
    machine_plus_core_labor_actual = machine_actual + core_labor_actual
    if core_labor_actual > 0 and base["labor_cost_total"] > 0:
        labor_logic = "double_source_risk"
    elif core_labor_actual > 0:
        labor_logic = "core_only"
    elif base["labor_cost_total"] > 0:
        labor_logic = "custom_only"
    else:
        labor_logic = "missing"
    return {
        **base,
        "finished_minus_raw_total": _round(finished_minus_raw),
        "residual_after_custom_total": _round(residual_after_custom),
        "machine_actual_total": _round(machine_actual),
        "machine_std_total": _round(machine_std),
        "core_labor_actual_total": _round(core_labor_actual),
        "core_labor_std_total": _round(core_labor_std),
        "machine_plus_core_labor_actual_total": _round(machine_plus_core_labor_actual),
        "residual_vs_machine_only": _round(residual_after_custom - machine_actual),
        "residual_vs_machine_plus_core_labor": _round(
            residual_after_custom - machine_plus_core_labor_actual
        ),
        "labor_logic": labor_logic,
        "productivity_lines": [
            {
                "id": line.id,
                "employee": line.employee_id.name,
                "workcenter": line.workcenter_id.name,
                "date_start": str(line.date_start),
                "date_end": str(line.date_end),
                "duration": _round(line.duration),
                "employee_cost": _round(line.employee_cost),
                "total_cost": _round(line.total_cost),
            }
            for line in productivity_lines
        ],
    }


def _run_case(env, helper_ns, case):
    helper_ns["SHOPFLOOR_PRODUCT"] = case["product_code"]
    helper_ns["SHOPFLOOR_MACHINE_ID"] = case["machine_id"]
    helper_ns["SHOPFLOOR_MOLD_ID"] = case["mold_id"]
    helper_ns["SHOPFLOOR_QTY"] = case["qty"]
    helper_ns["SHOPFLOOR_GOOD_QTY"] = case["good_qty"]
    helper_ns["SHOPFLOOR_SCRAP_QTY"] = case["scrap_qty"]
    helper_ns["SHOPFLOOR_CYCLE_TIME"] = 30.0
    helper_ns["SHOPFLOOR_MOLD_COST_HOUR"] = 60.0
    helper_ns["SHOPFLOOR_MOLD_LIFE_LIMIT"] = 1000
    helper_ns["SHOPFLOOR_LABOR_MINUTES"] = case["labor_minutes"]

    product = helper_ns["_get_product"](env, case["product_code"])
    bom = helper_ns["_get_bom"](env, product)
    if not bom:
        raise ValueError(f"No BoM found for {case['product_code']}.")
    employee = env["hr.employee"].search(
        [("company_id", "in", [env.company.id, False])],
        order="id",
        limit=1,
    )
    if not employee:
        raise ValueError("No employee found for the mold validation test.")
    mold_setup = helper_ns["_ensure_mold_mapping"](env, product)
    picking_before = env["stock.picking"].search([], order="id desc", limit=1).id or 0
    standard_before = _round(product.standard_price)
    picking_type = bom.picking_type_id or env["stock.picking.type"].search(
        [("name", "=", "Manufacturing Plastic")],
        limit=1,
    )
    mo = env["mrp.production"].create(
        {
            "product_id": product.id,
            "product_qty": case["qty"],
            "product_uom_id": product.uom_id.id,
            "bom_id": bom.id,
            "origin": f"CODEX-MOLD-VALIDATION-{case['name']}-{RUN_TAG}",
            "picking_type_id": picking_type.id,
            "location_src_id": picking_type.default_location_src_id.id,
            "location_dest_id": picking_type.default_location_dest_id.id,
        }
    )
    confirm_res = mo.action_confirm()
    if isinstance(confirm_res, dict) and confirm_res.get("res_model") == "mrp.mold.warning.wizard":
        env[confirm_res["res_model"]].browse(confirm_res["res_id"]).action_confirm_anyway()
    mo.invalidate_recordset()
    initial_workorders = _serialize_workorders(mo.workorder_ids)
    auto_mold_match = any(case["mold_id"] in row["mold_ids"] for row in initial_workorders)

    mo.action_assign()
    fg_lot = helper_ns["_make_lot"](env, product, f"{case['name']}-FG")
    product_lots = {}
    if fg_lot:
        product_lots[product.id] = fg_lot
        if "lot_producing_id" in mo._fields:
            mo.lot_producing_id = fg_lot.id

    for move in mo.move_raw_ids.filtered(lambda move: move.state not in ("done", "cancel")):
        qty = move.product_uom_qty or getattr(move, "quantity", 0.0) or 0.0
        lot = product_lots.get(move.product_id.id)
        if move.product_id.tracking in ("lot", "serial") and not lot:
            lot = helper_ns["_make_lot"](env, move.product_id, f"{case['name']}-RM")
            product_lots[move.product_id.id] = lot
        stock_buffer = max(getattr(move.product_uom, "rounding", 0.0) or 0.0, 0.01)
        helper_ns["_put_stock"](
            env,
            move.product_id,
            move.location_id,
            qty + stock_buffer,
            lot=lot,
        )
        helper_ns["_pin_move"](move, qty, lot=lot)

    workorders = mo.workorder_ids.filtered(lambda wo: wo.state != "cancel")
    for workorder in workorders:
        workorder.action_console_set_employees([employee.id])
        workorder.action_console_start_timer()
        open_lines = env["mrp.workcenter.productivity"].search(
            [("workorder_id", "=", workorder.id), ("date_end", "=", False)]
        )
        backdated_start = datetime.now() - timedelta(minutes=case["labor_minutes"])
        open_lines.write({"date_start": backdated_start})
        workorder.write({"console_qty": case["good_qty"]})
        env["mrp.workorder.qty.log"].create(
            {
                "workorder_id": workorder.id,
                "qty": case["good_qty"],
                "note": f"CODEX-MOLD-{case['name']}-{RUN_TAG}",
                "employee_ids": [(6, 0, [employee.id])],
            }
        )
        workorder.action_console_stop_timer()

    scrap_loc = env["stock.location"].search(
        [("scrap_location", "=", True), ("company_id", "in", [mo.company_id.id, False])],
        limit=1,
    )
    scrap_vals = {
        "product_id": product.id,
        "scrap_qty": case["scrap_qty"],
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

    result_action = mo._console_apply_quantities_and_backorder(workorders)
    if isinstance(result_action, dict) and result_action.get("res_model") == "mrp.production.backorder":
        env[result_action["res_model"]].browse(result_action["res_id"]).action_close_mo()

    pending_pickings = helper_ns["_process_pending_pickings"](
        env, picking_before, product_lots, case["name"].upper()
    )

    mo.invalidate_recordset()
    workorders.invalidate_recordset()
    scrap.invalidate_recordset()
    mold = env["mrp.workcenter"].browse(case["mold_id"])
    matrix_lines = env["mrp.mold.matrix.report"].search(
        [("product_id", "=", product.id)],
        order="units_per_hour desc, machine_id, mold_id",
    )
    costing = _extended_cost_snapshot(env, mo, helper_ns, standard_before)
    return {
        "case": case["name"],
        "pass": bool(
            mo.state == "done"
            and scrap.state == "done"
            and auto_mold_match
            and bool(mo.labor_move_id)
            and bool(mo.mold_move_id)
            and mo.employee_cost_total > 0
            and mo.mold_cost_total > 0
            and mold.mold_life_current > mold_setup["mold_life_current_before"]
        ),
        "product_code": case["product_code"],
        "mo_name": mo.name,
        "picking_type": picking_type.name,
        "auto_mold_match": auto_mold_match,
        "mold_setup": {
            **mold_setup,
            "mold_life_current_after": mold.mold_life_current,
        },
        "initial_workorders": initial_workorders,
        "final_workorders": _serialize_workorders(workorders),
        "scrap": {
            "name": scrap.name,
            "state": scrap.state,
            "qty": _round(scrap.scrap_qty),
            "lot": scrap.lot_id.name if getattr(scrap, "lot_id", False) else False,
        },
        "pickings": [
            {
                "name": picking.name,
                "type": picking.picking_type_id.name,
                "code": picking.picking_type_id.code,
                "state": picking.state,
            }
            for picking in pending_pickings
        ],
        "open_pickings": [
            {
                "name": picking.name,
                "type": picking.picking_type_id.name,
                "code": picking.picking_type_id.code,
                "state": picking.state,
            }
            for picking in pending_pickings.filtered(lambda p: p.state not in ("done", "cancel"))
        ],
        "matrix_candidates": [
            {
                "machine_id": line.machine_id.id,
                "machine_name": line.machine_id.name,
                "mold_id": line.mold_id.id,
                "mold_name": line.mold_id.name,
                "cycle_time": _round(line.cycle_time),
                "units_per_hour": _round(line.units_per_hour),
                "mold_state": line.mold_state,
            }
            for line in matrix_lines
        ],
        "documents": {
            "labor_move": mo.labor_move_id.name if mo.labor_move_id else False,
            "mold_move": mo.mold_move_id.name if mo.mold_move_id else False,
        },
        "costing": costing,
    }


def _write_doc_index(results):
    lines = ["case,product_code,mo_name,scrap_name,labor_move,mold_move,pickings"]
    for result in results:
        pickings = "|".join(p["name"] for p in result.get("pickings", []))
        scrap_name = result.get("scrap", {}).get("name", "") if result.get("scrap") else ""
        labor_move = result.get("documents", {}).get("labor_move", "") if result.get("documents") else ""
        mold_move = result.get("documents", {}).get("mold_move", "") if result.get("documents") else ""
        row = [
            result.get("case", ""),
            result.get("product_code", ""),
            result.get("mo_name", ""),
            scrap_name,
            labor_move,
            mold_move,
            pickings,
        ]
        lines.append(",".join(f'"{str(value).replace("\"", "\"\"")}"' for value in row))
    _doc_index_path().write_text("\n".join(lines), encoding="utf-8")


def main():
    helper_ns = _load_flow_helpers()
    env, cr = _load_env()
    results = []
    selected = set(sys.argv[1:])
    cases = [case for case in CASES if not selected or case["name"] in selected]
    try:
        for case in cases:
            try:
                result = _run_case(env, helper_ns, case)
                env.cr.commit()
                if hasattr(env, "invalidate_all"):
                    env.invalidate_all()
            except Exception as exc:
                env.cr.rollback()
                result = {
                    "case": case["name"],
                    "product_code": case["product_code"],
                    "pass": False,
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                }
            results.append(result)
        summary = {
            "database": DB_NAME,
            "run_tag": RUN_TAG,
            "run_at": datetime.now().isoformat(),
            "selected_cases": [case["name"] for case in cases],
            "passed_cases": [row["case"] for row in results if row.get("pass")],
            "failed_cases": [row["case"] for row in results if not row.get("pass")],
            "cases": results,
        }
        _report_path().write_text(
            json.dumps(summary, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        _write_doc_index(results)
        print(f"REPORT|{_report_path()}")
        print(f"DOC_INDEX|{_doc_index_path()}")
        print(
            json.dumps(
                {
                    "passed": summary["passed_cases"],
                    "failed": summary["failed_cases"],
                },
                ensure_ascii=True,
            )
        )
    finally:
        cr.close()


if __name__ == "__main__":
    main()
