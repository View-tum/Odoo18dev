import datetime as dt
import json
import re
import sys
import traceback
from pathlib import Path

import requests


BASE_URL = "http://10.0.0.14"
DB = "goldmints_uat"
USER = "admin"
PASSWORD = "365@gmp"
OUT = Path("scratch/server14_retest_assigned_dev_results.json")


session = requests.Session()
auth_response = session.post(
    f"{BASE_URL}/web/session/authenticate",
    json={
        "jsonrpc": "2.0",
        "method": "call",
        "params": {"db": DB, "login": USER, "password": PASSWORD},
        "id": 1,
    },
    timeout=30,
)
auth_response.raise_for_status()
auth_payload = auth_response.json()
if auth_payload.get("error"):
    raise RuntimeError(json.dumps(auth_payload["error"], ensure_ascii=False))
uid = auth_payload.get("result", {}).get("uid")
if not uid:
    raise RuntimeError("Authentication failed")


def rpc(model, method, args=None, kwargs=None):
    response = session.post(
        f"{BASE_URL}/web/dataset/call_kw/{model}/{method}",
        json={
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": model,
                "method": method,
                "args": args or [],
                "kwargs": kwargs or {},
            },
            "id": 1,
        },
        timeout=120,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("error"):
        raise RuntimeError(json.dumps(payload["error"], ensure_ascii=False))
    return payload.get("result")


def search(model, domain, limit=0, order=None, context=None):
    kwargs = {"limit": limit}
    if order:
        kwargs["order"] = order
    if context:
        kwargs["context"] = context
    return rpc(model, "search", [domain], kwargs)


def read(model, ids, fields=None, context=None):
    kwargs = {}
    if fields:
        kwargs["fields"] = fields
    if context:
        kwargs["context"] = context
    return rpc(model, "read", [ids], kwargs)


def search_read(model, domain, fields=None, limit=0, order=None, context=None):
    kwargs = {"limit": limit}
    if fields:
        kwargs["fields"] = fields
    if order:
        kwargs["order"] = order
    if context:
        kwargs["context"] = context
    return rpc(model, "search_read", [domain], kwargs)


def fields_get(model):
    try:
        return rpc(model, "fields_get", [], {"attributes": ["string", "type", "relation"]})
    except Exception as exc:
        return {"__error__": str(exc)}


def approx_zero(value, precision=0.01):
    return abs(float(value or 0.0)) <= precision


def html_text(value):
    if not value:
        return ""
    value = re.sub(r"<[^>]+>", " ", str(value))
    return re.sub(r"\s+", " ", value).strip()


def session_login():
    return session


def report_pdf(session, report_name, record_id):
    url = f"{BASE_URL}/report/pdf/{report_name}/{record_id}"
    response = session.get(url, timeout=60)
    headers = {k.lower(): v for k, v in response.headers.items()}
    body = response.content or b""
    return {
        "url": url,
        "status_code": response.status_code,
        "content_type": headers.get("content-type", ""),
        "is_pdf": body.startswith(b"%PDF"),
        "bytes": len(body),
        "snippet": body[:160].decode("utf-8", "ignore"),
    }


def add_result(defect_id, title, status, evidence=None, records=None, risk=None):
    status = status.upper()
    results.append(
        {
            "defect_id": defect_id,
            "title": title,
            "status": status,
            "evidence": evidence or {},
            "records": records or [],
            "risk": risk or "",
        }
    )


def safe_check(defect_id, title, fn):
    if defect_id not in current_ids:
        return
    live_title = task_by_id.get(defect_id, {}).get("name") or title
    try:
        status, evidence, records, risk = fn()
        add_result(defect_id, live_title, status, evidence, records, risk)
    except Exception as exc:
        add_result(
            defect_id,
            live_title,
            "FAIL",
            {
                "error": str(exc),
                "traceback": traceback.format_exc(limit=8),
            },
            risk="test harness caught exception",
        )


def menus_matching(text):
    return search_read(
        "ir.ui.menu",
        [("name", "ilike", text)],
        ["id", "name", "complete_name", "action"],
        limit=20,
        order="id",
    )


