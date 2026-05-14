from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from odoo import fields


OUT_PATH = Path(
    r"C:\365_project\TheCool18e\Dev\reports\accounting_manual_tools\output\fixed_asset_mfg_live_samples_20260409.json"
)

TODAY = fields.Date.today()
TAG = str(TODAY).replace("-", "")


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


def clean_text(value):
    if not value:
        return ""
    return str(value).replace("Â ", " ").replace("\xa0", " ").strip()


def menu_path(menu):
    names = []
    current = menu
    while current:
        names.append(clean_text(current.name))
        current = current.parent_id
    return " > ".join(reversed(names))


def _search_one(model, domain, order="id desc"):
    return env[model].search(domain, order=order, limit=1)


def _get_gain_loss_accounts(company):
    gain = company.gain_account_id
    loss = company.loss_account_id
    if not gain:
        gain = env["account.account"].search(
            [
                ("company_ids", "in", company.id),
                ("deprecated", "=", False),
                ("code", "like", "43%"),
            ],
            order="id asc",
            limit=1,
        )
    if not loss:
        loss = env["account.account"].search(
            [
                ("company_ids", "in", company.id),
                ("deprecated", "=", False),
                ("code", "like", "51%"),
            ],
            order="id asc",
            limit=1,
        )
    return gain, loss


def _find_asset_template_source():
    candidates = env["account.asset"].search(
        [
            ("state", "=", "model"),
            ("account_asset_id", "!=", False),
            ("account_depreciation_id", "!=", False),
            ("account_depreciation_expense_id", "!=", False),
            ("journal_id", "!=", False),
        ],
        order="id desc",
        limit=20,
    )
    return candidates[:1]


def _ensure_asset_model():
    model_name = f"MANUAL FIXED ASSET MODEL {TAG}"
    model = _search_one("account.asset", [("name", "=", model_name), ("state", "=", "model")])
    if model:
        return model

    source = _find_asset_template_source()
    if not source:
        raise ValueError("No asset model source found")
    return source[0] if hasattr(source, "__getitem__") else source


def _get_positive_rounding(uom):
    rounding = getattr(uom, "rounding", 0.0) or 0.0
    return rounding if rounding > 0 else 0.01


def _asset_row(asset):
    return {
        "id": asset.id,
        "name": clean_text(asset.display_name),
        "state": asset.state,
        "original_value": asset.original_value,
        "book_value": asset.book_value,
        "salvage_value": asset.salvage_value,
        "model": clean_text(asset.model_id.display_name) if asset.model_id else "",
        "fixed_asset_account": clean_text(asset.account_asset_id.display_name) if asset.account_asset_id else "",
        "depreciation_account": clean_text(asset.account_depreciation_id.display_name) if asset.account_depreciation_id else "",
        "expense_account": clean_text(asset.account_depreciation_expense_id.display_name) if asset.account_depreciation_expense_id else "",
        "journal": clean_text(asset.journal_id.display_name) if asset.journal_id else "",
        "acquisition_date": str(asset.acquisition_date or ""),
        "disposal_date": str(asset.disposal_date or ""),
    }


def _move_lines(move):
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


def _post_draft_asset_moves(asset):
    due_moves = asset.depreciation_move_ids.filtered(lambda m: m.state == "draft" and m.date and m.date <= TODAY)
    if due_moves:
        due_moves._post()


def _ensure_running_asset(name, model, amount, acquisition_date):
    asset = _search_one("account.asset", [("name", "=", name)])
    if not asset:
        asset = env["account.asset"].create(
            {
                "name": name,
                "model_id": model.id,
                "state": "draft",
                "original_value": amount,
                "salvage_value": 0.0,
                "acquisition_date": acquisition_date,
                "prorata_date": acquisition_date,
                "account_asset_id": model.account_asset_id.id,
                "account_depreciation_id": model.account_depreciation_id.id,
                "account_depreciation_expense_id": model.account_depreciation_expense_id.id,
                "journal_id": model.journal_id.id,
            }
        )
    if asset.state == "draft":
        asset.validate()
        asset.compute_depreciation_board()
    _post_draft_asset_moves(asset)
    return asset


