import json
from pathlib import Path


def _report_path():
    return Path("reports") / "late_backorder_recovery_uat_test_20260403_final.json"


def _jsonable_action(action):
    if isinstance(action, dict):
        cleaned = {}
        for key, value in action.items():
            if isinstance(value, (str, int, float, bool)) or value is None:
                cleaned[key] = value
            elif isinstance(value, (list, tuple, dict)):
                cleaned[key] = value
            else:
                cleaned[key] = str(value)
        return cleaned
    return action


report = {
    "database": env.cr.dbname,
    "module_name": "late_backorder_recovery",
    "module_installed": False,
    "stock": {},
    "mrp": {},
}

module = env["ir.module.module"].search(
    [("name", "=", "late_backorder_recovery")], limit=1
)
report["module_installed"] = module.state == "installed"


def run_stock_test():
    stock_env = env(context=dict(env.context, tracking_disable=True, mail_create_nolog=True, mail_notrack=True))
    ProductTmpl = stock_env["product.template"]
    Location = stock_env["stock.location"]
    Quant = stock_env["stock.quant"]
    Picking = stock_env["stock.picking"]
    PickingType = stock_env["stock.picking.type"]
    BackorderWizard = stock_env["stock.backorder.confirmation"]
    Uom = stock_env["uom.uom"]

    unit = Uom.search([("name", "in", ["Units", "Unit", "หน่วย"])], limit=1) or Uom.search([], limit=1)
    tmpl = ProductTmpl.create(
        {
            "name": "TMP Late BO Stock Product",
            "type": "consu",
            "is_storable": True,
            "uom_id": unit.id,
            "uom_po_id": unit.id,
        }
    )
    product = tmpl.product_variant_id
    internal_type = PickingType.search(
        [
            ("code", "=", "internal"),
            ("create_backorder", "=", "ask"),
            ("warehouse_id.company_id", "=", stock_env.company.id),
        ],
        limit=1,
    )
    assert internal_type, "No internal operation type with Ask backorder found."
    parent_loc = internal_type.warehouse_id.lot_stock_id
    src = Location.create(
        {"name": "TMP Late BO SRC", "usage": "internal", "location_id": parent_loc.id}
    )
    dst = Location.create(
        {"name": "TMP Late BO DST", "usage": "internal", "location_id": parent_loc.id}
    )
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
    assert (
        validate_action and validate_action.get("res_model") == "stock.backorder.confirmation"
    ), "Expected stock backorder wizard."
    wiz = BackorderWizard.with_context(validate_action["context"]).create(
        {"pick_ids": [(6, 0, picking.ids)]}
    )
    wiz.process_cancel_backorder()
    picking.invalidate_recordset()
    picking = Picking.browse(picking.id)

    result = {
        "operation_type": internal_type.name,
        "original_id": picking.id,
        "state_after_no_backorder": picking.state,
        "can_create_late_backorder_after_cancel": picking.can_create_late_backorder,
        "late_backorder_move_count": picking.late_backorder_move_count,
        "has_standard_backorder_link_before": bool(picking.backorder_ids),
    }
    late_action = picking.action_create_late_backorder()
    late_picking = Picking.browse(late_action["res_id"])
    result.update(
        {
            "late_backorder_action": _jsonable_action(late_action),
            "late_backorder_id": late_picking.id,
            "late_backorder_state": late_picking.state,
            "late_backorder_qty": late_picking.move_ids[:1].product_uom_qty if late_picking.move_ids else 0.0,
        }
    )
    picking.invalidate_recordset()
    picking = Picking.browse(picking.id)
    result.update(
        {
            "can_create_late_backorder_after_create": picking.can_create_late_backorder,
            "has_standard_backorder_link_after": bool(picking.backorder_ids),
        }
    )
    result["ok"] = (
        result["state_after_no_backorder"] == "done"
        and result["can_create_late_backorder_after_cancel"]
        and result["late_backorder_qty"] == 6.0
        and not result["can_create_late_backorder_after_create"]
        and result["has_standard_backorder_link_after"]
    )
    stock_env.cr.rollback()
    return result