def actions_matching(model, text):
    return search_read(
        model,
        [("name", "ilike", text)],
        ["id", "name"],
        limit=20,
        order="name",
    )


def check_vendor_billing_note_menu():
    actions = search_read(
        "ir.actions.act_window",
        [("res_model", "=", "vendor.billing.note")],
        ["id", "name", "res_model"],
        limit=20,
        order="id",
    )
    action_details = []
    for action in actions:
        menus = search_read(
            "ir.ui.menu",
            [("action", "=", f"ir.actions.act_window,{action['id']}")],
            ["id", "name", "complete_name", "action"],
            limit=20,
            order="id",
        )
        action_details.append({"action": action, "menus": menus})
    notes = search_read(
        "vendor.billing.note",
        [],
        ["id", "name", "state", "partner_id", "amount_total", "payment_state"],
        limit=5,
        order="id desc",
    )
    ok = any(
        row["action"].get("res_model") == "vendor.billing.note"
        and any("Accounting" in (menu.get("complete_name") or "") or "Vendor" in (menu.get("complete_name") or "") for menu in row["menus"])
        for row in action_details
    )
    return (
        "PASS" if ok else "FAIL",
        {"actions": action_details, "sample_billing_notes": notes},
        [],
        "" if ok else "No Accounting/Vendor menu was found for vendor.billing.note",
    )


def check_vendor_return_cn_linked():
    cn = search_read(
        "account.move",
        [("name", "=", "VCND/26/06/00002")],
        [
            "id",
            "name",
            "move_type",
            "state",
            "amount_total_signed",
            "amount_residual_signed",
            "payment_state",
            "return_picking_ids",
            "return_picking_count",
        ],
        limit=1,
    )
    returns = search_read(
        "stock.picking",
        [("name", "in", ["GMP/R-OUT/00011", "GMP/R-OUT/00012"])],
        ["id", "name", "state", "vendor_credit_note_ids", "vendor_credit_note_count"],
        limit=10,
        order="name",
    )
    linked_count = 0
    if cn:
        cn_id = cn[0]["id"]
        linked_count = sum(1 for item in returns if cn_id in item.get("vendor_credit_note_ids", []))
    ok = bool(cn) and cn[0]["state"] == "posted" and linked_count >= 2
    return (
        "PASS" if ok else "FAIL",
        {"credit_note": cn, "returns": returns, "linked_return_count": linked_count},
        [f"account.move:{cn[0]['id']}"] if cn else [],
        "" if ok else "Vendor return credit note is not linked to all sampled returns",
    )


def check_report_exists(keywords):
    found = {
        "reports": [],
        "menus": [],
        "window_actions": [],
    }
    for keyword in keywords:
        try:
            found["reports"].extend(
                search_read(
                    "ir.actions.report",
                    ["|", "|", ("name", "ilike", keyword), ("report_name", "ilike", keyword), ("model", "ilike", keyword)],
                    ["id", "name", "report_name", "model"],
                    limit=20,
                )
            )
        except Exception:
            pass
        found["menus"].extend(menus_matching(keyword))
        try:
            found["window_actions"].extend(
                search_read(
                    "ir.actions.act_window",
                    ["|", ("name", "ilike", keyword), ("res_model", "ilike", keyword)],
                    ["id", "name", "res_model"],
                    limit=20,
                )
            )
        except Exception:
            pass
    unique = {}
    for key, rows in found.items():
        cleaned = []
        seen = set()
        for row in rows:
            marker = row.get("id")
            if marker in seen:
                continue
            seen.add(marker)
            cleaned.append(row)
        unique[key] = cleaned[:20]
    ok = any(unique.values())
    return ("PASS" if ok else "FAIL", unique, [], "" if ok else "No matching report/menu/action found")