def _ensure_draft_asset(name, model, amount, acquisition_date):
    asset = _search_one("account.asset", [("name", "=", name)])
    if not asset:
        asset = env["account.asset"].create(
            {
                "name": name,
                "model_id": model.id,
                "state": "draft",
                "original_value": amount,
                "salvage_value": 0.0,
                "acquisition_date": acquisition_date,
                "prorata_date": acquisition_date,
                "account_asset_id": model.account_asset_id.id,
                "account_depreciation_id": model.account_depreciation_id.id,
                "account_depreciation_expense_id": model.account_depreciation_expense_id.id,
                "journal_id": model.journal_id.id,
            }
        )
    return asset


def _ensure_customer(name):
    partner = _search_one("res.partner", [("name", "=", name)])
    if partner:
        if partner.customer_rank < 1:
            partner.customer_rank = 1
        return partner
    partner = env["res.partner"].create(
        {
            "name": name,
            "company_type": "company",
            "customer_rank": 1,
            "supplier_rank": 0,
            "approval_state": "approved",
            "ecom_exempt": True,
        }
    )
    return partner


def _ensure_sale_invoice(partner, ref, amount):
    move = _search_one("account.move", [("move_type", "=", "out_invoice"), ("ref", "=", ref)])
    if move:
        if move.state == "draft":
            move.action_post()
        return move
    journal = _search_one("account.journal", [("type", "=", "sale")], order="id asc")
    account = env["account.account"].search(
        [("account_type", "=", "income"), ("deprecated", "=", False)],
        order="id asc",
        limit=1,
    )
    move = env["account.move"].create(
        {
            "move_type": "out_invoice",
            "partner_id": partner.id,
            "invoice_date": TODAY,
            "journal_id": journal.id,
            "ref": ref,
            "invoice_line_ids": [
                (
                    0,
                    0,
                    {
                        "name": ref,
                        "quantity": 1.0,
                        "price_unit": amount,
                        "account_id": account.id,
                    },
                )
            ],
        }
    )
    move.action_post()
    return move


def _ensure_sell_sample(model):
    asset_name = f"MANUAL FA SELL {TAG}"
    invoice_ref = f"MANUAL-ASSET-SELL-{TAG}"
    customer = _ensure_customer(f"Manual Asset Buyer {TAG}")
    asset = _ensure_running_asset(asset_name, model, 75000.0, date(2025, 1, 1))
    invoice = _ensure_sale_invoice(customer, invoice_ref, 68000.0)
    sale_moves = asset.depreciation_move_ids.filtered(lambda m: m.asset_move_type == "sale")
    if not sale_moves:
        gain, loss = _get_gain_loss_accounts(asset.company_id)
        wizard = env["asset.modify"].create(
            {
                "asset_id": asset.id,
                "modify_action": "sell",
                "date": TODAY,
                "name": "ขายสินทรัพย์ตัวอย่างสำหรับคู่มือ",
                "invoice_ids": [(6, 0, invoice.ids)],
                "invoice_line_ids": [(6, 0, invoice.invoice_line_ids.filtered(lambda l: l.display_type == "product").ids)],
                "gain_account_id": gain.id if gain else False,
                "loss_account_id": loss.id if loss else False,
            }
        )
        wizard.sell_dispose()
        sale_moves = asset.depreciation_move_ids.filtered(lambda m: m.asset_move_type == "sale")
        sale_moves.filtered(lambda m: m.state == "draft")._post()
    return asset, invoice, sale_moves.sorted(key=lambda m: (m.date or fields.Date.today(), m.id))[-1:]


def _ensure_dispose_sample(model):
    asset_name = f"MANUAL FA DISPOSE {TAG}"
    asset = _ensure_running_asset(asset_name, model, 42000.0, date(2025, 1, 1))
    disposal_moves = asset.depreciation_move_ids.filtered(lambda m: m.asset_move_type == "disposal")
    if not disposal_moves:
        gain, loss = _get_gain_loss_accounts(asset.company_id)
        wizard = env["asset.modify"].create(
            {
                "asset_id": asset.id,
                "modify_action": "dispose",
                "date": TODAY,
                "name": "ตัดจำหน่ายสินทรัพย์ตัวอย่างสำหรับคู่มือ",
                "gain_account_id": gain.id if gain else False,
                "loss_account_id": loss.id if loss else False,
            }
        )
        wizard.sell_dispose()
        disposal_moves = asset.depreciation_move_ids.filtered(lambda m: m.asset_move_type == "disposal")
        disposal_moves.filtered(lambda m: m.state == "draft")._post()
    return asset, disposal_moves.sorted(key=lambda m: (m.date or fields.Date.today(), m.id))[-1:]


