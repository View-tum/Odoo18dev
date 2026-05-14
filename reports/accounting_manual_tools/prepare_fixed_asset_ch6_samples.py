from __future__ import annotations

import json
from pathlib import Path


OUT_PATH = Path(
    r"C:\365_project\TheCool18e\Dev\reports\accounting_manual_tools\output\fixed_asset_ch6_live_samples_20260410.json"
)


def _line_dict(line):
    return {
        "account_code": line.account_id.code or "",
        "account_name": line.account_id.name or "",
        "label": line.name or "",
        "debit": float(line.debit or 0.0),
        "credit": float(line.credit or 0.0),
    }


def _move_dict(move):
    return {
        "id": move.id,
        "name": move.name or "",
        "date": str(move.date or ""),
        "ref": move.ref or "",
        "journal": move.journal_id.display_name if move.journal_id else "",
        "lines": [_line_dict(line) for line in move.line_ids.filtered(lambda l: l.display_type == "product" or not l.display_type)],
    }


def _asset_dict(asset):
    return {
        "id": asset.id,
        "name": asset.name or "",
        "state": asset.state or "",
        "original_value": float(asset.original_value or 0.0),
        "book_value": float(asset.book_value or 0.0),
        "salvage_value": float(asset.salvage_value or 0.0),
        "model_name": asset.model_id.name if asset.model_id else "",
        "acquisition_date": str(asset.acquisition_date or ""),
        "method": asset.method or "",
        "method_number": int(asset.method_number or 0),
        "method_period": str(asset.method_period or ""),
        "prorata_date": str(asset.prorata_date or ""),
        "account_asset_id": asset.account_asset_id.display_name if asset.account_asset_id else "",
        "account_depreciation_id": asset.account_depreciation_id.display_name if asset.account_depreciation_id else "",
        "account_depreciation_expense_id": asset.account_depreciation_expense_id.display_name if asset.account_depreciation_expense_id else "",
        "journal_id": asset.journal_id.display_name if asset.journal_id else "",
        "depreciation_entries_count": int(asset.depreciation_entries_count or 0),
        "total_depreciation_entries_count": int(asset.total_depreciation_entries_count or 0),
    }


def _menu_path(xmlid):
    menu = env.ref(xmlid)
    names = []
    current = menu
    while current:
        names.append(current.name)
        current = current.parent_id
    return " > ".join(reversed(names))


def _pick_current_samples():
    draft_asset = env["account.asset"].search([("state", "=", "draft")], order="id desc", limit=1)

    open_asset = env["account.asset"].search(
        [("state", "=", "open"), ("model_id", "!=", False)],
        order="id desc",
        limit=1,
    )
    machine_asset = env["account.asset"].search(
        [("state", "=", "open"), ("name", "ilike", "HOT STAMPING")],
        order="id desc",
        limit=1,
    )
    if machine_asset:
        open_asset = machine_asset

    model_asset = env["account.asset"].browse(11545)
    if not model_asset.exists():
        model_asset = env["account.asset"].search([("state", "=", "model")], order="id desc", limit=1)

    return {
        "draft_asset": _asset_dict(draft_asset),
        "open_asset": _asset_dict(open_asset),
        "model_asset": _asset_dict(model_asset),
    }


payload = {
    "generated_at": str(env["ir.config_parameter"].sudo().get_param("database.uuid") or ""),
    "menus": {
        "assets": _menu_path("account_asset.menu_action_account_asset_form"),
        "asset_models": _menu_path("account_asset.menu_action_account_asset_model_form"),
        "fixed_asset_report": _menu_path("account_fixed_asset_report.menu_accounting_fixed_asset_report"),
    },
    "samples": _pick_current_samples(),
}

OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(OUT_PATH)
