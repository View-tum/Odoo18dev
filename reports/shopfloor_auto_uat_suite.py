import json
import traceback
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

from odoo import api, fields
from odoo.exceptions import UserError

import odoo.addons.mrp_parallel_console.controllers.mrp_parallel_console as base_console_module
import odoo.addons.mrp_scrap_auto_replenish.controllers.mrp_parallel_console_override as scrap_console_module


DATE_TAG = "20260406"
REPORT_JSON = Path("reports") / f"shopfloor_auto_uat_suite_{DATE_TAG}.json"
REPORT_MD = Path("reports") / f"shopfloor_auto_uat_suite_{DATE_TAG}.md"
EXISTING_UI_JSON = Path("reports") / "mold_shopfloor_uat_full_20260406.json"


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


def patch_request(shell_env):
    dummy = SimpleNamespace(env=shell_env)
    base_console_module.request = dummy
    scrap_console_module.request = dummy
    return dummy


def module_installed(shell_env, name):
    module = shell_env["ir.module.module"].search([("name", "=", name)], limit=1)
    return bool(module and module.state == "installed")


def get_unit_uom(shell_env):
    Uom = shell_env["uom.uom"]
    return Uom.search([("name", "in", ["Units", "Unit", "หน่วย"])], limit=1) or Uom.search([], limit=1)


def get_mrp_operation_type(shell_env, ask_only=False):
    domain = [
        ("code", "=", "mrp_operation"),
        ("warehouse_id.company_id", "=", shell_env.company.id),
    ]
    if ask_only:
        domain.append(("create_backorder", "=", "ask"))
    return shell_env["stock.picking.type"].search(domain, limit=1)


def get_internal_operation_type(shell_env, ask_only=False):
    domain = [
        ("code", "=", "internal"),
        ("warehouse_id.company_id", "=", shell_env.company.id),
    ]
    if ask_only:
        domain.append(("create_backorder", "=", "ask"))
    return shell_env["stock.picking.type"].search(domain, limit=1)


def create_product(shell_env, name, uom=None):
    uom = uom or get_unit_uom(shell_env)
    tmpl = shell_env["product.template"].create(
        {
            "name": name,
            "type": "consu",
            "is_storable": True,
            "uom_id": uom.id,
            "uom_po_id": uom.id,
        }
    )
    return tmpl.product_variant_id


def create_workcenter(shell_env, name, **extra_vals):
    wc_model = shell_env["mrp.workcenter"]
    vals = {
        "name": name,
        "code": name[:12].upper().replace(" ", "_"),
        "time_efficiency": 100.0,
        "oee_target": 1.0,
        "default_capacity": 1.0,
        "costs_hour": 10.0,
    }
    vals = {key: value for key, value in vals.items() if key in wc_model._fields}
    vals.update({key: value for key, value in extra_vals.items() if key in wc_model._fields})
    return wc_model.create(vals)


def create_bom(shell_env, finished, component, component_qty=1.0, operation_vals=None):
    vals = {
        "product_tmpl_id": finished.product_tmpl_id.id,
        "product_id": finished.id,
        "product_qty": 1.0,
        "type": "normal",
        "bom_line_ids": [
            (
                0,
                0,
                {
                    "product_id": component.id,
                    "product_qty": component_qty,
                    "product_uom_id": component.uom_id.id,
                },
            )
        ],
    }
    if operation_vals:
        vals["operation_ids"] = [(0, 0, operation_vals)]
    return shell_env["mrp.bom"].create(vals)


def create_mo(shell_env, name, finished, bom, qty, picking_type):
    mo = shell_env["mrp.production"].create(
        {
            "name": name,
            "product_id": finished.id,
            "product_qty": qty,
            "product_uom_id": finished.uom_id.id,
            "bom_id": bom.id,
            "picking_type_id": picking_type.id,
            "location_src_id": picking_type.default_location_src_id.id,
            "location_dest_id": picking_type.default_location_dest_id.id,
        }
    )
    mo.action_confirm()
    return mo


def prepare_component_stock(shell_env, product, location, qty):
    shell_env["stock.quant"]._update_available_quantity(product, location, qty)


def run_case(case_id, name, runner):
    try:
        result = runner()
        return {
            "id": case_id,
            "name": name,
            "status": "passed",
            "result": json_safe(result),
        }
    except AssertionError as exc:
        return {
            "id": case_id,
            "name": name,
            "status": "failed",
            "error": str(exc),
            "traceback": traceback.format_exc(limit=6),
        }
    except Exception as exc:
        return {
            "id": case_id,
            "name": name,
            "status": "failed",
            "error": str(exc),
            "traceback": traceback.format_exc(limit=10),
        }
    finally:
        env.cr.rollback()


