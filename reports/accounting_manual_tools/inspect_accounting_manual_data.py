from __future__ import annotations

import json
from pathlib import Path


BASE = Path(r"C:\365_project\TheCool18e\Dev\reports\accounting_manual_tools")
OUT = BASE / "accounting_manual_inspection.json"


def _menu_path(menu):
    names = []
    current = menu
    while current:
        names.append(current.name)
        current = current.parent_id
    return " > ".join(reversed(names))


def _serialize_move(move):
    return {
        "id": move.id,
        "name": move.name,
        "ref": move.ref,
        "partner": move.partner_id.display_name,
        "invoice_date": str(move.invoice_date or ""),
        "amount_total": move.amount_total,
        "amount_residual": move.amount_residual,
        "payment_state": move.payment_state,
        "journal": move.journal_id.display_name,
        "currency": move.currency_id.name,
    }


def _primitive(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [_primitive(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _primitive(val) for key, val in value.items()}
    if hasattr(value, "ids") and hasattr(value, "_name"):
        if len(value) == 1:
            try:
                return value.display_name
            except Exception:
                return {"id": value.id, "model": value._name}
        return [getattr(record, "display_name", record.id) for record in value]
    return str(value)


data = {}

data["menus"] = {}
menu_xmlids = [
    "account_customer_group_payment.menu_account_customer_group_payment",
    "cheque_management.menu_cheque_root",
    "cheque_management.menu_cheque_book",
    "cheque_management.menu_cheque_inbound_outbound",
    "cheque_management.menu_cheque_transactions",
    "cheque_management.menu_cheque_inbound",
    "cheque_management.menu_cheque_outbound",
    "cheque_management.menu_cheque_paid",
    "cheque_management.menu_cheque_void",
    "cheque_management.menu_cheque_configuration",
    "cheque_management.menu_cheque_management_config",
]
for xmlid in menu_xmlids:
    try:
        menu = env.ref(xmlid)
        data["menus"][xmlid] = {
            "id": menu.id,
            "name": menu.name,
            "path": _menu_path(menu),
            "action": menu.action.id if menu.action else None,
        }
    except Exception as exc:  # pragma: no cover - shell script
        data["menus"][xmlid] = {"error": str(exc)}


journals = []
for journal in env["account.journal"].search([("type", "in", ("bank", "cash"))], order="name asc"):
    entry = {
        "id": journal.id,
        "name": journal.display_name,
        "code": journal.code,
        "type": journal.type,
        "is_cheque_incoming": bool(getattr(journal, "is_cheque_incoming", False)),
        "is_cheque_outgoing": bool(getattr(journal, "is_cheque_outgoing", False)),
        "dynamic_templates": journal.dynamic_cheque_id.mapped("name"),
        "incoming_lines": [],
        "outgoing_lines": [],
    }
    for line in journal.inbound_payment_method_line_ids:
        entry["incoming_lines"].append(
            {
                "id": line.id,
                "name": line.name,
                "code": line.payment_method_id.code,
                "payment_account": line.payment_account_id.display_name,
                "is_cheque_line": bool(getattr(line, "is_cheque_incoming_line", False)),
                "incoming_cheque_account": getattr(line, "incoming_cheque_account_id", False)
                and line.incoming_cheque_account_id.display_name,
            }
        )
    for line in journal.outbound_payment_method_line_ids:
        entry["outgoing_lines"].append(
            {
                "id": line.id,
                "name": line.name,
                "code": line.payment_method_id.code,
                "payment_account": line.payment_account_id.display_name,
                "is_cheque_line": bool(getattr(line, "is_cheque_outgoing_line", False)),
                "outgoing_cheque_account": getattr(line, "outgoing_cheque_account_id", False)
                and line.outgoing_cheque_account_id.display_name,
            }
        )
    journals.append(entry)
data["journals"] = journals


data["company_groups"] = [
    {
        "id": partner.id,
        "name": partner.display_name,
        "member_count": env["res.partner"].search_count([("company_group_id", "=", partner.id)]),
    }
    for partner in env["res.partner"].search([("is_company_group", "=", True)], order="name asc", limit=50)
]

data["open_customer_invoices"] = [
    _serialize_move(move)
    for move in env["account.move"].search(
        [
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("payment_state", "!=", "paid"),
        ],
        order="invoice_date desc, id desc",
        limit=30,
    )
]
data["open_vendor_bills"] = [
    _serialize_move(move)
    for move in env["account.move"].search(
        [
            ("move_type", "=", "in_invoice"),
            ("state", "=", "posted"),
            ("payment_state", "!=", "paid"),
        ],
        order="invoice_date desc, id desc",
        limit=30,
    )
]

data["cheque_templates"] = [
    {
        "id": rec.id,
        "name": rec.name,
        "width": rec.cheque_width,
        "height": rec.cheque_hight,
    }
    for rec in env["dynamic.cheque"].search([], order="id asc")
]

data["existing_cheque_books"] = [
    {
        "id": rec.id,
        "name": rec.name,
        "state": rec.state,
        "journal": rec.bank_account_journal_id.display_name,
        "qty": rec.cheque_qty,
        "first": rec.first_cheque_no_char,
        "last": rec.last_cheque_no_char,
    }
    for rec in env["cheque.book"].search([], order="id desc", limit=20)
]

data["existing_cheques"] = [
    {
        "id": rec.id,
        "name": rec.name,
        "type": rec.cheque_type,
        "state": rec.state,
        "partner": rec.pay_partner_id.display_name,
        "journal": rec.bank_account_journal_id.display_name,
        "amount": rec.amount,
        "payment": rec.payment_id.display_name,
    }
    for rec in env["cheque.inbound.outbound"].search([], order="id desc", limit=50)
]

OUT.write_text(json.dumps(_primitive(data), ensure_ascii=False, indent=2), encoding="utf-8")
print(str(OUT))
