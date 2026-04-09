import json
import traceback
from pathlib import Path

from odoo import api, fields


DATE_TAG = "20260406"
REPORT_JSON = Path("reports") / f"mrp_scrap_landed_cost_uat_{DATE_TAG}.json"
REPORT_MD = Path("reports") / f"mrp_scrap_landed_cost_uat_{DATE_TAG}.md"


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


def get_unit_uom(shell_env):
    return shell_env["uom.uom"].search([("uom_type", "=", "reference")], limit=1)


def build_temp_flow(shell_env):
    Product = shell_env["product.product"]
    Category = shell_env["product.category"]
    Bom = shell_env["mrp.bom"]
    Production = shell_env["mrp.production"]
    Scrap = shell_env["stock.scrap"]
    Quant = shell_env["stock.quant"]

    company = shell_env.company
    unit = get_unit_uom(shell_env)
    category = Category.search(
        [
            ("property_valuation", "=", "real_time"),
            ("property_cost_method", "in", ["fifo", "average"]),
        ],
        limit=1,
    )
    assert category, "No real_time FIFO/Average category found for landed cost test."
    mrp_type = shell_env["stock.picking.type"].search([("code", "=", "mrp_operation")], limit=1)
    assert mrp_type, "No manufacturing operation type found."

    raw = Product.create(
        {
            "name": "TMP SCRAP LC RAW",
            "type": "consu",
            "is_storable": True,
            "uom_id": unit.id,
            "uom_po_id": unit.id,
            "categ_id": category.id,
            "standard_price": 10.0,
            "company_id": company.id,
        }
    )
    finished = Product.create(
        {
            "name": "TMP SCRAP LC FG",
            "type": "consu",
            "is_storable": True,
            "uom_id": unit.id,
            "uom_po_id": unit.id,
            "categ_id": category.id,
            "standard_price": 100.0,
            "company_id": company.id,
        }
    )

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
                        "product_id": raw.id,
                        "product_qty": 1.0,
                        "product_uom_id": raw.uom_id.id,
                    },
                )
            ],
        }
    )

    Quant._update_available_quantity(raw, mrp_type.default_location_src_id, 20.0)

    mo = Production.create(
        {
            "name": "TMP SCRAP LC MO",
            "product_id": finished.id,
            "product_qty": 5.0,
            "product_uom_id": finished.uom_id.id,
            "bom_id": bom.id,
            "picking_type_id": mrp_type.id,
            "location_src_id": mrp_type.default_location_src_id.id,
            "location_dest_id": mrp_type.default_location_dest_id.id,
        }
    )
    mo.action_confirm()
    mo.action_assign()

    raw_move = mo.move_raw_ids.filtered(lambda m: m.product_id == raw)[:1]
    assert raw_move, "Raw move missing on temporary MO."

    scrap = Scrap.create(
        {
            "product_id": raw.id,
            "scrap_qty": 1.0,
            "product_uom_id": raw.uom_id.id,
            "location_id": mrp_type.default_location_src_id.id,
            "scrap_location_id": shell_env["stock.location"].search([("scrap_location", "=", True)], limit=1).id,
            "production_id": mo.id,
            "company_id": company.id,
        }
    )
    scrap.action_validate()

    mo.qty_producing = mo.product_qty
    for ml in mo.move_raw_ids.move_line_ids:
        ml.quantity = mo.product_qty
        ml.picked = True
    mo.with_context(skip_consumption=True).button_mark_done()

    mo.invalidate_recordset()
    scrap.invalidate_recordset()

    failure_messages = shell_env["mail.message"].search(
        [
            ("model", "=", "mrp.production"),
            ("res_id", "=", mo.id),
            ("body", "ilike", "Auto-Allocate Scrap Cost Failed"),
        ],
        order="id desc",
    )

    direct_error = None
    try:
        mo._auto_allocate_scrap_cost()
    except Exception as exc:
        direct_error = {
            "type": exc.__class__.__name__,
            "message": str(exc),
        }

    landed_costs = shell_env["stock.landed.cost"].search(
        [("target_model", "=", "manufacturing"), ("mrp_production_ids", "in", mo.ids)]
    )

    return {
        "test_category": {
            "id": category.id,
            "name": category.display_name,
            "valuation": category.property_valuation,
            "cost_method": category.property_cost_method,
        },
        "temporary_mo": mo.name,
        "temporary_mo_state": mo.state,
        "temporary_scrap": scrap.name,
        "temporary_scrap_state": scrap.state,
        "temporary_scrap_landed_cost_id": scrap.landed_cost_id.id or None,
        "cost_finalized": bool(mo.cost_finalized),
        "failure_messages": failure_messages.mapped("body"),
        "direct_error": direct_error,
        "created_landed_cost_names": landed_costs.mapped("name"),
    }