def _pick_manufacturing_sample():
    done_mos = env["mrp.production"].search([("state", "=", "done")], order="date_finished desc, id desc", limit=50)
    target = done_mos.filtered(
        lambda mo: any(abs(v.value) > 0 for v in mo.move_raw_ids.stock_valuation_layer_ids)
        and any(abs(v.value) > 0 for v in mo.move_finished_ids.stock_valuation_layer_ids)
    )[:1]
    if not target:
        target = done_mos[:1]
    return target[:1]


def _mo_row(mo):
    return {
        "id": mo.id,
        "name": mo.name,
        "product": clean_text(mo.product_id.display_name),
        "qty": mo.product_qty,
        "qty_produced": getattr(mo, "qty_produced", 0.0),
        "state": mo.state,
        "bom": clean_text(mo.bom_id.display_name) if mo.bom_id else "",
        "picking_type": clean_text(mo.picking_type_id.display_name) if mo.picking_type_id else "",
        "date_start": str(mo.date_start or ""),
        "date_finished": str(mo.date_finished or ""),
    }


def _valuation_rows(mo):
    rows = []
    for move in (mo.move_raw_ids | mo.move_finished_ids):
        for svl in move.stock_valuation_layer_ids:
            rows.append(
                {
                    "svl_id": svl.id,
                    "description": clean_text(svl.description),
                    "reference": clean_text(svl.reference),
                    "product": clean_text(svl.product_id.display_name),
                    "quantity": svl.quantity,
                    "value": svl.value,
                    "account_move_id": svl.account_move_id.id if svl.account_move_id else False,
                    "account_move_name": clean_text(svl.account_move_id.name) if svl.account_move_id else "",
                }
            )
    return rows


def _pick_scrap_sample():
    scrap = env["stock.scrap"].search(
        [
            ("state", "=", "done"),
            "|",
            ("production_id", "!=", False),
            ("workorder_id", "!=", False),
        ],
        order="date_done desc, id desc",
        limit=1,
    )
    return scrap


def _create_manufacturing_scrap_sample(sample_mo):
    if not sample_mo:
        return env["stock.scrap"]

    existing = env["stock.scrap"].search(
        [
            ("state", "=", "done"),
            ("origin", "=", f"MANUAL SCRAP {TAG}"),
            "|",
            ("production_id", "=", sample_mo.id),
            ("workorder_id.production_id", "=", sample_mo.id),
        ],
        order="id desc",
        limit=1,
    )
    if existing:
        return existing

    raw_move = sample_mo.move_raw_ids.filtered(
        lambda move: move.location_id
        and move.product_id
        and move.product_id.categ_id.property_valuation == "real_time"
    )[:1]
    if not raw_move:
        return env["stock.scrap"]

    location = raw_move.location_id
    product = raw_move.product_id
    qty_available = product.with_context(location=location.id).qty_available
    qty = min(max(_get_positive_rounding(raw_move.product_uom), 0.01), qty_available)
    if qty_available <= 0 or qty <= 0:
        return env["stock.scrap"]

    scrap_location = env["stock.location"].search(
        [("scrap_location", "=", True), ("company_id", "in", [False, sample_mo.company_id.id])],
        order="company_id desc, id asc",
        limit=1,
    )
    if not scrap_location:
        return env["stock.scrap"]

    values = {
        "product_id": product.id,
        "scrap_qty": qty,
        "product_uom_id": raw_move.product_uom.id,
        "location_id": location.id,
        "scrap_location_id": scrap_location.id,
        "origin": f"MANUAL SCRAP {TAG}",
        "production_id": sample_mo.id,
        "company_id": sample_mo.company_id.id,
    }
    scrap = env["stock.scrap"].create(values)
    scrap.action_validate()
    return scrap


