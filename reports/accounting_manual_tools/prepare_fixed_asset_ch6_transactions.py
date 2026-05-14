from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from odoo import fields


OUT_PATH = Path(
    r"C:\365_project\TheCool18e\Dev\reports\accounting_manual_tools\output\fixed_asset_ch6_transactions_20260410.json"
)

TODAY = fields.Date.today()
TAG = str(TODAY).replace("-", "")


def clean_text(value):
    if not value:
        return ""
    return str(value).replace("Ã‚Â ", " ").replace("\xa0", " ").strip()


def prim(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [prim(v) for v in value]
    if isinstance(value, dict):
        return {str(k): prim(v) for k, v in value.items()}
    return str(value)


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


def _get_asset_model():
    preferred = env["account.asset"].browse(11545)
    if preferred.exists() and preferred.state == "model":
        return preferred
    model = env["account.asset"].search(
        [
            ("state", "=", "model"),
            ("account_asset_id", "!=", False),
            ("account_depreciation_id", "!=", False),
            ("account_depreciation_expense_id", "!=", False),
            ("journal_id", "!=", False),
        ],
        order="id desc",
        limit=1,
    )
    if not model:
        raise ValueError("No asset model available")
    return model


def _ensure_customer(name):
    fallback = env["res.partner"].search([("customer_rank", ">", 0), ("active", "=", True)], order="id asc", limit=1)
    partner = env["res.partner"].search([("name", "=", name)], limit=1)
    if partner:
        if partner.customer_rank < 1:
            partner.customer_rank = 1
        return partner
    if fallback:
        return fallback
    return env["res.partner"].create(
        {
            "name": name,
            "company_type": "company",
            "customer_rank": 1,
            "supplier_rank": 0,
            "approval_state": "approved",
            "ecom_exempt": True,
        }
    )


def _get_gain_loss_accounts(company):
    gain = company.gain_account_id or env["account.account"].search(
        [("company_ids", "in", company.id), ("deprecated", "=", False), ("code", "like", "43%")],
        order="id asc",
        limit=1,
    )
    loss = company.loss_account_id or env["account.account"].search(
        [("company_ids", "in", company.id), ("deprecated", "=", False), ("code", "like", "51%")],
        order="id asc",
        limit=1,
    )
    return gain, loss


def _ensure_asset(name, model, amount, acquisition_date):
    asset = env["account.asset"].search([("name", "=", name)], limit=1)
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
    return asset


def _ensure_sale_invoice(partner, ref, amount):
    move = env["account.move"].search([("move_type", "=", "out_invoice"), ("ref", "=", ref)], limit=1)
    if move:
        if move.state == "draft":
            move.action_post()
        return move
    journal = env["account.journal"].search([("type", "=", "sale")], order="id asc", limit=1)
    account = env["account.account"].search(
        [("account_type", "=", "income"), ("deprecated", "=", False)], order="id asc", limit=1
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
    asset = _ensure_asset(asset_name, model, 60000.0, date(2026, 1, 1))
    invoice = _ensure_sale_invoice(customer, invoice_ref, 55000.0)
    sale_move = asset.depreciation_move_ids.filtered(lambda m: m.asset_move_type == "sale").sorted(key=lambda m: m.id)[-1:]
    if not sale_move:
        gain, loss = _get_gain_loss_accounts(asset.company_id)
        wizard = env["asset.modify"].create(
            {
                "asset_id": asset.id,
                "modify_action": "sell",
                "date": TODAY,
                "name": "ขายสินทรัพย์ตัวอย่างบท 6",
                "invoice_ids": [(6, 0, invoice.ids)],
                "invoice_line_ids": [(6, 0, invoice.invoice_line_ids.filtered(lambda l: l.display_type == "product").ids)],
                "gain_account_id": gain.id if gain else False,
                "loss_account_id": loss.id if loss else False,
            }
        )
        wizard.sell_dispose()
        sale_move = asset.depreciation_move_ids.filtered(lambda m: m.asset_move_type == "sale").sorted(key=lambda m: m.id)[-1:]
        sale_move.filtered(lambda m: m.state == "draft")._post()
    return asset, invoice, sale_move[:1]


def _ensure_dispose_sample(model):
    asset_name = f"MANUAL FA DISPOSE {TAG}"
    asset = _ensure_asset(asset_name, model, 36000.0, date(2026, 1, 1))
    disposal_move = asset.depreciation_move_ids.filtered(lambda m: m.asset_move_type == "disposal").sorted(key=lambda m: m.id)[-1:]
    if not disposal_move:
        gain, loss = _get_gain_loss_accounts(asset.company_id)
        wizard = env["asset.modify"].create(
            {
                "asset_id": asset.id,
                "modify_action": "dispose",
                "date": TODAY,
                "name": "ตัดจำหน่ายสินทรัพย์ตัวอย่างบท 6",
                "gain_account_id": gain.id if gain else False,
                "loss_account_id": loss.id if loss else False,
            }
        )
        wizard.sell_dispose()
        disposal_move = asset.depreciation_move_ids.filtered(lambda m: m.asset_move_type == "disposal").sorted(key=lambda m: m.id)[-1:]
        disposal_move.filtered(lambda m: m.state == "draft")._post()
    return asset, disposal_move[:1]


model = _get_asset_model()
sell_asset, sale_invoice, sale_move = _ensure_sell_sample(model)
dispose_asset, disposal_move = _ensure_dispose_sample(model)

data = {
    "model": _asset_row(model),
    "sell_asset": _asset_row(sell_asset),
    "sale_invoice": {
        "id": sale_invoice.id,
        "name": clean_text(sale_invoice.name),
        "ref": clean_text(sale_invoice.ref),
        "amount_total": sale_invoice.amount_total,
        "partner": clean_text(sale_invoice.partner_id.display_name),
        "date": str(sale_invoice.invoice_date or ""),
        "journal": clean_text(sale_invoice.journal_id.display_name),
    },
    "sale_move": {
        "id": sale_move.id if sale_move else False,
        "name": clean_text(sale_move.name) if sale_move else "",
        "date": str(sale_move.date or "") if sale_move else "",
        "lines": _move_lines(sale_move) if sale_move else [],
    },
    "dispose_asset": _asset_row(dispose_asset),
    "disposal_move": {
        "id": disposal_move.id if disposal_move else False,
        "name": clean_text(disposal_move.name) if disposal_move else "",
        "date": str(disposal_move.date or "") if disposal_move else "",
        "lines": _move_lines(disposal_move) if disposal_move else [],
    },
}

OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
OUT_PATH.write_text(json.dumps(prim(data), ensure_ascii=False, indent=2), encoding="utf-8")
env.cr.commit()
print(str(OUT_PATH))