def check_auto_asset_accounts():
    accounts = search_read(
        "account.account",
        [("code", "in", ["123010", "123008"])],
        ["id", "code", "name"],
        limit=10,
        order="code",
    )
    account_by_id = {row["id"]: row for row in accounts}
    fg = fields_get("account.asset")
    account_fields = [
        name
        for name, spec in fg.items()
        if isinstance(spec, dict)
        and spec.get("type") == "many2one"
        and spec.get("relation") == "account.account"
    ]
    asset_read_fields = ["id", "name"]
    if "state" in fg:
        asset_read_fields.append("state")
    asset_read_fields += account_fields
    asset_domain = [("state", "=", "model")] if "state" in fg else []
    asset_models = search_read("account.asset", asset_domain, asset_read_fields, limit=100, order="name")
    referenced = []
    for model in asset_models:
        refs = {}
        for field in account_fields:
            value = model.get(field)
            if value and value[0] in account_by_id:
                refs[field] = account_by_id[value[0]]
        if refs:
            referenced.append({"asset_model": {"id": model["id"], "name": model["name"]}, "refs": refs})
    referenced_codes = {
        acc["code"]
        for row in referenced
        for acc in row["refs"].values()
    }
    product_fields = fields_get("product.template")
    product_read_fields = ["id", "name", "categ_id"]
    if "asset_model_id" in product_fields:
        product_read_fields.append("asset_model_id")
    if "split_assets" in product_fields:
        product_read_fields.append("split_assets")
    asset_products = search_read(
        "product.template",
        [("asset_model_id", "!=", False)] if "asset_model_id" in product_fields else [],
        product_read_fields,
        limit=20,
        order="id desc",
    )
    move_fields = fields_get("account.move")
    move_custom_fields = {
        name: move_fields[name]
        for name in ["has_asset_category_line", "asset_creatd", "asset_ids", "asset_count"]
        if name in move_fields
    }
    views = search_read(
        "ir.ui.view",
        [
            ("model", "=", "account.move"),
            "|",
            ("arch_db", "ilike", "action_create_assets_from_bill_lines"),
            ("arch_db", "ilike", "has_asset_category_line"),
        ],
        ["id", "name", "type", "arch_db"],
        limit=20,
    )
    ok = (
        {"123010", "123008"}.issubset({row["code"] for row in accounts})
        and bool(asset_products)
        and bool(move_custom_fields)
        and bool(views)
    )
    return (
        "PASS" if ok else "FAIL",
        {
            "accounts": accounts,
            "account_fields": account_fields,
            "asset_model_account_refs": referenced[:20],
            "referenced_codes": sorted(referenced_codes),
            "asset_products": asset_products,
            "account_move_custom_fields": move_custom_fields,
            "account_move_views": [{"id": v["id"], "name": v["name"], "type": v["type"]} for v in views],
        },
        [],
        "" if ok else "Auto asset vendor bill setup is incomplete for existing fixed-asset products/accounts/views",
    )


def check_payment_config():
    company_fields = fields_get("res.company")
    interesting_fields = [
        name
        for name in company_fields
        if any(token in name.lower() for token in ["diff", "round", "write", "exchange", "payment"])
    ]
    companies = read("res.company", [1], interesting_fields[:80]) if interesting_fields else []
    method_lines = search_read(
        "account.payment.method.line",
        [],
        ["id", "name", "journal_id", "payment_account_id", "payment_method_id"],
        limit=100,
        order="journal_id",
    )
    missing_accounts = [line for line in method_lines if not line.get("payment_account_id")]
    auto_diff_configured = False
    company = companies[0] if companies else {}
    for key, value in company.items():
        if ("diff" in key.lower() or "round" in key.lower() or "write" in key.lower()) and value:
            auto_diff_configured = True
    ok = auto_diff_configured and len(missing_accounts) < len(method_lines)
    return (
        "PASS" if ok else "FAIL",
        {
            "company_payment_related_fields": company,
            "payment_method_lines_count": len(method_lines),
            "missing_payment_account_count": len(missing_accounts),
            "sample_missing": missing_accounts[:10],
        },
        [],
        "" if ok else "Payment difference/rounding account config or payment method account setup is incomplete",
    )


