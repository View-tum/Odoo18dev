from __future__ import annotations

import json
from pathlib import Path


OUT = Path(
    r"C:\365_project\TheCool18e\Dev\reports\accounting_manual_tools\output\fixed_asset_mfg_probe_20260409.json"
)


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
                "name": getattr(value, "display_name", str(value.id)),
            }
        return [prim(record) for record in value]
    return str(value)


def menu_path(menu):
    names = []
    current = menu
    while current:
        names.append(current.name)
        current = current.parent_id
    return " > ".join(reversed(names))


def move_lines(move):
    return [
        {
            "account_code": line.account_id.code,
            "account_name": line.account_id.name,
            "label": line.name,
            "partner": line.partner_id.display_name or "",
            "debit": line.debit,
            "credit": line.credit,
        }
        for line in move.line_ids.sorted(key=lambda l: (l.account_id.code, l.id))
    ]


def asset_row(asset):
    return {
        "id": asset.id,
        "name": asset.display_name,
        "state": asset.state,
        "original_value": getattr(asset, "original_value", 0.0),
        "acquisition_date": str(getattr(asset, "acquisition_date", "") or ""),
        "book_value": getattr(asset, "book_value", 0.0),
        "salvage_value": getattr(asset, "salvage_value", 0.0),
        "model": asset.model_id.display_name if getattr(asset, "model_id", False) else "",
        "account_asset": asset.account_asset_id.display_name if getattr(asset, "account_asset_id", False) else "",
        "journal": asset.journal_id.display_name if getattr(asset, "journal_id", False) else "",
    }


def production_row(mo):
    return {
        "id": mo.id,
        "name": mo.name,
        "origin": mo.origin,
        "product": mo.product_id.display_name,
        "qty": mo.product_qty,
        "qty_produced": getattr(mo, "qty_produced", 0.0),
        "state": mo.state,
        "bom": mo.bom_id.display_name if mo.bom_id else "",
        "picking_type": mo.picking_type_id.display_name if mo.picking_type_id else "",
        "date_start": str(mo.date_start or ""),
        "date_finished": str(mo.date_finished or ""),
    }


data = {
    "menus": {},
    "asset_samples": {},
    "asset_reports": {},
    "asset_models": [],
    "manufacturing_samples": {},
    "manufacturing_reports": {},
}

menu_xmlids = [
    "account_asset.menu_action_asset",
    "account_asset.menu_action_asset_model",
    "account_asset_customization.menu_account_asset_hierarchy",
    "mrp.menu_mrp_root",
    "mrp.menu_mrp_production_action",
    "stock_account.menu_valuation_report",
]

for xmlid in menu_xmlids:
    try:
        menu = env.ref(xmlid)
        data["menus"][xmlid] = {
            "id": menu.id,
            "name": menu.name,
            "path": menu_path(menu),
            "action": menu.action.id if menu.action else None,
        }
    except Exception as exc:
        data["menus"][xmlid] = {"error": str(exc)}


Asset = env["account.asset"]
Model = env["account.asset"]
Move = env["account.move"]
MO = env["mrp.production"]


data["asset_samples"]["draft"] = prim(
    asset_row(Asset.search([("state", "=", "draft")], order="id desc", limit=1))
)
data["asset_samples"]["running"] = prim(
    asset_row(Asset.search([("state", "=", "open")], order="id desc", limit=1))
)
data["asset_samples"]["closed"] = prim(
    asset_row(Asset.search([("state", "in", ("close", "closed", "model"))], order="id desc", limit=1))
)
data["asset_samples"]["recent"] = prim(
    [asset_row(asset) for asset in Asset.search([], order="id desc", limit=10)]
)

data["asset_models"] = prim(
    [
        {
            "id": asset.id,
            "name": asset.display_name,
            "state": asset.state,
            "journal": asset.journal_id.display_name if getattr(asset, "journal_id", False) else "",
            "account_asset": asset.account_asset_id.display_name if getattr(asset, "account_asset_id", False) else "",
            "method_number": getattr(asset, "method_number", 0),
            "method_period": getattr(asset, "method_period", 0),
        }
        for asset in Asset.search([("state", "=", "model")], order="id desc", limit=20)
    ]
)

asset_moves = Move.search(
    [("asset_id", "!=", False), ("state", "=", "posted")],
    order="date desc, id desc",
    limit=10,
)
data["asset_reports"]["journal_entries"] = prim(
    [
        {
            "move": move.name,
            "date": str(move.date or ""),
            "ref": move.ref,
            "asset": move.asset_id.display_name if move.asset_id else "",
            "journal": move.journal_id.display_name if move.journal_id else "",
            "lines": move_lines(move),
        }
        for move in asset_moves
    ]
)

asset_count = Asset.search_count([])
data["asset_reports"]["counts"] = {"total_assets": asset_count}

done_mos = MO.search([("state", "=", "done")], order="date_finished desc, id desc", limit=20)
confirmed_mos = MO.search([("state", "in", ("confirmed", "progress", "to_close"))], order="id desc", limit=20)
data["manufacturing_samples"]["done"] = prim([production_row(mo) for mo in done_mos[:10]])
data["manufacturing_samples"]["active"] = prim([production_row(mo) for mo in confirmed_mos[:10]])

data["manufacturing_reports"]["stock_valuation_report_action"] = prim(
    data["menus"].get("stock_account.menu_valuation_report", {})
)
data["manufacturing_reports"]["journal_entries"] = prim(
    [
        {
            "mo": mo.display_name,
            "product": mo.product_id.display_name,
            "state": mo.state,
            "finished_moves": [
                {
                    "move": move.display_name,
                    "qty": move.quantity,
                    "value": sum(move.stock_valuation_layer_ids.mapped("value")),
                }
                for move in mo.move_finished_ids
            ],
            "raw_moves": [
                {
                    "move": move.display_name,
                    "qty": move.quantity,
                    "value": sum(move.stock_valuation_layer_ids.mapped("value")),
                }
                for move in mo.move_raw_ids[:10]
            ],
        }
        for mo in done_mos[:5]
    ]
)

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(prim(data), ensure_ascii=False, indent=2), encoding="utf-8")
print(str(OUT))