def test_module_presence():
    shell_env = fresh_env()
    modules = [
        "mrp_parallel_console",
        "mrp_mold_management",
        "mrp_scrap_auto_replenish",
        "mrp_workcenter_lock",
        "late_backorder_recovery",
        "mrp_scrap_finished_Good",
    ]
    states = {name: module_installed(shell_env, name) for name in modules}
    missing = [name for name, installed in states.items() if not installed]
    assert not missing, f"Missing installed modules: {', '.join(missing)}"
    return {"modules": states}


def test_workcenter_lock():
    shell_env = fresh_env()
    pt = get_mrp_operation_type(shell_env)
    assert pt, "No manufacturing operation type found."
    unit = get_unit_uom(shell_env)
    wc = create_workcenter(shell_env, "TMP LOCK WC")
    finished_1 = create_product(shell_env, "TMP LOCK FG 1", unit)
    component_1 = create_product(shell_env, "TMP LOCK COMP 1", unit)
    bom_1 = create_bom(
        shell_env,
        finished_1,
        component_1,
        component_qty=1.0,
        operation_vals={
            "name": "LOCK OP",
            "workcenter_id": wc.id,
            "time_mode": "manual",
            "time_cycle_manual": 60.0,
        },
    )
    finished_2 = create_product(shell_env, "TMP LOCK FG 2", unit)
    component_2 = create_product(shell_env, "TMP LOCK COMP 2", unit)
    bom_2 = create_bom(
        shell_env,
        finished_2,
        component_2,
        component_qty=1.0,
        operation_vals={
            "name": "LOCK OP 2",
            "workcenter_id": wc.id,
            "time_mode": "manual",
            "time_cycle_manual": 60.0,
        },
    )
    prepare_component_stock(shell_env, component_1, pt.default_location_src_id, 10.0)
    prepare_component_stock(shell_env, component_2, pt.default_location_src_id, 10.0)
    mo_1 = create_mo(shell_env, "TMP LOCK MO 1", finished_1, bom_1, 2.0, pt)
    mo_2 = create_mo(shell_env, "TMP LOCK MO 2", finished_2, bom_2, 2.0, pt)
    mo_1.action_assign()
    mo_2.action_assign()
    wo_1 = mo_1.workorder_ids[:1]
    wo_2 = mo_2.workorder_ids[:1]
    wo_1.button_start()
    blocked = False
    message = ""
    try:
        wo_2.button_start()
    except UserError as exc:
        blocked = True
        message = str(exc)
    assert blocked, "Second workorder on the same workcenter was not blocked."
    return {
        "workcenter": wc.display_name,
        "first_workorder": wo_1.display_name,
        "second_workorder": wo_2.display_name,
        "block_message": message,
    }


def test_parallel_split_distribution():
    shell_env = fresh_env()
    pt = get_mrp_operation_type(shell_env)
    assert pt, "No manufacturing operation type found."
    unit = get_unit_uom(shell_env)
    wc_fast = create_workcenter(shell_env, "TMP PAR FAST", default_capacity=2.0)
    wc_slow = create_workcenter(shell_env, "TMP PAR SLOW", default_capacity=1.0)
    finished = create_product(shell_env, "TMP PAR FG", unit)
    component = create_product(shell_env, "TMP PAR COMP", unit)
    bom = create_bom(
        shell_env,
        finished,
        component,
        component_qty=1.0,
        operation_vals={
            "name": "PAR SPLIT OP",
            "workcenter_id": wc_fast.id,
            "time_mode": "manual",
            "time_cycle_manual": 60.0,
            "parallel_mode": "parallel",
            "parallel_workcenter_ids": [(6, 0, [wc_slow.id])],
        },
    )
    prepare_component_stock(shell_env, component, pt.default_location_src_id, 50.0)
    mo = create_mo(shell_env, "TMP PAR SPLIT MO", finished, bom, 9.0, pt)
    active_wos = mo.workorder_ids.filtered(lambda wo: wo.state != "cancel")
    planned = {wo.workcenter_id.display_name: wo.planned_qty for wo in active_wos}
    assert len(active_wos) == 2, f"Expected 2 active parallel workorders, got {len(active_wos)}"
    assert sum(active_wos.mapped("planned_qty")) == 9.0, "Planned quantities do not sum to MO quantity."
    assert sorted(active_wos.mapped("planned_qty"), reverse=True) == [6.0, 3.0], f"Unexpected parallel split: {planned}"
    return {
        "mo": mo.name,
        "workorders": [
            {
                "name": wo.display_name,
                "workcenter": wo.workcenter_id.display_name,
                "planned_qty": wo.planned_qty,
            }
            for wo in active_wos.sorted("id")
        ],
    }