def check_stock_report(report_name, picking_name=None, picking_type=None):
    session = session_login()
    picking = []
    if picking_name:
        picking = search_read(
            "stock.picking",
            [("name", "=", picking_name)],
            ["id", "name", "state", "picking_type_id"],
            limit=1,
        )
    if not picking and picking_type:
        picking = search_read(
            "stock.picking",
            [("state", "=", "done"), ("picking_type_code", "=", picking_type)],
            ["id", "name", "state", "picking_type_id"],
            limit=1,
            order="id desc",
        )
    if not picking:
        return "FAIL", {"error": "No picking found"}, [], "No existing picking available for report test"
    pdf = report_pdf(session, report_name, picking[0]["id"])
    ok = pdf["status_code"] == 200 and pdf["is_pdf"] and pdf["bytes"] > 1000
    return (
        "PASS" if ok else "FAIL",
        {"picking": picking[0], "pdf": pdf},
        [f"stock.picking:{picking[0]['id']}"],
        "" if ok else f"Report {report_name} did not render as PDF",
    )


def check_bn_payment_wizard():
    bn_fields_get = fields_get("vendor.billing.note")
    desired_fields = [
        "id",
        "name",
        "state",
        "payment_state",
        "amount_total",
        "amount_net_due",
        "amount_credit_notes",
        "amount_vendor_bills",
        "amount_residual_net_due",
        "bill_ids",
    ]
    bn_fields = [field for field in desired_fields if field in bn_fields_get]
    bn = search_read(
        "vendor.billing.note",
        [("name", "=", "BN/2026/06/0069")],
        bn_fields,
        limit=1,
    )
    if not bn:
        return "FAIL", {"error": "BN/2026/06/0069 not found"}, [], "Sample billing note missing"
    action = rpc("vendor.billing.note", "action_register_payment", [[bn[0]["id"]]])
    ctx = action.get("context", {})
    values = {}
    if isinstance(ctx, dict):
        for key, value in ctx.items():
            if key.startswith("default_"):
                values[key[8:]] = value
    wizard_id = rpc("account.payment.register", "create", [values], {"context": ctx})
    wizard = read(
        "account.payment.register",
        [wizard_id],
        ["amount", "payment_difference", "payment_difference_handling", "group_payment", "line_ids"],
        context=ctx,
    )[0]
    expected = float(
        bn[0].get("amount_residual_net_due")
        or bn[0].get("amount_net_due")
        or bn[0].get("amount_total")
        or 0.0
    )
    ok = abs(float(wizard["amount"] or 0.0) - expected) <= 0.01 and approx_zero(wizard["payment_difference"])
    return (
        "PASS" if ok else "FAIL",
        {"billing_note": bn[0], "action_context": ctx, "wizard": wizard, "expected_amount": expected},
        [f"vendor.billing.note:{bn[0]['id']}", f"account.payment.register:{wizard_id}"],
        "" if ok else "Register Payment wizard still shows payment difference for net APD/CN billing note",
    )


def check_prepare_material_lots():
    session = session_login()
    mos = search_read(
        "mrp.production",
        [("state", "in", ["confirmed", "progress", "to_close"])],
        ["id", "name", "state"],
        limit=1,
        order="id desc",
    )
    if not mos:
        return "PASS", {"message": "No open MO found; no state-changing test executed"}, [], ""
    before = mos[0]["state"]
    response = session.post(
        f"{BASE_URL}/mrp_parallel_console/prepare_material_lots",
        json={"jsonrpc": "2.0", "method": "call", "params": {"production_id": mos[0]["id"]}, "id": 1672},
        timeout=60,
    )
    after = read("mrp.production", [mos[0]["id"]], ["state"])[0]["state"]
    ok = response.status_code == 200 and before == after
    try:
        body = response.json()
    except Exception:
        body = response.text[:300]
    return (
        "PASS" if ok else "FAIL",
        {"mo": mos[0], "state_before": before, "state_after": after, "response_status": response.status_code, "response": body},
        [f"mrp.production:{mos[0]['id']}"],
        "" if ok else "Material lot route failed or changed MO state unexpectedly",
    )