def _scrap_row(scrap):
    return {
        "id": scrap.id,
        "name": clean_text(scrap.name),
        "product": clean_text(scrap.product_id.display_name),
        "qty": scrap.scrap_qty,
        "uom": clean_text(scrap.product_uom_id.display_name) if scrap.product_uom_id else "",
        "production": clean_text(scrap.production_id.name) if scrap.production_id else clean_text(scrap.workorder_id.production_id.name),
        "source_location": clean_text(scrap.location_id.display_name),
        "scrap_location": clean_text(scrap.scrap_location_id.display_name),
        "state": scrap.state,
        "date_done": str(scrap.date_done or ""),
        "landed_cost_id": scrap.landed_cost_id.id if hasattr(scrap, "landed_cost_id") and scrap.landed_cost_id else False,
    }


def _category_row(category):
    return {
        "id": category.id,
        "name": clean_text(category.complete_name),
        "cost_method": getattr(category, "property_cost_method", ""),
        "valuation": getattr(category, "property_valuation", ""),
        "stock_input": clean_text(category.property_stock_account_input_categ_id.display_name) if getattr(category, "property_stock_account_input_categ_id", False) else "",
        "stock_output": clean_text(category.property_stock_account_output_categ_id.display_name) if getattr(category, "property_stock_account_output_categ_id", False) else "",
        "stock_valuation": clean_text(category.property_stock_valuation_account_id.display_name) if getattr(category, "property_stock_valuation_account_id", False) else "",
    }


data = {"menus": {}, "fixed_asset": {}, "manufacturing": {}}

for xmlid in [
    "account_asset.menu_action_account_asset_form",
    "account_asset.menu_action_account_asset_model_form",
    "account_asset_related_assets.menu_account_asset_hierarchy",
    "account_fixed_asset_report.menu_accounting_fixed_asset_report",
    "mrp.menu_mrp_root",
    "mrp.menu_mrp_production_action",
    "stock_account.menu_valuation",
    "account_stock_card_rng8.menu_account_stock_card_rng8",
]:
    try:
        menu = env.ref(xmlid)
        data["menus"][xmlid] = {
            "id": menu.id,
            "name": clean_text(menu.name),
            "path": menu_path(menu),
            "action": menu.action.id if menu.action else False,
        }
    except Exception as exc:
        data["menus"][xmlid] = {"error": str(exc)}

asset_model = _ensure_asset_model()
draft_asset = _ensure_draft_asset(f"MANUAL FA DRAFT {TAG}", asset_model, 120000.0, TODAY)
running_asset = _ensure_running_asset(f"MANUAL FA RUNNING {TAG}", asset_model, 120000.0, date(2025, 1, 1))
_post_draft_asset_moves(running_asset)
sell_asset, sale_invoice, sale_move = _ensure_sell_sample(asset_model)
dispose_asset, disposal_move = _ensure_dispose_sample(asset_model)

latest_depreciation = running_asset.depreciation_move_ids.filtered(lambda m: m.asset_move_type == "depreciation" and m.state == "posted").sorted(
    key=lambda m: (m.date or fields.Date.today(), m.id)
)[-1:]

data["fixed_asset"] = {
    "model": prim(_asset_row(asset_model)),
    "draft_asset": prim(_asset_row(draft_asset)),
    "running_asset": prim(_asset_row(running_asset)),
    "latest_depreciation_move": prim(
        {
            "id": latest_depreciation.id,
            "name": clean_text(latest_depreciation.name),
            "date": str(latest_depreciation.date or ""),
            "asset_move_type": latest_depreciation.asset_move_type,
            "lines": _move_lines(latest_depreciation),
        }
        if latest_depreciation
        else {}
    ),
    "sell_asset": prim(_asset_row(sell_asset)),
    "sale_invoice": prim(
        {
            "id": sale_invoice.id,
            "name": clean_text(sale_invoice.name),
            "ref": clean_text(sale_invoice.ref),
            "amount_total": sale_invoice.amount_total,
        }
    ),
    "sale_move": prim(
        {
            "id": sale_move.id,
            "name": clean_text(sale_move.name),
            "date": str(sale_move.date or ""),
            "asset_move_type": sale_move.asset_move_type,
            "lines": _move_lines(sale_move),
        }
        if sale_move
        else {}
    ),
    "dispose_asset": prim(_asset_row(dispose_asset)),
    "disposal_move": prim(
        {
            "id": disposal_move.id,
            "name": clean_text(disposal_move.name),
            "date": str(disposal_move.date or ""),
            "asset_move_type": disposal_move.asset_move_type,
            "lines": _move_lines(disposal_move),
        }
        if disposal_move
        else {}
    ),
}