def test_mold_auto_assignment():
    shell_env = fresh_env()
    pt = get_mrp_operation_type(shell_env)
    assert pt, "No manufacturing operation type found."
    unit = get_unit_uom(shell_env)
    machine = create_workcenter(shell_env, "TMP MOLD MACHINE")
    mold = create_workcenter(
        shell_env,
        "TMP MOLD TOOL",
        is_mold=True,
        mold_cost_hour=25.0,
        mold_life_limit=100,
        mold_cavities=2,
    )
    machine.allowed_mold_ids = [(6, 0, [mold.id])]
    finished = create_product(shell_env, "TMP MOLD FG", unit)
    component = create_product(shell_env, "TMP MOLD COMP", unit)
    shell_env["mrp.mold.product.line"].create(
        {
            "mold_id": mold.id,
            "product_id": finished.id,
            "cycle_time": 30.0,
        }
    )
    bom = create_bom(
        shell_env,
        finished,
        component,
        component_qty=1.0,
        operation_vals={
            "name": "MOLD OP",
            "workcenter_id": machine.id,
            "time_mode": "manual",
            "time_cycle_manual": 60.0,
        },
    )
    prepare_component_stock(shell_env, component, pt.default_location_src_id, 20.0)
    mo = create_mo(shell_env, "TMP MOLD MO", finished, bom, 10.0, pt)
    wo = mo.workorder_ids[:1]
    assert wo.mold_ids == mold, "Mold was not auto-assigned from matrix."
    assert wo.duration_expected > 0, "Expected duration was not updated from mold speed."
    return {
        "mo": mo.name,
        "workorder": wo.display_name,
        "assigned_mold": wo.mold_ids.display_name,
        "duration_expected": wo.duration_expected,
    }


def test_unique_parallel_mold_guard():
    shell_env = fresh_env()
    pt = get_mrp_operation_type(shell_env)
    assert pt, "No manufacturing operation type found."
    unit = get_unit_uom(shell_env)
    wc_a = create_workcenter(shell_env, "TMP GUARD A", default_capacity=1.0)
    wc_b = create_workcenter(shell_env, "TMP GUARD B", default_capacity=1.0)
    mold = create_workcenter(
        shell_env,
        "TMP GUARD MOLD",
        is_mold=True,
        mold_life_limit=100,
        mold_cavities=1,
    )
    wc_a.allowed_mold_ids = [(6, 0, [mold.id])]
    wc_b.allowed_mold_ids = [(6, 0, [mold.id])]
    finished = create_product(shell_env, "TMP GUARD FG", unit)
    component = create_product(shell_env, "TMP GUARD COMP", unit)
    shell_env["mrp.mold.product.line"].create(
        {
            "mold_id": mold.id,
            "product_id": finished.id,
            "cycle_time": 40.0,
        }
    )
    bom = create_bom(
        shell_env,
        finished,
        component,
        component_qty=1.0,
        operation_vals={
            "name": "GUARD OP",
            "workcenter_id": wc_a.id,
            "time_mode": "manual",
            "time_cycle_manual": 60.0,
            "parallel_mode": "parallel",
            "parallel_workcenter_ids": [(6, 0, [wc_b.id])],
        },
    )
    prepare_component_stock(shell_env, component, pt.default_location_src_id, 20.0)
    mo = create_mo(shell_env, "TMP GUARD MO", finished, bom, 8.0, pt)
    active = mo.workorder_ids.filtered(lambda wo: wo.state != "cancel")
    cancelled = mo.workorder_ids.filtered(lambda wo: wo.state == "cancel")
    active_with_mold = active.filtered("mold_ids")
    assert len(active) == 1, f"Expected only 1 active workorder after unique mold guard, got {len(active)}"
    assert len(active_with_mold) == 1, "Active workorder does not hold the unique mold."
    assert cancelled, "Expected sibling workorder to be cancelled by mold guard."
    return {
        "mo": mo.name,
        "active_workorders": [
            {
                "name": wo.display_name,
                "state": wo.state,
                "molds": wo.mold_ids.mapped("display_name"),
            }
            for wo in active
        ],
        "cancelled_workorders": [
            {
                "name": wo.display_name,
                "state": wo.state,
            }
            for wo in cancelled
        ],
    }