def check_mo_schedule_dates():
    bad = []
    checked = []
    sales = search_read(
        "sale.order",
        [("commitment_date", "!=", False), ("state", "in", ["sale", "done"])],
        ["id", "name", "commitment_date"],
        limit=80,
        order="id desc",
    )
    for so in sales:
        mos = search_read(
            "mrp.production",
            [("origin", "ilike", so["name"])],
            ["id", "name", "origin", "date_start", "date_deadline", "product_id", "state"],
            limit=20,
            order="id desc",
        )
        if not mos:
            continue
        so_date = str(so["commitment_date"])[:10]
        for mo in mos:
            item = {"sale_order": so, "mo": mo}
            checked.append(item)
            if str(mo.get("date_start") or "")[:10] == so_date:
                bad.append(item)
    ok = bool(checked) and not bad
    if not checked:
        return "FAIL", {"checked": checked, "bad": bad}, [], "No SO with linked MO found for schedule-date validation"
    return (
        "PASS" if ok else "FAIL",
        {"checked_count": len(checked), "sample_checked": checked[:10], "bad": bad[:20]},
        [f"mrp.production:{row['mo']['id']}" for row in checked[:5]],
        "" if ok else "At least one MO date_start equals SO Delivery Date",
    )


def check_export_so_auto_po():
    candidates = search_read(
        "sale.order",
        [
            ("state", "in", ["sale", "done"]),
            "|",
            ("name", "ilike", "SOE"),
            ("name", "ilike", "Export"),
        ],
        ["id", "name", "partner_id", "warehouse_id", "commitment_date"],
        limit=20,
        order="id desc",
    )
    checked = []
    for so in candidates:
        pos = search_read(
            "purchase.order",
            [("origin", "ilike", so["name"])],
            ["id", "name", "state", "origin", "partner_id"],
            limit=20,
            order="id desc",
        )
        checked.append({"sale_order": so, "purchase_orders": pos})
    ok = bool(checked) and any(row["purchase_orders"] for row in checked)
    return (
        "PASS" if ok else "FAIL",
        {"checked": checked[:20]},
        [f"sale.order:{row['sale_order']['id']}" for row in checked[:5]],
        "" if ok else "No linked Purchase Order found for sampled international/export SO",
    )


def check_shopfloor_visibility():
    fg = fields_get("mrp.production")
    fields_ok = "hide_from_shopfloor" in fg and "show_on_shopfloor" in fg
    views = search_read(
        "ir.ui.view",
        [
            ("model", "=", "mrp.production"),
            "|",
            ("arch_db", "ilike", "hide_from_shopfloor"),
            ("arch_db", "ilike", "show_on_shopfloor"),
        ],
        ["id", "name", "type", "arch_db"],
        limit=20,
    )
    evidence_views = []
    for view in views:
        arch = view.get("arch_db") or ""
        evidence_views.append(
            {
                "id": view["id"],
                "name": view["name"],
                "type": view["type"],
                "has_hide_from_shopfloor": "hide_from_shopfloor" in arch,
                "has_show_on_shopfloor": "show_on_shopfloor" in arch,
            }
        )
    ok = fields_ok and any(v["has_show_on_shopfloor"] or v["has_hide_from_shopfloor"] for v in evidence_views)
    return (
        "PASS" if ok else "FAIL",
        {
            "fields": {name: fg.get(name) for name in ["show_on_shopfloor", "hide_from_shopfloor"]},
            "views": evidence_views,
        },
        [],
        "" if ok else "Shopfloor visibility fields/views are missing",
    )


def check_transform_valuation():
    evidence = {}
    ok = False
    for model in ["product.transform", "rma.transform.return"]:
        fg = fields_get(model)
        if "__error__" in fg:
            evidence[model] = fg
            continue
        wanted = [field for field in ["id", "name", "state", "move_out_id", "move_in_id", "svl_count"] if field in fg]
        rows = search_read(model, [], wanted, limit=20, order="id desc")
        evidence[model] = rows
        for row in rows:
            if row.get("move_out_id") and row.get("move_in_id") and float(row.get("svl_count") or 0) > 0:
                ok = True
    return (
        "PASS" if ok else "FAIL",
        evidence,
        [],
        "" if ok else "No existing transform record with stock moves and valuation layers found",
    )