report = {
    "date": fields.Date.context_today(env.user).isoformat(),
    "database": env.cr.dbname,
    "module": "mrp_scrap_landed_cost",
    "status": "pending",
    "checks": {},
    "flow_test": {},
    "risks": [],
}

try:
    shell_env = fresh_env()
    report["checks"]["module_installed"] = bool(
        shell_env["ir.module.module"].search(
            [("name", "=", "mrp_scrap_landed_cost"), ("state", "=", "installed")], limit=1
        )
    )
    report["checks"]["dependency_mrp_landed_costs_installed"] = bool(
        shell_env["ir.module.module"].search(
            [("name", "=", "mrp_landed_costs"), ("state", "=", "installed")], limit=1
        )
    )
    report["checks"]["legacy_scrap_record_model_exists"] = "mrp.scrap.record" in shell_env
    report["checks"]["configured_service_product"] = bool(
        shell_env.company.mrp_scrap_landed_cost_product_id
    )
    if shell_env.company.mrp_scrap_landed_cost_product_id:
        svc = shell_env.company.mrp_scrap_landed_cost_product_id
        report["checks"]["service_product"] = {
            "id": svc.id,
            "name": svc.display_name,
            "type": svc.type,
            "landed_cost_ok": bool(svc.landed_cost_ok),
            "is_scrap_cost": bool(svc.product_tmpl_id.is_scrap_cost),
        }

    report["flow_test"] = build_temp_flow(shell_env)

    if (
        report["checks"]["module_installed"]
        and report["checks"]["dependency_mrp_landed_costs_installed"]
        and report["flow_test"]["cost_finalized"]
        and report["flow_test"]["created_landed_cost_names"]
    ):
        report["status"] = "passed"
    else:
        report["status"] = "failed"

    if not report["flow_test"]["cost_finalized"]:
        report["risks"].append(
            "MO can complete while scrap cost auto-allocation does not finalize, because button_mark_done swallows exceptions."
        )
    if not report["flow_test"]["created_landed_cost_names"]:
        report["risks"].append(
            "No manufacturing landed cost is created in the tested flow."
        )
    if not report["checks"]["legacy_scrap_record_model_exists"]:
        report["risks"].append(
            "Legacy model 'mrp.scrap.record' is absent in UAT. The module now has to rely on stock.scrap only."
        )

except Exception as exc:
    report["status"] = "error"
    report["error"] = {
        "type": exc.__class__.__name__,
        "message": str(exc),
        "traceback": traceback.format_exc(),
    }
finally:
    REPORT_JSON.write_text(
        json.dumps(json_safe(report), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    lines = [
        "# MRP Scrap Landed Cost UAT",
        "",
        f"- Date: {report['date']}",
        f"- Database: {report['database']}",
        f"- Status: {report['status']}",
        "",
        "## Checks",
    ]
    for key, value in report.get("checks", {}).items():
        lines.append(f"- {key}: `{json_safe(value)}`")
    lines.extend(
        [
            "",
            "## Flow Test",
        ]
    )
    for key, value in report.get("flow_test", {}).items():
        lines.append(f"- {key}: `{json_safe(value)}`")
    if report.get("risks"):
        lines.extend(["", "## Risks"])
        for risk in report["risks"]:
            lines.append(f"- {risk}")
    if report.get("error"):
        lines.extend(
            [
                "",
                "## Error",
                f"- type: `{report['error']['type']}`",
                f"- message: `{report['error']['message']}`",
            ]
        )
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    env.cr.rollback()
