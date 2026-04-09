import json
from pathlib import Path

from odoo import fields


TODAY = fields.Date.today()
TODAY_TAG = str(TODAY).replace("-", "")
OUT_PATH = Path(
    r"C:\365_project\TheCool18e\Dev\reports\accounting_manual_tools\output\manual_live_samples_20260408.json"
)


def _search_one(model, domain, order="id desc"):
    return env[model].search(domain, order=order, limit=1)


def _get_bank_journal():
    journal = _search_one("account.journal", [("code", "=", "PBAY1")], order="id asc")
    if not journal:
        raise ValueError("Journal PBAY1 not found")
    return journal


def _get_payment_method_line(journal, payment_type, code=None, flag_field=None):
    domain = [("journal_id", "=", journal.id), ("payment_type", "=", payment_type)]
    if code:
        domain.append(("payment_method_id.code", "=", code))
    if flag_field:
        domain.append((flag_field, "=", True))
    line = _search_one("account.payment.method.line", domain, order="id asc")
    if not line:
        raise ValueError(
            f"Payment method not found for journal={journal.code}, type={payment_type}, code={code}, flag={flag_field}"
        )
    return line


def _get_account(code):
    account = _search_one("account.account", [("code", "=", code), ("deprecated", "=", False)])
    if not account:
        raise ValueError(f"Account {code} not found")
    return account


def _get_sale_journal():
    journal = _search_one("account.journal", [("type", "=", "sale")], order="id asc")
    if not journal:
        raise ValueError("Sale journal not found")
    return journal


def _get_purchase_journal():
    journal = _search_one("account.journal", [("type", "=", "purchase")], order="id asc")
    if not journal:
        raise ValueError("Purchase journal not found")
    return journal


def _ensure_partner(name, *, company_type="company", customer_rank=0, supplier_rank=0, group=None):
    partner = _search_one("res.partner", [("name", "=", name)])
    vals = {}
    if not partner:
        vals = {
            "name": name,
            "company_type": company_type,
            "customer_rank": customer_rank,
            "supplier_rank": supplier_rank,
            "approval_state": "approved",
            "ecom_exempt": True,
        }
        if group:
            vals["company_group_id"] = group.id
        return env["res.partner"].create(vals)

    if customer_rank and partner.customer_rank < customer_rank:
        vals["customer_rank"] = customer_rank
    if supplier_rank and partner.supplier_rank < supplier_rank:
        vals["supplier_rank"] = supplier_rank
    if group and partner.company_group_id != group:
        vals["company_group_id"] = group.id
    if hasattr(partner, "approval_state") and partner.approval_state != "approved":
        vals["approval_state"] = "approved"
    if hasattr(partner, "ecom_exempt") and not partner.ecom_exempt:
        vals["ecom_exempt"] = True
    if vals:
        partner.write(vals)
    return partner


def _ensure_group():
    name = f"UAT MANUAL GROUP {TODAY_TAG}"
    group = _search_one("res.partner", [("name", "=", name), ("is_company_group", "=", True)])
    if not group:
        group = env["res.partner"].create(
            {
                "name": name,
                "company_type": "company",
                "is_company_group": True,
                "credit_limit": 500000.0,
                "approval_state": "approved",
                "ecom_exempt": True,
            }
        )
    return group


def _ensure_invoice(partner, move_type, ref, amount, account_code):
    move = _search_one(
        "account.move",
        [("partner_id", "=", partner.id), ("move_type", "=", move_type), ("ref", "=", ref)],
    )
    if move:
        if move.state == "draft":
            move.action_post()
        return move

    journal = _get_sale_journal() if move_type.startswith("out_") else _get_purchase_journal()
    move = env["account.move"].create(
        {
            "move_type": move_type,
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
                        "account_id": _get_account(account_code).id,
                    },
                )
            ],
        }
    )
    move.action_post()
    return move


def _ensure_cheque_template_on_journal(journal):
    template = _search_one("dynamic.cheque", [("name", "=", "Standard Cheque")], order="id asc")
    if template and template not in journal.dynamic_cheque_id:
        journal.write({"dynamic_cheque_id": [(4, template.id)]})
    return template