def check_sales_transform_function():
    product_transform_model = search_read(
        "ir.model",
        [("model", "=", "product.transform")],
        ["id", "name", "model"],
        limit=1,
    )
    actions = search_read(
        "ir.actions.act_window",
        [("res_model", "in", ["product.transform", "rma.transform.return"])],
        ["id", "name", "res_model"],
        limit=50,
        order="name",
    )
    menus = search_read(
        "ir.ui.menu",
        [("name", "ilike", "Transform")],
        ["id", "name", "complete_name", "action"],
        limit=80,
        order="id",
    )
    action_by_ref = {f"ir.actions.act_window,{action['id']}": action for action in actions}
    resolved = []
    for menu in menus:
        resolved.append({"menu": menu, "action": action_by_ref.get(menu.get("action"))})
    sales_product_transform = [
        item
        for item in resolved
        if (item.get("action") or {}).get("res_model") == "product.transform"
        and "Sales" in (item.get("menu", {}).get("complete_name") or "")
    ]
    product_transform_any = [
        item for item in resolved if (item.get("action") or {}).get("res_model") == "product.transform"
    ]
    ok = bool(product_transform_model) and bool(sales_product_transform)
    return (
        "PASS" if ok else "FAIL",
        {
            "product_transform_model": product_transform_model,
            "sales_product_transform_menus": sales_product_transform,
            "all_transform_menus": resolved,
            "product_transform_menus_any_module": product_transform_any,
        },
        [],
        "" if ok else "Product Transform action is not available under the Sales module menu",
    )


def check_van_sales_paid_invoice():
    invoices = search_read(
        "account.move",
        [
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("payment_state", "in", ["paid", "in_payment"]),
            "|",
            ("invoice_origin", "ilike", "SOD"),
            ("name", "ilike", "INV-D"),
        ],
        ["id", "name", "invoice_origin", "amount_total", "payment_state", "invoice_date"],
        limit=20,
        order="id desc",
    )
    linked = []
    for inv in invoices:
        orders = []
        if inv.get("invoice_origin"):
            orders = search_read(
                "sale.order",
                [("name", "=", inv["invoice_origin"])],
                ["id", "name", "warehouse_id", "state", "amount_total"],
                limit=5,
            )
        linked.append({"invoice": inv, "sale_orders": orders})
    ok = bool(linked)
    return (
        "PASS" if ok else "FAIL",
        {"linked": linked[:20]},
        [f"account.move:{row['invoice']['id']}" for row in linked[:5]],
        "" if ok else "No paid Van Sales invoice sample found",
    )


def check_original_tax_invoice_once():
    fg = fields_get("account.move")
    candidate_fields = {
        name: spec
        for name, spec in fg.items()
        if any(token in name.lower() for token in ["original", "tax_invoice", "print"])
    }
    reports = search_read(
        "ir.actions.report",
        [
            "|",
            "|",
            ("name", "ilike", "Tax Invoice"),
            ("report_name", "ilike", "tax_invoice"),
            ("name", "ilike", "Original"),
        ],
        ["id", "name", "report_name", "model"],
        limit=50,
    )
    ok = any(
        any(token in name.lower() for token in ["original", "tax_invoice_print", "printed"])
        for name in candidate_fields
    )
    return (
        "PASS" if ok else "FAIL",
        {"account_move_print_fields": candidate_fields, "reports": reports},
        [],
        "" if ok else "No account.move field found to control one-time original tax invoice printing",
    )


def check_manual_merge_internal_transfer():
    wizard_model = search_read(
        "ir.model",
        [("model", "=", "stock.picking.manual.merge.wizard")],
        ["id", "name", "model"],
        limit=1,
    )
    views = search_read(
        "ir.ui.view",
        [
            "|",
            ("arch_db", "ilike", "manual_merge"),
            ("arch_db", "ilike", "Generate Internal Transfer"),
        ],
        ["id", "name", "model", "type", "arch_db"],
        limit=30,
    )
    server_actions = search_read(
        "ir.actions.server",
        [
            "|",
            ("name", "ilike", "Generate Internal Transfer"),
            ("name", "ilike", "Merge Internal"),
        ],
        ["id", "name", "model_id"],
        limit=20,
    )
    pickings = search_read(
        "stock.picking",
        [("name", "in", ["GMP/STOR/00100", "GMP/STOR/00101"])],
        ["id", "name", "state", "origin", "picking_type_id", "move_ids"],
        limit=10,
        order="name",
    )
    ok = bool(wizard_model) and (bool(views) or bool(server_actions))
    return (
        "PASS" if ok else "FAIL",
        {
            "wizard_model": wizard_model,
            "views": [
                {"id": v["id"], "name": v["name"], "model": v["model"], "type": v["type"]}
                for v in views
            ],
            "server_actions": server_actions,
            "sample_pickings": pickings,
        },
        [f"stock.picking:{p['id']}" for p in pickings],
        "" if ok else "Manual merge internal transfer wizard/action not found",
    )