def test_mold_ui_helper():
    shell_env = fresh_env()
    patch_request(shell_env)
    pt = get_mrp_operation_type(shell_env)
    assert pt, "No manufacturing operation type found."
    unit = get_unit_uom(shell_env)
    ctrl = base_console_module.MrpParallelConsoleController()

    machine = create_workcenter(shell_env, "TMP UI MOLD MACHINE")
    mold = create_workcenter(shell_env, "TMP UI MOLD TOOL", is_mold=True, mold_life_limit=50)
    machine.allowed_mold_ids = [(6, 0, [mold.id])]
    finished = create_product(shell_env, "TMP UI MOLD FG", unit)
    component = create_product(shell_env, "TMP UI MOLD COMP", unit)
    shell_env["mrp.mold.product.line"].create({"mold_id": mold.id, "product_id": finished.id, "cycle_time": 25.0})
    bom_mold = create_bom(
        shell_env,
        finished,
        component,
        component_qty=1.0,
        operation_vals={
            "name": "UI MOLD OP",
            "workcenter_id": machine.id,
            "time_mode": "manual",
            "time_cycle_manual": 60.0,
        },
    )
    prepare_component_stock(shell_env, component, pt.default_location_src_id, 20.0)
    mo_mold = create_mo(shell_env, "TMP UI MOLD MO", finished, bom_mold, 5.0, pt)
    wo_mold = mo_mold.workorder_ids[:1]

    wc_plain = create_workcenter(shell_env, "TMP UI PLAIN MACHINE")
    finished_2 = create_product(shell_env, "TMP UI PLAIN FG", unit)
    component_2 = create_product(shell_env, "TMP UI PLAIN COMP", unit)
    bom_plain = create_bom(
        shell_env,
        finished_2,
        component_2,
        component_qty=1.0,
        operation_vals={
            "name": "UI PLAIN OP",
            "workcenter_id": wc_plain.id,
            "time_mode": "manual",
            "time_cycle_manual": 60.0,
        },
    )
    prepare_component_stock(shell_env, component_2, pt.default_location_src_id, 20.0)
    mo_plain = create_mo(shell_env, "TMP UI PLAIN MO", finished_2, bom_plain, 5.0, pt)
    wo_plain = mo_plain.workorder_ids[:1]

    assert ctrl._mpc_should_show_mold_ui(wo_mold) is True, "Mold UI should be visible on mold-capable workorder."
    assert ctrl._mpc_should_show_mold_ui(wo_plain) is False, "Mold UI should be hidden on non-mold workorder."
    return {
        "mold_workorder": wo_mold.display_name,
        "mold_ui": True,
        "plain_workorder": wo_plain.display_name,
        "plain_ui": False,
    }


def test_console_timer_and_qty_logs():
    shell_env = fresh_env()
    patch_request(shell_env)
    pt = get_mrp_operation_type(shell_env)
    assert pt, "No manufacturing operation type found."
    unit = get_unit_uom(shell_env)
    wc = create_workcenter(shell_env, "TMP TIMER WC")
    finished = create_product(shell_env, "TMP TIMER FG", unit)
    component = create_product(shell_env, "TMP TIMER COMP", unit)
    bom = create_bom(
        shell_env,
        finished,
        component,
        component_qty=1.0,
        operation_vals={
            "name": "TIMER OP",
            "workcenter_id": wc.id,
            "time_mode": "manual",
            "time_cycle_manual": 60.0,
        },
    )
    prepare_component_stock(shell_env, component, pt.default_location_src_id, 20.0)
    mo = create_mo(shell_env, "TMP TIMER MO", finished, bom, 5.0, pt)
    wo = mo.workorder_ids[:1]
    ctrl = base_console_module.MrpParallelConsoleController()
    employee = shell_env["hr.employee"].create({"name": "TMP Timer Operator"})
    wo.employee_ids = [(6, 0, [employee.id])]
    start_dt = wo.action_console_start_timer()
    open_logs = shell_env["mrp.workcenter.productivity"].search(
        [("workorder_id", "=", wo.id), ("employee_id", "=", employee.id), ("date_end", "=", False)]
    )
    assert open_logs, "Console start timer did not create/open productivity lines."
    stop_dt = wo.action_console_stop_timer()
    open_logs_after = shell_env["mrp.workcenter.productivity"].search_count(
        [("workorder_id", "=", wo.id), ("employee_id", "=", employee.id), ("date_end", "=", False)]
    )
    assert open_logs_after == 0, "Console stop timer left productivity lines open."
    ctrl.add_qty_log(wo.id, 3.0, note="batch 1", employee_ids=[employee.id])
    ctrl.add_qty_log(wo.id, 2.0, note="batch 2", employee_ids=[employee.id])
    total = ctrl._get_effective_console_qty(wo)
    assert total == 5.0, f"Expected effective console qty 5.0, got {total}"
    return {
        "workorder": wo.display_name,
        "start": fields.Datetime.to_string(start_dt),
        "stop": fields.Datetime.to_string(stop_dt),
        "effective_qty": total,
    }