sample_mo = _pick_manufacturing_sample()
sample_scrap = _pick_scrap_sample()
if not sample_scrap and sample_mo:
    sample_scrap = _create_manufacturing_scrap_sample(sample_mo)
fg_category = env["product.category"].search([("complete_name", "like", "%FG%")], order="id asc", limit=1)
rm_category = env["product.category"].search([("complete_name", "like", "%RM%")], order="id asc", limit=1)
stock_location = env["stock.location"].search([("usage", "=", "internal"), ("complete_name", "like", "%Stock%")], order="id asc", limit=1)

data["manufacturing"] = {
    "sample_mo": prim(_mo_row(sample_mo)) if sample_mo else {},
    "sample_valuation_rows": prim(_valuation_rows(sample_mo)) if sample_mo else [],
    "sample_stock_moves": prim(
        {
            "raw_moves": [
                {
                    "name": clean_text(move.display_name),
                    "product": clean_text(move.product_id.display_name),
                    "quantity": move.quantity,
                    "from": clean_text(move.location_id.display_name),
                    "to": clean_text(move.location_dest_id.display_name),
                    "valuation_value": sum(move.stock_valuation_layer_ids.mapped("value")),
                }
                for move in sample_mo.move_raw_ids[:10]
            ],
            "finished_moves": [
                {
                    "name": clean_text(move.display_name),
                    "product": clean_text(move.product_id.display_name),
                    "quantity": move.quantity,
                    "from": clean_text(move.location_id.display_name),
                    "to": clean_text(move.location_dest_id.display_name),
                    "valuation_value": sum(move.stock_valuation_layer_ids.mapped("value")),
                }
                for move in sample_mo.move_finished_ids[:10]
            ],
        }
        if sample_mo
        else {}
    ),
    "sample_scrap": prim(_scrap_row(sample_scrap)) if sample_scrap else {},
    "sample_scrap_move": prim(
        {
            "id": sample_scrap.move_id.account_move_ids[:1].id,
            "name": clean_text(sample_scrap.move_id.account_move_ids[:1].name),
            "date": str(sample_scrap.move_id.account_move_ids[:1].date or ""),
            "lines": _move_lines(sample_scrap.move_id.account_move_ids[:1]),
        }
        if sample_scrap
        and sample_scrap.move_id
        and sample_scrap.move_id.account_move_ids
        else {}
    ),
    "sample_valuation_moves": prim(
        [
            {
                "id": move.id,
                "name": clean_text(move.name),
                "date": str(move.date or ""),
                "ref": clean_text(move.ref),
                "journal": clean_text(move.journal_id.display_name),
                "lines": _move_lines(move),
            }
            for move in env["account.move"].browse(
                list(
                    {
                        row["account_move_id"]
                        for row in _valuation_rows(sample_mo)
                        if row.get("account_move_id")
                    }
                )
            ).sorted(key=lambda m: m.id)
        ]
        if sample_mo
        else []
    ),
    "categories": prim(
        {
            "fg": _category_row(fg_category) if fg_category else {},
            "rm": _category_row(rm_category) if rm_category else {},
        }
    ),
    "rng8_defaults": prim(
        {
            "product_category": clean_text(rm_category.display_name) if rm_category else "",
            "location": clean_text(stock_location.display_name) if stock_location else "",
            "date_from": str(date(2026, 1, 1)),
            "date_to": str(TODAY),
        }
    ),
}

OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
OUT_PATH.write_text(json.dumps(prim(data), ensure_ascii=False, indent=2), encoding="utf-8")
env.cr.commit()
print(str(OUT_PATH))