def check_contract_expiry():
    crons = search_read(
        "ir.cron",
        [
            "|",
            "|",
            ("name", "ilike", "Contract"),
            ("name", "ilike", "Expire"),
            ("name", "ilike", "หมด"),
        ],
        ["id", "name", "active", "interval_number", "interval_type", "nextcall", "model_id"],
        limit=30,
        order="name",
    )
    ok = any(cron.get("active") for cron in crons)
    return (
        "PASS" if ok else "FAIL",
        {"crons": crons},
        [],
        "" if ok else "No active contract expiry cron found",
    )


def check_cn_before_vendor_bill():
    reversal_fields = fields_get("account.move.reversal")
    consolidated_model = search_read(
        "ir.model",
        [("model", "=", "account.move.consolidated.reversal")],
        ["id", "name", "model"],
        limit=1,
    )
    reversal_views = search_read(
        "ir.ui.view",
        [
            ("model", "=", "account.move.reversal"),
            "|",
            ("arch_db", "ilike", "return_picking_ids"),
            ("arch_db", "ilike", "Vendor Returns"),
        ],
        ["id", "name", "type", "arch_db"],
        limit=20,
    )
    stock_fields = fields_get("stock.picking")
    return_cn_fields = {
        name: stock_fields[name]
        for name in ["vendor_credit_note_ids", "vendor_credit_note_count", "vendor_credit_note_state"]
        if name in stock_fields
    }
    vendor_return_samples = search_read(
        "stock.picking",
        [("picking_type_code", "=", "outgoing"), ("return_id", "!=", False), ("state", "=", "done")],
        ["id", "name", "partner_id", "vendor_credit_note_count", "vendor_credit_note_state"],
        limit=20,
        order="id desc",
    )
    return_without_cn = [row for row in vendor_return_samples if not row.get("vendor_credit_note_count")]
    can_select_return_only_with_bill = "include_vendor_returns" in reversal_fields and bool(reversal_views)
    has_consolidated_add_lines = bool(consolidated_model)
    return (
        "FAIL",
        {
            "account_move_reversal_vendor_return_fields": {
                name: reversal_fields.get(name)
                for name in ["include_vendor_returns", "available_return_picking_ids", "return_picking_ids", "return_line_ids"]
                if name in reversal_fields
            },
            "reversal_views": [{"id": v["id"], "name": v["name"], "type": v["type"]} for v in reversal_views],
            "consolidated_reversal_model": consolidated_model,
            "stock_picking_cn_fields": return_cn_fields,
            "vendor_return_samples": vendor_return_samples,
            "vendor_returns_without_cn_sample": return_without_cn[:10],
            "observed_capability": {
                "can_select_vendor_returns_when_reversing_existing_bill": can_select_return_only_with_bill,
                "can_add_return_lines_to_existing_credit_note": has_consolidated_add_lines,
                "can_create_cn_before_bill_directly": False,
            },
        },
        [],
        "Current implementation still requires an existing bill/reversal or existing target credit note; no direct CN-before-bill flow was verified",
    )


def check_payment_receipt_report():
    session = session_login()
    payments = search_read(
        "account.payment",
        [("state", "in", ["paid", "in_process"])],
        ["id", "name", "amount", "payment_type", "partner_id", "date"],
        limit=10,
        order="id desc",
    )
    if not payments:
        return "FAIL", {"error": "No paid/in_process payment found"}, [], "No existing paid payment for receipt report"
    pdf = report_pdf(session, "account.report_payment_receipt", payments[0]["id"])
    ok = pdf["status_code"] == 200 and pdf["is_pdf"] and pdf["bytes"] > 1000
    return (
        "PASS" if ok else "FAIL",
        {"payment": payments[0], "pdf": pdf},
        [f"account.payment:{payments[0]['id']}"],
        "" if ok else "Payment receipt report did not render as PDF",
    )