def test_employee_cost_compute():
    shell_env = fresh_env()
    pt = get_mrp_operation_type(shell_env)
    assert pt, "No manufacturing operation type found."
    unit = get_unit_uom(shell_env)
    wc = create_workcenter(shell_env, "TMP LABOR WC", costs_hour=50.0, employee_costs_hour=120.0)
    finished = create_product(shell_env, "TMP LABOR FG", unit)
    component = create_product(shell_env, "TMP LABOR COMP", unit)
    bom = create_bom(
        shell_env,
        finished,
        component,
        component_qty=1.0,
        operation_vals={
            "name": "LABOR OP",
            "workcenter_id": wc.id,
            "time_mode": "manual",
            "time_cycle_manual": 60.0,
        },
    )
    prepare_component_stock(shell_env, component, pt.default_location_src_id, 20.0)
    mo = create_mo(shell_env, "TMP LABOR MO", finished, bom, 5.0, pt)
    wo = mo.workorder_ids[:1]
    employee = shell_env["hr.employee"].create({"name": "TMP Labor Operator"})
    now = fields.Datetime.now()
    productive_loss = shell_env["mrp.workcenter.productivity.loss"].search([("loss_type", "=", "productive")], limit=1)
    assert productive_loss, "No productive loss reason found for productivity log creation."
    shell_env["mrp.workcenter.productivity"].create(
        {
            "workorder_id": wo.id,
            "workcenter_id": wc.id,
            "employee_id": employee.id,
            "loss_id": productive_loss.id,
            "date_start": now - timedelta(hours=1),
            "date_end": now,
            "description": "TMP labor log",
        }
    )
    mo.invalidate_recordset()
    assert mo.employee_cost_total > 0, "Employee cost total was not computed from productivity logs."
    return {
        "mo": mo.name,
        "employee_cost_total": mo.employee_cost_total,
    }


def test_overproduction_sync():
    shell_env = fresh_env()
    pt = get_mrp_operation_type(shell_env)
    assert pt, "No manufacturing operation type found."
    unit = get_unit_uom(shell_env)
    wc = create_workcenter(shell_env, "TMP OVER WC")
    finished = create_product(shell_env, "TMP OVER FG", unit)
    component = create_product(shell_env, "TMP OVER COMP", unit)
    bom = create_bom(
        shell_env,
        finished,
        component,
        component_qty=1.0,
        operation_vals={
            "name": "OVER OP",
            "workcenter_id": wc.id,
            "time_mode": "manual",
            "time_cycle_manual": 60.0,
        },
    )
    prepare_component_stock(shell_env, component, pt.default_location_src_id, 50.0)
    mo = create_mo(shell_env, "TMP OVER MO", finished, bom, 10.0, pt)
    move = mo.move_raw_ids.filtered(lambda m: m.product_id == component)[:1]
    assert move, "No raw move generated for overproduction test."
    ok = mo._console_sync_demand_and_replenish(12.0)
    move.invalidate_recordset()
    assert ok is True, "Overproduction sync did not run."
    assert mo.product_qty == 12.0, f"MO product_qty not updated, got {mo.product_qty}"
    assert move.product_uom_qty == 12.0, f"Raw move demand not updated, got {move.product_uom_qty}"
    return {
        "mo": mo.name,
        "new_product_qty": mo.product_qty,
        "new_component_qty": move.product_uom_qty,
    }


def test_scrap_product_guard():
    shell_env = fresh_env()
    pt = get_mrp_operation_type(shell_env)
    assert pt, "No manufacturing operation type found."
    unit = get_unit_uom(shell_env)
    wc = create_workcenter(shell_env, "TMP SCRAP WC")
    finished = create_product(shell_env, "TMP SCRAP FG", unit)
    component = create_product(shell_env, "TMP SCRAP COMP", unit)
    unrelated = create_product(shell_env, "TMP SCRAP OTHER", unit)
    bom = create_bom(
        shell_env,
        finished,
        component,
        component_qty=2.0,
        operation_vals={
            "name": "SCRAP OP",
            "workcenter_id": wc.id,
            "time_mode": "manual",
            "time_cycle_manual": 60.0,
        },
    )
    prepare_component_stock(shell_env, component, pt.default_location_src_id, 20.0)
    mo = create_mo(shell_env, "TMP SCRAP MO", finished, bom, 5.0, pt)
    wo = mo.workorder_ids[:1]
    action = wo.button_scrap()
    allowed_ids = set((action.get("context") or {}).get("allowed_product_ids") or [])
    assert finished.id in allowed_ids, "Finished product missing from allowed scrap products."
    assert component.id in allowed_ids, "Component missing from allowed scrap products."
    assert unrelated.id not in allowed_ids, "Unrelated product leaked into allowed scrap products."
    return {
        "workorder": wo.display_name,
        "allowed_product_ids": sorted(list(allowed_ids)),
    }


