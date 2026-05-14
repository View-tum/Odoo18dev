from __future__ import annotations

import json
from pathlib import Path


OUT_PATH = Path(
    r"C:\365_project\TheCool18e\Dev\reports\accounting_manual_tools\output\fixed_asset_mfg_doc_samples_20260409.json"
)


def clean_text(value):
    if not value:
        return ""
    text = str(value).replace("Ã‚Â ", " ").replace("\xa0", " ").strip()
    try:
        return text.encode("latin1").decode("utf-8")
    except Exception:
        return text


def prim(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [prim(item) for item in value]
    if isinstance(value, dict):
        return {str(key): prim(val) for key, val in value.items()}
    if hasattr(value, "ids") and hasattr(value, "_name"):
        if len(value) == 1:
            return {
                "id": value.id,
                "model": value._name,
                "name": clean_text(getattr(value, "display_name", str(value.id))),
            }
        return [prim(record) for record in value]
    return clean_text(value)


def move_lines(move):
    return [
        {
            "account_code": line.account_id.code,
            "account_name": clean_text(line.account_id.name),
            "label": clean_text(line.name),
            "debit": line.debit,
            "credit": line.credit,
        }
        for line in move.line_ids.sorted(key=lambda l: (l.account_id.code or "", l.id))
    ]


def _get_positive_rounding(uom):
    rounding = getattr(uom, "rounding", 0.0) or 0.0
    return rounding if rounding > 0 else 0.01


def _find_done_mo():
    mos = env["mrp.production"].search(
        [
            ("state", "=", "done"),
            ("move_raw_ids", "!=", False),
        ],
        order="date_finished desc, id desc",
        limit=20,
    )
    return mos[:1]


def _find_or_create_scrap():
    existing = env["stock.scrap"].search(
        [
            ("state", "=", "done"),
            ("origin", "=", "MANUAL-DOC-SCRAP-20260409"),
        ],
        order="id desc",
        limit=1,
    )
    if existing:
        return existing

    mo = _find_done_mo()
    if not mo:
        return env["stock.scrap"]

    raw_move = mo.move_raw_ids.filtered(
        lambda move: move.state == "done"
        and move.location_id
        and move.product_id
        and move.product_id.categ_id.property_valuation == "real_time"
    )[:1]
    if not raw_move:
        return env["stock.scrap"]

    location = raw_move.location_id
    product = raw_move.product_id
    qty_available = product.with_context(location=location.id).qty_available
    if qty_available <= 0:
        return env["stock.scrap"]

    scrap_location = env["stock.location"].search(
        [("scrap_location", "=", True), ("company_id", "in", [False, mo.company_id.id])],
        order="company_id desc, id asc",
        limit=1,
    )
    if not scrap_location:
        return env["stock.scrap"]

    qty = min(max(_get_positive_rounding(raw_move.product_uom), 0.01), qty_available)
    scrap = env["stock.scrap"].create(
        {
            "product_id": product.id,
            "scrap_qty": qty,
            "product_uom_id": raw_move.product_uom.id,
            "location_id": location.id,
            "scrap_location_id": scrap_location.id,
            "origin": "MANUAL-DOC-SCRAP-20260409",
            "production_id": mo.id,
            "company_id": mo.company_id.id,
        }
    )
    scrap.action_validate()
    return scrap


def _scrap_row(scrap):
    production = scrap.production_id or scrap.workorder_id.production_id
    return {
        "id": scrap.id,
        "name": clean_text(scrap.name),
        "origin": clean_text(scrap.origin),
        "state": scrap.state,
        "product": clean_text(scrap.product_id.display_name),
        "qty": scrap.scrap_qty,
        "uom": clean_text(scrap.product_uom_id.display_name),
        "location": clean_text(scrap.location_id.display_name),
        "scrap_location": clean_text(scrap.scrap_location_id.display_name),
        "production": clean_text(production.name) if production else "",
        "company": clean_text(scrap.company_id.display_name),
    }


def _related_stock_move(scrap):
    move = scrap.move_ids[:1]
    if not move:
        return {}
    return {
        "id": move.id,
        "name": clean_text(move.name),
        "from": clean_text(move.location_id.display_name),
        "to": clean_text(move.location_dest_id.display_name),
        "qty": move.quantity,
        "product": clean_text(move.product_id.display_name),
        "valuation_layers": [
            {
                "id": svl.id,
                "value": svl.value,
                "description": clean_text(svl.description),
                "account_move_id": svl.account_move_id.id if svl.account_move_id else False,
                "account_move_name": clean_text(svl.account_move_id.name) if svl.account_move_id else "",
            }
            for svl in move.stock_valuation_layer_ids
        ],
    }


def _related_account_move(scrap):
    move = scrap.move_ids[:1]
    if not move:
        return {}
    svl = move.stock_valuation_layer_ids.filtered(lambda row: row.account_move_id)[:1]
    if not svl or not svl.account_move_id:
        return {}
    account_move = svl.account_move_id
    return {
        "id": account_move.id,
        "name": clean_text(account_move.name),
        "date": str(account_move.date or ""),
        "ref": clean_text(account_move.ref),
        "journal": clean_text(account_move.journal_id.display_name),
        "lines": move_lines(account_move),
    }


def _report_defaults():
    return {
        "fixed_asset_report_action": 1550,
        "valuation_action": 705,
        "rng8_action": 1456,
    }


scrap = _find_or_create_scrap()
result = {
    "scrap": prim(_scrap_row(scrap)) if scrap else {},
    "stock_move": prim(_related_stock_move(scrap)) if scrap else {},
    "account_move": prim(_related_account_move(scrap)) if scrap else {},
    "report_defaults": _report_defaults(),
}

OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(str(OUT_PATH))