def _ensure_cheque_book(journal, min_draft_leaves=1):
    existing_books = env["cheque.book"].search(
        [("bank_account_journal_id", "=", journal.id), ("state", "=", "done")],
        order="id desc",
    )
    for existing in existing_books:
        draft_count = len(existing.cheque_book_lines.filtered(lambda l: l.status == "draft"))
        if draft_count >= min_draft_leaves:
            return existing
    book = env["cheque.book"].create(
        {
            "name": f"UAT-MANUAL-CB-{TODAY_TAG}-{len(existing_books) + 1:02d}",
            "bank_account_journal_id": journal.id,
            "date": TODAY,
            "cheque_qty": 10,
            "first_cheque_no": int(f"86{len(existing_books) + 1:02d}00001"),
            "first_cheque_no_char": f"86{len(existing_books) + 1:02d}00001",
        }
    )
    book.action_submit()
    book.action_generate_cheque()
    book.action_confirm()
    return book


def _get_cheque_leaf(book):
    leaf = _search_one(
        "cheque.book.lines",
        [("cheque_book_id", "=", book.id), ("status", "=", "draft")],
        order="id asc",
    )
    if not leaf:
        raise ValueError(f"No draft cheque leaf found in {book.name}")
    return leaf


def _create_payment_register(move_ids, *, journal, payment_method_line):
    wizard = (
        env["account.payment.register"]
        .with_context(active_model="account.move", active_ids=move_ids)
        .create({})
    )
    wizard.write(
        {
            "journal_id": journal.id,
            "payment_method_line_id": payment_method_line.id,
            "payment_date": TODAY,
        }
    )
    return wizard


def _action_create_payments(wizard, move_ids):
    return wizard.with_context(active_model="account.move", active_ids=move_ids).action_create_payments()


def _ensure_group_payment_draft(group, member_a, member_b, bank_journal):
    record = _search_one(
        "account.customer.group.payment",
        [("company_group_id", "=", group.id), ("state", "=", "lines")],
        order="id desc",
    )
    if record:
        return record
    record = env["account.customer.group.payment"].create(
        {
            "company_group_id": group.id,
            "member_partner_ids": [(6, 0, [member_a.id, member_b.id])],
            "payment_journal_id": bank_journal.id,
            "payment_date": TODAY,
        }
    )
    record.action_search_moves()
    return record


def _ensure_outbound_cheque(vendor_bill, *, journal, cheque_line, memo, final_state):
    existing = _search_one(
        "cheque.inbound.outbound",
        [("memo", "=", memo), ("cheque_type", "=", "inbound")],
        order="id desc",
    )
    if not existing:
        book = _ensure_cheque_book(journal, min_draft_leaves=1)
        leaf = _get_cheque_leaf(book)
        wizard = _create_payment_register([vendor_bill.id], journal=journal, payment_method_line=cheque_line)
        wizard.write(
            {
                "wizard_outbound_cheque_lines": [
                    (
                        0,
                        0,
                        {
                            "cheque_id": leaf.id,
                            "amount": vendor_bill.amount_residual,
                            "date": TODAY,
                            "remarks": memo,
                            "ac_payee": True,
                        },
                    )
                ]
            }
        )
        _action_create_payments(wizard, [vendor_bill.id])
        existing = _search_one(
            "cheque.inbound.outbound",
            [("memo", "=", memo), ("cheque_type", "=", "inbound")],
            order="id desc",
        )

    if final_state in ("bank_deposit", "paid", "void") and existing.state == "confirmed":
        existing.write({"clearing_date": TODAY})
        existing.action_bank_deposit()
    if final_state in ("paid", "void") and existing.state == "bank_deposit":
        existing.action_validate()
    if final_state == "void" and existing.state != "return":
        wizard = env["cheque.return.wizard"].with_context(active_ids=existing.ids).create(
            {"void_reason": "UAT manual void", "cheque_no": existing.name}
        )
        wizard.action_void()
        existing.invalidate_recordset()
        existing = existing.exists()
    return existing