def test_scrap_auto_replenish_same_location():
    shell_env = fresh_env()
    patch_request(shell_env)
    pt = get_mrp_operation_type(shell_env)
    assert pt, "No manufacturing operation type found."
    unit = get_unit_uom(shell_env)
    wc = create_workcenter(shell_env, "TMP SCRAP SAME WC")
    finished = create_product(shell_env, "TMP SCRAP SAME FG", unit)
    component = create_product(shell_env, "TMP SCRAP SAME COMP", unit)
    bom = create_bom(
        shell_env,
        finished,
        component,
        component_qty=5.0,
        operation_vals={
            "name": "SCRAP SAME OP",
            "workcenter_id": wc.id,
            "time_mode": "manual",
            "time_cycle_manual": 60.0,
        },
    )
    prepare_component_stock(shell_env, component, pt.default_location_src_id, 30.0)
    mo = create_mo(shell_env, "TMP SCRAP SAME MO", finished, bom, 1.0, pt)
    mo.action_assign()
    wo = mo.workorder_ids[:1]
    raw_move = mo.move_raw_ids.filtered(lambda m: m.product_id == component)[:1]
    ctrl = scrap_console_module.MrpParallelConsoleControllerOverride()
    res = ctrl.create_scrap(
        workorder_id=wo.id,
        product_id=component.id,
        quantity=2.0,
        location_id=mo.location_src_id.id,
        workcenter_name=wc.display_name,
    )
    raw_move.invalidate_recordset()
    replenishment_pickings = shell_env["stock.picking"].search([("origin", "=", f"Scrap Replenish for {mo.name}")])
    assert res.get("status") == "success", f"Scrap creation failed: {res}"
    assert raw_move.product_uom_qty == 7.0, f"Expected raw demand 7.0 after scrap replenish, got {raw_move.product_uom_qty}"
    assert not replenishment_pickings, "Unexpected internal replenishment picking was created."
    return {
        "mo": mo.name,
        "raw_move_qty": raw_move.product_uom_qty,
        "scrap_id": res.get("scrap_id"),
    }


def test_scrap_auto_replenish_internal_transfer():
    shell_env = fresh_env()
    patch_request(shell_env)
    pt = get_mrp_operation_type(shell_env)
    assert pt, "No manufacturing operation type found."
    unit = get_unit_uom(shell_env)
    wc = create_workcenter(shell_env, "TMP SCRAP INT WC")
    finished = create_product(shell_env, "TMP SCRAP INT FG", unit)
    component = create_product(shell_env, "TMP SCRAP INT COMP", unit)
    bom = create_bom(
        shell_env,
        finished,
        component,
        component_qty=5.0,
        operation_vals={
            "name": "SCRAP INT OP",
            "workcenter_id": wc.id,
            "time_mode": "manual",
            "time_cycle_manual": 60.0,
        },
    )
    warehouse = pt.warehouse_id
    prepare_component_stock(shell_env, component, warehouse.lot_stock_id, 30.0)
    mo = create_mo(shell_env, "TMP SCRAP INT MO", finished, bom, 1.0, pt)
    wo = mo.workorder_ids[:1]
    raw_move = mo.move_raw_ids.filtered(lambda m: m.product_id == component)[:1]
    ctrl = scrap_console_module.MrpParallelConsoleControllerOverride()
    res = ctrl.create_scrap(
        workorder_id=wo.id,
        product_id=component.id,
        quantity=2.0,
        location_id=mo.location_src_id.id,
        workcenter_name=wc.display_name,
    )
    raw_move.invalidate_recordset()
    replenishment_pickings = shell_env["stock.picking"].search([("origin", "=", f"Scrap Replenish for {mo.name}")])
    assert res.get("status") == "success", f"Scrap creation failed: {res}"
    assert raw_move.product_uom_qty == 7.0, f"Expected raw demand 7.0 after scrap replenish, got {raw_move.product_uom_qty}"
    assert replenishment_pickings, "Expected internal replenishment picking was not created."
    return {
        "mo": mo.name,
        "raw_move_qty": raw_move.product_uom_qty,
        "replenishment_picking": replenishment_pickings[:1].name,
    }