def run_mrp_test():
    mrp_env = env(context=dict(env.context, tracking_disable=True, mail_create_nolog=True, mail_notrack=True))
    ProductTmpl = mrp_env["product.template"]
    Uom = mrp_env["uom.uom"]
    PickingType = mrp_env["stock.picking.type"]
    Bom = mrp_env["mrp.bom"]
    Production = mrp_env["mrp.production"]
    BackorderWizard = mrp_env["mrp.production.backorder"]
    Quant = mrp_env["stock.quant"]

    unit = Uom.search([("name", "in", ["Units", "Unit", "หน่วย"])], limit=1) or Uom.search([], limit=1)
    finished_tmpl = ProductTmpl.create(
        {
            "name": "TMP Late BO FG",
            "type": "consu",
            "is_storable": True,
            "uom_id": unit.id,
            "uom_po_id": unit.id,
        }
    )
    component_tmpl = ProductTmpl.create(
        {
            "name": "TMP Late BO COMP",
            "type": "consu",
            "is_storable": True,
            "uom_id": unit.id,
            "uom_po_id": unit.id,
        }
    )
    finished = finished_tmpl.product_variant_id
    component = component_tmpl.product_variant_id
    mrp_type = PickingType.search(
        [
            ("code", "=", "mrp_operation"),
            ("create_backorder", "=", "ask"),
            ("warehouse_id.company_id", "=", mrp_env.company.id),
        ],
        limit=1,
    )
    assert mrp_type, "No manufacturing operation type with Ask backorder found."

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
    assert (
        mo_action and mo_action.get("res_model") == "mrp.production.backorder"
    ), "Expected MRP backorder wizard."
    mo_wiz = BackorderWizard.with_context(mo_action["context"]).create(
        {"mrp_production_ids": [(6, 0, mo.ids)]}
    )
    mo_wiz.action_close_mo()
    mo.invalidate_recordset()
    mo = Production.browse(mo.id)

    result = {
        "operation_type": mrp_type.name,
        "original_id": mo.id,
        "state_after_no_backorder": mo.state,
        "qty_produced": mo.qty_produced,
        "remaining_qty": mo.late_backorder_remaining_qty,
        "can_create_late_backorder_after_cancel": mo.can_create_late_backorder,
        "has_late_backorder_link_before": bool(mo.late_backorder_ids),
    }
    late_mo_action = mo.action_create_late_backorder()
    late_mo = Production.browse(late_mo_action["res_id"])
    result.update(
        {
            "late_backorder_action": _jsonable_action(late_mo_action),
            "late_backorder_id": late_mo.id,
            "late_backorder_state": late_mo.state,
            "late_backorder_qty": late_mo.product_qty,
        }
    )
    mo.invalidate_recordset()
    mo = Production.browse(mo.id)
    result.update(
        {
            "can_create_late_backorder_after_create": mo.can_create_late_backorder,
            "has_late_backorder_link_after": bool(mo.late_backorder_ids),
        }
    )
    result["ok"] = (
        result["state_after_no_backorder"] == "done"
        and result["qty_produced"] == 4.0
        and result["remaining_qty"] == 6.0
        and result["can_create_late_backorder_after_cancel"]
        and result["late_backorder_qty"] == 6.0
        and not result["can_create_late_backorder_after_create"]
        and result["has_late_backorder_link_after"]
    )
    mrp_env.cr.rollback()
    return result


report["stock"] = run_stock_test()
report["mrp"] = run_mrp_test()
report["overall_ok"] = (
    report["module_installed"]
    and report["stock"].get("ok")
    and report["mrp"].get("ok")
)

output = _report_path()
output.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
print(str(output))