def _ensure_inbound_cheque(customer_invoice, *, journal, cheque_line, memo, final_state):
    existing = _search_one(
        "cheque.inbound.outbound",
        [("memo", "=", memo), ("cheque_type", "=", "outbound")],
        order="id desc",
    )
    if not existing:
        bank = _search_one("res.bank", [], order="id asc")
        if not bank:
            raise ValueError("No bank found for inbound cheque sample")
        wizard = _create_payment_register([customer_invoice.id], journal=journal, payment_method_line=cheque_line)
        wizard.write(
            {
                "wizard_inbound_cheque_lines": [
                    (
                        0,
                        0,
                        {
                            "cheque_id": f"RCV-{customer_invoice.name}",
                            "bank_account_id": bank.id,
                            "branch": "UAT Main Branch",
                            "amount": customer_invoice.amount_residual,
                            "date": TODAY,
                            "remarks": memo,
                            "ac_payee": True,
                        },
                    )
                ]
            }
        )
        _action_create_payments(wizard, [customer_invoice.id])
        existing = _search_one(
            "cheque.inbound.outbound",
            [("memo", "=", memo), ("cheque_type", "=", "outbound")],
            order="id desc",
        )

    if final_state in ("bank_deposit", "paid") and existing.state == "confirmed":
        existing.write({"clearing_date": TODAY})
        existing.action_bank_deposit()
    if final_state == "paid" and existing.state == "bank_deposit":
        existing.action_validate()
    return existing


def _move_lines(move):
    if not move:
        return []
    return [
        {
            "account_code": line.account_id.code,
            "account_name": line.account_id.name,
            "label": line.name,
            "partner": line.partner_id.display_name or False,
            "debit": line.debit,
            "credit": line.credit,
        }
        for line in move.line_ids.sorted(key=lambda l: (l.account_id.code, l.id))
    ]


def _cheque_summary(cheque):
    payment_moves = (cheque.payment_ids | cheque.payment_id).mapped("move_id")
    return {
        "id": cheque.id,
        "name": cheque.name,
        "cheque_type": cheque.cheque_type,
        "state": cheque.state,
        "partner": cheque.pay_partner_id.display_name,
        "journal": cheque.bank_account_journal_id.name,
        "amount": cheque.amount,
        "memo": cheque.memo,
        "payment_ids": (cheque.payment_ids | cheque.payment_id).ids,
        "payment_moves": [
            {"name": move.name, "lines": _move_lines(move)} for move in payment_moves
        ],
        "deposit_move": {
            "name": cheque.cheque_journal_entry_id.name if cheque.cheque_journal_entry_id else None,
            "lines": _move_lines(cheque.cheque_journal_entry_id),
        },
        "void_move": {
            "name": cheque.cheque_return_journal_move_id.name if cheque.cheque_return_journal_move_id else None,
            "lines": _move_lines(cheque.cheque_return_journal_move_id),
        },
        "reversed_entry_names": cheque.reversed_move_ids.mapped("name"),
    }