def test_late_backorder_stock():
    shell_env = fresh_env()
    ProductTmpl = shell_env["product.template"]
    Location = shell_env["stock.location"]
    Quant = shell_env["stock.quant"]
    Picking = shell_env["stock.picking"]
    BackorderWizard = shell_env["stock.backorder.confirmation"]
    unit = get_unit_uom(shell_env)

    tmpl = ProductTmpl.create(
        {
            "name": "TMP LATE BO STOCK",
            "type": "consu",
            "is_storable": True,
            "uom_id": unit.id,
            "uom_po_id": unit.id,
        }
    )
    product = tmpl.product_variant_id
    internal_type = get_internal_operation_type(shell_env, ask_only=True)
    assert internal_type, "No internal operation type with Ask backorder found."
    parent_loc = internal_type.warehouse_id.lot_stock_id
    src = Location.create({"name": "TMP LATE BO SRC", "usage": "internal", "location_id": parent_loc.id})
    dst = Location.create({"name": "TMP LATE BO DST", "usage": "internal", "location_id": parent_loc.id})
    Quant._update_available_quantity(product, src, 10.0)
    picking = Picking.create(
        {
            "picking_type_id": internal_type.id,
            "location_id": src.id,
            "location_dest_id": dst.id,
            "move_ids": [
                (
                    0,
                    0,
                    {
                        "name": product.display_name,
                        "product_id": product.id,
                        "product_uom_qty": 10.0,
                        "product_uom": product.uom_id.id,
                        "location_id": src.id,
                        "location_dest_id": dst.id,
                    },
                )
            ],
        }
    )
    picking.action_confirm()
    picking.action_assign()
    for ml in picking.move_line_ids:
        ml.quantity = 4.0
    validate_action = picking.button_validate()
    assert validate_action and validate_action.get("res_model") == "stock.backorder.confirmation", "Expected stock backorder wizard."
    wizard = BackorderWizard.with_context(validate_action["context"]).create({"pick_ids": [(6, 0, picking.ids)]})
    wizard.process_cancel_backorder()
    picking.invalidate_recordset()
    assert picking.can_create_late_backorder, "Late backorder recovery button should be available after No Backorder."
    late_action = picking.action_create_late_backorder()
    late_picking = Picking.browse(late_action["res_id"])
    assert late_picking.move_ids[:1].product_uom_qty == 6.0, f"Expected late backorder qty 6.0, got {late_picking.move_ids[:1].product_uom_qty}"
    return {
        "original_picking": picking.name,
        "late_backorder": late_picking.name,
        "late_qty": late_picking.move_ids[:1].product_uom_qty,
    }


def test_late_backorder_mrp():
    shell_env = fresh_env()
    ProductTmpl = shell_env["product.template"]
    Bom = shell_env["mrp.bom"]
    Production = shell_env["mrp.production"]
    BackorderWizard = shell_env["mrp.production.backorder"]
    Quant = shell_env["stock.quant"]
    unit = get_unit_uom(shell_env)
    mrp_type = get_mrp_operation_type(shell_env, ask_only=True)
    assert mrp_type, "No manufacturing operation type with Ask backorder found."

    finished_tmpl = ProductTmpl.create(
        {"name": "TMP LATE BO FG", "type": "consu", "is_storable": True, "uom_id": unit.id, "uom_po_id": unit.id}
    )
    component_tmpl = ProductTmpl.create(
        {"name": "TMP LATE BO COMP", "type": "consu", "is_storable": True, "uom_id": unit.id, "uom_po_id": unit.id}
    )
    finished = finished_tmpl.product_variant_id
    component = component_tmpl.product_variant_id
    bom = Bom.create(
        {
            "product_tmpl_id": finished.product_tmpl_id.id,
            "product_id": finished.id,
            "product_qty": 1.0,
            "type": "normal",
            "bom_line_ids": [
                (
                    0,
                    0,
                    {
                        "product_id": component.id,
                        "product_qty": 1.0,
                        "product_uom_id": component.uom_id.id,
                    },
                )
            ],
        }
    )
    Quant._update_available_quantity(component, mrp_type.default_location_src_id, 100.0)
    mo = Production.create(
        {
            "name": "TMP LATE BO MO",
            "product_id": finished.id,
            "product_qty": 10.0,
            "product_uom_id": finished.uom_id.id,
            "bom_id": bom.id,
            "picking_type_id": mrp_type.id,
            "location_src_id": mrp_type.default_location_src_id.id,
            "location_dest_id": mrp_type.default_location_dest_id.id,
        }
    )
    mo.action_confirm()
    mo.action_assign()
    mo.qty_producing = 4.0
    for ml in mo.move_raw_ids.move_line_ids:
        ml.quantity = 4.0
        ml.picked = True
    mo_action = mo.button_mark_done()
    assert mo_action and mo_action.get("res_model") == "mrp.production.backorder", "Expected MRP backorder wizard."
    wizard = BackorderWizard.with_context(mo_action["context"]).create({"mrp_production_ids": [(6, 0, mo.ids)]})
    wizard.action_close_mo()
    mo.invalidate_recordset()
    assert mo.can_create_late_backorder, "Late backorder recovery button should be available on MO after No Backorder."
    late_action = mo.action_create_late_backorder()
    late_mo = Production.browse(late_action["res_id"])
    assert late_mo.product_qty == 6.0, f"Expected late backorder MO qty 6.0, got {late_mo.product_qty}"
    return {
        "original_mo": mo.name,
        "late_backorder_mo": late_mo.name,
        "late_qty": late_mo.product_qty,
    }


