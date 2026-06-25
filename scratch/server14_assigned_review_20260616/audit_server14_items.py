import json
from pathlib import Path

import requests


URL = "http://10.0.0.14"
DB = "goldmints_uat"
USER = "admin"
PASSWORD = "365@gmp"


def connect():
    session = requests.Session()
    response = session.post(
        f"{URL}/web/session/authenticate",
        json={
            "jsonrpc": "2.0",
            "method": "call",
            "params": {"db": DB, "login": USER, "password": PASSWORD},
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("error"):
        raise RuntimeError(payload["error"])
    uid = (payload.get("result") or {}).get("uid")
    if not uid:
        raise RuntimeError("Authentication failed")
    return uid, session


def call(session, uid, model, method, *args, **kwargs):
    response = session.post(
        f"{URL}/web/dataset/call_kw/{model}/{method}",
        json={
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": model,
                "method": method,
                "args": list(args),
                "kwargs": kwargs,
            },
        },
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("error"):
        raise RuntimeError(json.dumps(payload["error"], ensure_ascii=False, default=str))
    return payload.get("result")


def search_read(models, uid, model, domain, fields=None, limit=None, order=None):
    kwargs = {}
    if fields:
        kwargs["fields"] = fields
    if limit:
        kwargs["limit"] = limit
    if order:
        kwargs["order"] = order
    return call(models, uid, model, "search_read", domain, **kwargs)


def fields_containing(models, uid, model, tokens):
    try:
        data = call(models, uid, model, "fields_get", [], attributes=["string", "type", "relation", "store"])
    except Exception as exc:
        return {"error": str(exc)}
    out = {}
    for name, meta in data.items():
        hay = f"{name} {meta.get('string') or ''}".lower()
        if any(token.lower() in hay for token in tokens):
            out[name] = meta
    return out


def safe_read(models, uid, model, domain, wanted_fields, limit=10, order=None):
    field_defs = call(models, uid, model, "fields_get", [], attributes=["string", "type"])
    valid = [field for field in wanted_fields if field in field_defs]
    return search_read(models, uid, model, domain, valid, limit=limit, order=order)


def read_moves(models, uid, move_ids):
    if not move_ids:
        return []
    return safe_read(
        models,
        uid,
        "stock.move",
        [("id", "in", move_ids)],
        [
            "id",
            "name",
            "product_id",
            "product_uom_qty",
            "quantity",
            "reserved_availability",
            "product_uom",
            "state",
            "picking_id",
            "location_id",
            "location_dest_id",
            "raw_material_production_id",
            "production_id",
            "created_production_id",
            "origin",
        ],
        limit=200,
        order="id",
    )


def main():
    uid, models = connect()
    result = {"uid": uid}

    task_ids = [1673, 1675, 1689, 1690, 1693, 1694, 1697, 1698, 1701]
    result["tasks"] = safe_read(
        models,
        uid,
        "project.task",
        [("id", "in", task_ids)],
        [
            "id",
            "name",
            "stage_id",
            "x_studio_module",
            "x_studio_function",
            "x_studio_test_steps",
            "x_studio_test_step",
            "x_studio_expected_result",
            "description",
            "message_attachment_count",
        ],
        limit=50,
        order="id",
    )

    modules = [
        "account_asset_customization",
        "vendor_billing_note",
        "purchase_order_status_report",
        "mrp_mps_manufacturing_type",
        "mrp_auto_merge",
        "sale_tax_invoice",
        "sale_auto_confirm_invoice",
        "auto_asset_from_vendor_bill",
    ]
    result["modules"] = search_read(
        models,
        uid,
        "ir.module.module",
        [("name", "in", modules)],
        ["name", "state", "latest_version"],
        limit=100,
        order="name",
    )

    result["field_checks"] = {
        "account.asset": fields_containing(models, uid, "account.asset", ["last", "depreciation", "post"]),
        "account.move": fields_containing(models, uid, "account.move", ["print", "printed", "billing", "vendor_billing"]),
        "sale.order": fields_containing(models, uid, "sale.order", ["print", "printed"]),
        "product.template": fields_containing(models, uid, "product.template", ["produce", "lead", "delay", "mfg", "manufact"]),
        "product.product": fields_containing(models, uid, "product.product", ["produce", "lead", "delay", "mfg", "manufact"]),
        "stock.picking": fields_containing(models, uid, "stock.picking", ["production", "manufact", "mo", "origin"]),
        "stock.move": fields_containing(models, uid, "stock.move", ["production", "manufact", "raw", "origin"]),
        "purchase.order.status.report.wizard.line": fields_containing(models, uid, "purchase.order.status.report.wizard.line", ["asset", "bill", "credit", "billing", "move"]),
    }

    result["asset_custom_views"] = search_read(
        models,
        uid,
        "ir.ui.view",
        [
            ("model", "=", "account.asset"),
            "|",
            ("arch_db", "ilike", "last_post_depreciation_date"),
            ("name", "ilike", "last post"),
        ],
        ["id", "name", "model", "type", "inherit_id", "active"],
        limit=20,
        order="id",
    )
    result["sample_assets"] = safe_read(
        models,
        uid,
        "account.asset",
        [],
        ["id", "name", "display_name", "state", "last_post_depreciation_date", "original_value", "book_value"],
        limit=10,
        order="id desc",
    )

    result["asset_receipt_reports"] = search_read(
        models,
        uid,
        "ir.actions.report",
        [
            ("model", "=", "stock.picking"),
            "|",
            "|",
            ("name", "ilike", "asset"),
            ("name", "ilike", "สินทรัพย์"),
            ("name", "ilike", "ทรัพย์สิน"),
        ],
        ["id", "name", "model", "report_name", "report_type", "binding_model_id"],
        limit=50,
        order="id",
    )

    result["stock_reports_receipt"] = search_read(
        models,
        uid,
        "ir.actions.report",
        [("model", "=", "stock.picking")],
        ["id", "name", "model", "report_name", "report_type", "binding_model_id"],
        limit=80,
        order="id",
    )

    mo_names = ["GMP/MOPL/00167", "GMP/MOPL/00169", "GMP/MOPL/00170"]
    picking_names = ["GMP/TRPL/00057", "GMP/TRPL/00059"]
    result["sample_mos"] = safe_read(
        models,
        uid,
        "mrp.production",
        [("name", "in", mo_names)],
        [
            "id",
            "name",
            "product_id",
            "product_qty",
            "product_uom_id",
            "state",
            "origin",
            "date_start",
            "date_finished",
            "date_deadline",
            "move_raw_ids",
            "picking_ids",
            "manufacturing_type",
        ],
        limit=20,
        order="name",
    )
    result["sample_pickings"] = safe_read(
        models,
        uid,
        "stock.picking",
        [("name", "in", picking_names)],
        [
            "id",
            "name",
            "state",
            "origin",
            "picking_type_id",
            "location_id",
            "location_dest_id",
            "scheduled_date",
            "manufacturing_type",
            "move_ids",
            "move_ids_without_package",
            "move_line_ids",
            "production_id",
        ],
        limit=20,
        order="name",
    )
    move_ids = []
    for mo in result["sample_mos"]:
        move_ids += mo.get("move_raw_ids") or []
    for picking in result["sample_pickings"]:
        move_ids += picking.get("move_ids") or []
        move_ids += picking.get("move_ids_without_package") or []
    result["sample_moves"] = read_moves(models, uid, sorted(set(move_ids)))

    result["po_status_wizard_models"] = {}
    for model in ["purchase.order.status.report.wizard", "purchase.order.status.report.wizard.line"]:
        try:
            result["po_status_wizard_models"][model] = fields_containing(
                models, uid, model, ["asset", "bill", "credit", "billing", "selected", "move", "fixed"]
            )
        except Exception as exc:
            result["po_status_wizard_models"][model] = {"error": str(exc)}

    out = Path(__file__).with_name("audit_server14_items_result.json")
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