def main():
    bank_journal = _get_bank_journal()
    manual_in_line = _get_payment_method_line(bank_journal, "inbound", code="manual")
    cheque_out_line = _get_payment_method_line(
        bank_journal, "outbound", code="cheque", flag_field="is_cheque_outgoing_line"
    )
    cheque_in_line = _get_payment_method_line(
        bank_journal, "inbound", code="cheque", flag_field="is_cheque_incoming_line"
    )
    template = _ensure_cheque_template_on_journal(bank_journal)
    book = _ensure_cheque_book(bank_journal, min_draft_leaves=5)

    group = _ensure_group()
    customer_a = _ensure_partner(f"UAT Manual Customer A {TODAY_TAG}", customer_rank=1, group=group)
    customer_b = _ensure_partner(f"UAT Manual Customer B {TODAY_TAG}", customer_rank=1, group=group)
    customer_c = _ensure_partner(f"UAT Manual Customer C {TODAY_TAG}", customer_rank=1)
    customer_d = _ensure_partner(f"UAT Manual Customer D {TODAY_TAG}", customer_rank=1)
    vendor = _ensure_partner(f"UAT Manual Vendor {TODAY_TAG}", supplier_rank=1)

    _ensure_invoice(customer_a, "out_invoice", f"UAT-GP-A-{TODAY_TAG}", 12000.0, "410001")
    _ensure_invoice(customer_b, "out_invoice", f"UAT-GP-B-{TODAY_TAG}", 8000.0, "410001")
    group_draft = _ensure_group_payment_draft(group, customer_a, customer_b, bank_journal)
    group_done = _search_one("account.customer.group.payment", [("state", "=", "done")], order="id desc")

    bill_confirm = _ensure_invoice(vendor, "in_invoice", f"UAT-CQ-OUT-CF-{TODAY_TAG}", 15000.0, "510000")
    bill_paid = _ensure_invoice(vendor, "in_invoice", f"UAT-CQ-OUT-PD-{TODAY_TAG}", 18000.0, "510000")
    bill_void = _ensure_invoice(vendor, "in_invoice", f"UAT-CQ-OUT-VD-{TODAY_TAG}", 9000.0, "510000")
    inv_confirm = _ensure_invoice(customer_c, "out_invoice", f"UAT-CQ-IN-CF-{TODAY_TAG}", 9500.0, "410001")
    inv_paid = _ensure_invoice(customer_d, "out_invoice", f"UAT-CQ-IN-PD-{TODAY_TAG}", 11000.0, "410001")

    outbound_confirmed = _ensure_outbound_cheque(
        bill_confirm,
        journal=bank_journal,
        cheque_line=cheque_out_line,
        memo=f"UAT MANUAL OUTBOUND CONFIRMED {TODAY_TAG}",
        final_state="confirmed",
    )
    outbound_paid = _ensure_outbound_cheque(
        bill_paid,
        journal=bank_journal,
        cheque_line=cheque_out_line,
        memo=f"UAT MANUAL OUTBOUND PAID {TODAY_TAG}",
        final_state="paid",
    )
    outbound_void = _ensure_outbound_cheque(
        bill_void,
        journal=bank_journal,
        cheque_line=cheque_out_line,
        memo=f"UAT MANUAL OUTBOUND VOID {TODAY_TAG}",
        final_state="void",
    )
    inbound_confirmed = _ensure_inbound_cheque(
        inv_confirm,
        journal=bank_journal,
        cheque_line=cheque_in_line,
        memo=f"UAT MANUAL INBOUND CONFIRMED {TODAY_TAG}",
        final_state="confirmed",
    )
    inbound_paid = _ensure_inbound_cheque(
        inv_paid,
        journal=bank_journal,
        cheque_line=cheque_in_line,
        memo=f"UAT MANUAL INBOUND PAID {TODAY_TAG}",
        final_state="paid",
    )

    result = {
        "bank_journal": {
            "id": bank_journal.id,
            "code": bank_journal.code,
            "name": bank_journal.name,
            "manual_in_line_id": manual_in_line.id,
            "cheque_out_line_id": cheque_out_line.id,
            "cheque_in_line_id": cheque_in_line.id,
        },
        "template": {
            "id": template.id if template else None,
            "name": template.name if template else None,
        },
        "cheque_book": {
            "id": book.id,
            "name": book.name,
            "state": book.state,
            "journal": book.bank_account_journal_id.name,
            "draft_leaves": book.cheque_book_lines.filtered(lambda l: l.status == "draft").mapped("name")[:10],
        },
        "group_payment": {
            "draft_id": group_draft.id,
            "draft_state": group_draft.state,
            "draft_members": group_draft.member_partner_ids.mapped("name"),
            "draft_lines": [
                {
                    "move": line.move_id.name,
                    "partner": line.partner_id.name,
                    "amount_to_pay": line.amount_to_pay,
                    "selected": line.is_selected,
                }
                for line in group_draft.line_ids
            ],
            "done_id": group_done.id if group_done else None,
            "done_state": group_done.state if group_done else None,
            "done_name": group_done.name if group_done else None,
        },
        "cheques": {
            "outbound_confirmed": _cheque_summary(outbound_confirmed),
            "outbound_paid": _cheque_summary(outbound_paid),
            "outbound_void": _cheque_summary(outbound_void),
            "inbound_confirmed": _cheque_summary(inbound_confirmed),
            "inbound_paid": _cheque_summary(inbound_paid),
        },
    }
    env.cr.commit()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(OUT_PATH))


main()