TESTS = [
    ("AUTO-01", "custom auto modules installed", test_module_presence),
    ("AUTO-02", "workcenter lock blocks second start on same machine", test_workcenter_lock),
    ("AUTO-03", "parallel split distributes planned qty by capacity", test_parallel_split_distribution),
    ("AUTO-04", "mold matrix auto-assigns mold and duration", test_mold_auto_assignment),
    ("AUTO-05", "parallel mold guard prevents duplicate mold usage", test_unique_parallel_mold_guard),
    ("AUTO-06", "mold UI helper shows only on mold-capable workorders", test_mold_ui_helper),
    ("AUTO-07", "console timer and qty logs aggregate effective quantity", test_console_timer_and_qty_logs),
    ("AUTO-08", "employee cost total computes from productivity logs", test_employee_cost_compute),
    ("AUTO-09", "overproduction sync updates MO and component demand", test_overproduction_sync),
    ("AUTO-10", "scrap wizard limits products to MO raw and finished goods", test_scrap_product_guard),
    ("AUTO-11", "scrap auto-replenish uses same-location stock when available", test_scrap_auto_replenish_same_location),
    ("AUTO-12", "scrap auto-replenish creates internal transfer when source is short", test_scrap_auto_replenish_internal_transfer),
    ("AUTO-13", "late backorder recovery recreates stock picking backorder", test_late_backorder_stock),
    ("AUTO-14", "late backorder recovery recreates MO backorder", test_late_backorder_mrp),
]


report = {
    "date": fields.Date.context_today(env.user).isoformat(),
    "database": env.cr.dbname,
    "scope": "manufacturing_shopfloor_auto",
    "cases": [],
    "summary": {},
    "reference_ui_cases": [],
}


for case_id, name, runner in TESTS:
    report["cases"].append(run_case(case_id, name, runner))


if EXISTING_UI_JSON.exists():
    try:
        ui_payload = json.loads(EXISTING_UI_JSON.read_text(encoding="utf-8"))
        for case in ui_payload.get("cases", []):
            report["reference_ui_cases"].append(
                {
                    "id": case.get("id"),
                    "name": case.get("name"),
                    "status": case.get("status"),
                    "source": str(EXISTING_UI_JSON),
                    "evidence": case.get("evidence", []),
                }
            )
    except Exception as exc:
        report["reference_ui_cases"].append(
            {
                "id": "UI-LOAD-ERROR",
                "name": "load existing mold ui report",
                "status": "failed",
                "source": str(EXISTING_UI_JSON),
                "error": str(exc),
            }
        )


all_cases = report["cases"] + report["reference_ui_cases"]
passed = len([c for c in all_cases if c.get("status") == "passed"])
failed = len([c for c in all_cases if c.get("status") != "passed"])
report["summary"] = {
    "shell_cases": len(report["cases"]),
    "reference_ui_cases": len(report["reference_ui_cases"]),
    "total_cases": len(all_cases),
    "passed": passed,
    "failed": failed,
    "overall_ok": failed == 0,
}


REPORT_JSON.write_text(json.dumps(json_safe(report), ensure_ascii=False, indent=2), encoding="utf-8")

md_lines = [
    "# Manufacturing / Shopfloor Auto UAT Suite",
    "",
    f"- Date: {report['date']}",
    f"- Database: {report['database']}",
    f"- Scope: {report['scope']}",
    "",
    "## Summary",
    "",
    f"- Shell cases: {report['summary']['shell_cases']}",
    f"- Reference UI cases: {report['summary']['reference_ui_cases']}",
    f"- Total cases: {report['summary']['total_cases']}",
    f"- Passed: {report['summary']['passed']}",
    f"- Failed: {report['summary']['failed']}",
    f"- Overall OK: {report['summary']['overall_ok']}",
    "",
    "## Shell Cases",
    "",
]

for case in report["cases"]:
    md_lines.append(f"### {case['id']} - {case['name']}")
    md_lines.append(f"- Status: {case['status']}")
    if case.get("result"):
        md_lines.append(f"- Result: `{json.dumps(case['result'], ensure_ascii=False)}`")
    if case.get("error"):
        md_lines.append(f"- Error: {case['error']}")
    md_lines.append("")

if report["reference_ui_cases"]:
    md_lines.extend(["## Reference UI Cases", ""])
    for case in report["reference_ui_cases"]:
        md_lines.append(f"### {case['id']} - {case['name']}")
        md_lines.append(f"- Status: {case['status']}")
        md_lines.append(f"- Source: `{case['source']}`")
        if case.get("evidence"):
            md_lines.append(f"- Evidence: {', '.join(case['evidence'])}")
        if case.get("error"):
            md_lines.append(f"- Error: {case['error']}")
        md_lines.append("")

REPORT_MD.write_text("\n".join(md_lines), encoding="utf-8")