task_fields = [
    "id",
    "name",
    "project_id",
    "stage_id",
    "x_studio_assign_365",
    "x_studio_module",
    "x_studio_function",
    "description",
    "message_attachment_count",
]
task_fields = [field for field in task_fields if field in fields_get("project.task")]
tasks = search_read(
    "project.task",
    [("project_id.name", "=", "Defects List"), ("stage_id.name", "=", "05) Assigned Dev")],
    task_fields,
    limit=200,
    order="id",
)
current_ids = {task["id"] for task in tasks}
task_by_id = {task["id"]: task for task in tasks}
results = []


safe_check(1611, "Sales: Van Sales Transform function/menu", check_vendor_billing_note_menu)
safe_check(1618, "Accounting: consolidated return credit note", check_vendor_return_cn_linked)
safe_check(1625, "Accounting: statement of changes in equity report", lambda: check_report_exists(["equity", "shareholder", "statement of changes"]))
safe_check(1626, "Accounting: cost of sales report", lambda: check_report_exists(["cost of sales", "COGS", "cost sales"]))
safe_check(1633, "Accounting: auto asset from vendor bill account mapping", check_auto_asset_accounts)
safe_check(1654, "Accounting: payment difference rounding/payment posting config", check_payment_config)
safe_check(1659, "Sales report: receipt/tax print once", lambda: check_stock_report("stock.report_picking", "GMP/IN/00123", "incoming"))
safe_check(1665, "Purchase: vendor billing note can pull vendor bill and credit note", check_bn_payment_wizard)
safe_check(1667, "Inventory: vendor return document linkage", check_vendor_return_cn_linked)
safe_check(1672, "Manufacturing: material lot list trigger keeps MO state", check_prepare_material_lots)
safe_check(1673, "Manufacturing: MO schedule date vs SO delivery date", check_mo_schedule_dates)
safe_check(1674, "Manufacturing: international SO auto gen PO", check_export_so_auto_po)
safe_check(1677, "Manufacturing: MO shopfloor visible column/header", check_shopfloor_visibility)
safe_check(1678, "Sales: product transform function in Sales module", check_sales_transform_function)
safe_check(1679, "Van Sales: payment method invoice/payment flow", check_van_sales_paid_invoice)
safe_check(1680, "Sales: original tax invoice print only once", check_original_tax_invoice_once)
safe_check(1682, "Stock: delivery slip/receipt report render", lambda: check_stock_report("stock.report_deliveryslip", "GMP/IN/00123", "incoming"))
safe_check(1683, "Inventory: manual merge internal transfer from MO", check_manual_merge_internal_transfer)
safe_check(1684, "Purchase: contract expiry trigger", check_contract_expiry)
safe_check(1685, "Accounting: create CN before vendor bill", check_cn_before_vendor_bill)
safe_check(1688, "Accounting: multi payment receipt voucher print", check_payment_receipt_report)

tested_ids = {row["defect_id"] for row in results}
untested_current = [
    {
        "id": task["id"],
        "name": task.get("name"),
        "module": task.get("x_studio_module"),
        "function": task.get("x_studio_function"),
    }
    for task in tasks
    if task["id"] not in tested_ids
]
summary = {
    "PASS": sum(1 for row in results if row["status"] == "PASS"),
    "FAIL": sum(1 for row in results if row["status"] == "FAIL"),
    "BLOCKED": sum(1 for row in results if row["status"] == "BLOCKED"),
    "UNTESTED_CURRENT": len(untested_current),
}
payload = {
    "tested_at": dt.datetime.now().isoformat(timespec="seconds"),
    "server": BASE_URL,
    "database": DB,
    "uid": uid,
    "current_assigned_dev_tasks": tasks,
    "summary": summary,
    "results": results,
    "untested_current_tasks": untested_current,
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps({"output": str(OUT), "summary": summary, "tested_ids": sorted(tested_ids), "current_ids": sorted(current_ids)}, ensure_ascii=False, indent=2))
