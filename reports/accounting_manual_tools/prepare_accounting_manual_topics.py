import json
from pathlib import Path

from odoo import fields


TODAY = fields.Date.today()
TODAY_TAG = str(TODAY).replace("-", "")
OUT_PATH = Path(r"C:\365_project\TheCool18e\Dev\reports\accounting_manual_tools\output\manual_topic_samples.json")


def _search_one(model, domain, order="id desc"):
    return env[model].search(domain, order=order, limit=1)


def _get_bank_journal():
    journal = _search_one("account.journal", [("code", "=", "PBAY1")])
    if not journal:
        raise ValueError("Bank journal PBAY1 not found")
    return journal


def _get_payment_method_line(journal, payment_type, code=None, flag_field=None):
    domain = [
        ("journal_id", "=", journal.id),
        ("payment_type", "=", payment_type),
    ]
    if code:
        domain.append(("payment_method_id.code", "=", code))
    if flag_field:
        domain.append((flag_field, "=", True))
    line = _search_one("account.payment.method.line", domain, order="id asc")
    if not line:
        raise ValueError(
            f"Payment method line not found for journal={journal.code}, "
            f"payment_type={payment_type}, code={code}, flag={flag_field}"
        )
    return line


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
        partner = env["res.partner"].create(vals)
        return partner

    if group and partner.company_group_id != group:
        vals["company_group_id"] = group.id
    if hasattr(partner, "approval_state") and partner.approval_state != "approved":
        vals["approval_state"] = "approved"
    if hasattr(partner, "ecom_exempt") and not partner.ecom_exempt:
        vals["ecom_exempt"] = True
    if customer_rank and partner.customer_rank < customer_rank:
        vals["customer_rank"] = customer_rank
    if supplier_rank and partner.supplier_rank < supplier_rank:
        vals["supplier_rank"] = supplier_rank
    if vals:
        partner.write(vals)
    return partner


def _ensure_group():
    group_name = f"UAT MANUAL GROUP {TODAY_TAG}"
    group = _search_one("res.partner", [("name", "=", group_name), ("is_company_group", "=", True)])
    if not group:
        group = env["res.partner"].create(
            {
                "name": group_name,
                "company_type": "company",
                "is_company_group": True,
                "credit_limit": 500000.0,
                "approval_state": "approved",
                "ecom_exempt": True,
            }
        )
    else:
        group.write({"approval_state": "approved", "ecom_exempt": True})
    return group


def _get_account(code):
    account = _search_one("account.account", [("deprecated", "=", False), ("code", "=", code)])
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


def _ensure_invoice(partner, move_type, ref, amount, account_code):
    existing = _search_one(
        "account.move",
        [
            ("partner_id", "=", partner.id),
            ("move_type", "=", move_type),
            ("ref", "=", ref),
        ],
    )
    if existing:
        if existing.state == "draft":
            existing.action_post()
        return existing

    journal = _get_sale_journal() if move_type.startswith("out_") else _get_purchase_journal()
    line_vals = {
        "name": ref,
        "quantity": 1.0,
        "price_unit": amount,
        "account_id": _get_account(account_code).id,
    }
    move = env["account.move"].create(
        {
            "move_type": move_type,
            "partner_id": partner.id,
            "invoice_date": TODAY,
            "journal_id": journal.id,
            "ref": ref,
            "invoice_line_ids": [(0, 0, line_vals)],
        }
    )
    move.action_post()
    return move


def _ensure_cheque_template_on_journal(journal):
    template = _search_one("dynamic.cheque", [("name", "=", "Standard Cheque")])
    if template and template not in journal.dynamic_cheque_id:
        journal.write({"dynamic_cheque_id": [(4, template.id)]})
    return template


def _ensure_cheque_book(journal):
    prefix = f"UAT-MANUAL-CB-{TODAY_TAG}"
    candidates = env["cheque.book"].search(
        [
            ("name", "=like", f"{prefix}%"),
            ("bank_account_journal_id", "=", journal.id),
        ],
        order="id desc",
    )
    for candidate in candidates:
        draft_lines = candidate.cheque_book_lines.filtered(lambda l: l.status == "draft")
        if len(draft_lines) >= 5:
            return candidate

    suffix = len(candidates) + 1
    book = env["cheque.book"].create(
        {
            "name": f"{prefix}-{suffix:02d}",
            "bank_account_journal_id": journal.id,
            "date": TODAY,
            "cheque_qty": 10,
            "first_cheque_no": int(f"86{suffix:02d}00001"),
            "first_cheque_no_char": f"86{suffix:02d}00001",
        }
    )
    book.action_submit()
    book.action_generate_cheque()
    book.action_confirm()
    return book


def _get_cheque_leaf(book, number=None):
    domain = [("cheque_book_id", "=", book.id), ("status", "=", "draft")]
    if number:
        domain.append(("name", "=", number))
    line = _search_one("cheque.book.lines", domain, order="id asc")
    if line:
        return line
    if number:
        line = _search_one("cheque.book.lines", [("cheque_book_id", "=", book.id), ("name", "=", number)], order="id asc")
        if line:
            return line
    raise ValueError(f"No available cheque leaf found in {book.name}")


def _create_payment_register_for_moves(move_ids, *, journal, payment_method_line):
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


def _wizard_create_payments(wizard, move_ids, extra_context=None):
    ctx = {"active_model": "account.move", "active_ids": move_ids}
    if extra_context:
        ctx.update(extra_context)
    return wizard.with_context(**ctx).action_create_payments()


def _ensure_group_payment_records(group, member_a, member_b, bank_journal, manual_in_line, selected_moves):
    draft_rec = _search_one("account.customer.group.payment", [("company_group_id", "=", group.id), ("state", "=", "lines")])
    if not draft_rec:
        draft_rec = env["account.customer.group.payment"].create(
            {
                "company_group_id": group.id,
                "member_partner_ids": [(6, 0, [member_a.id, member_b.id])],
                "payment_journal_id": bank_journal.id,
                "payment_date": TODAY,
            }
        )
        draft_rec.action_search_moves()
    draft_rec.line_ids.write({"is_selected": False})
    draft_rec.line_ids.filtered(lambda l: l.move_id.id in selected_moves.ids).write({"is_selected": True})

    done_rec = _search_one("account.customer.group.payment", [("company_group_id", "=", group.id), ("state", "=", "done")])
    if not done_rec:
        done_rec = env["account.customer.group.payment"].create(
            {
                "company_group_id": group.id,
                "member_partner_ids": [(6, 0, [member_a.id, member_b.id])],
                "payment_journal_id": bank_journal.id,
                "payment_date": TODAY,
            }
        )
        done_rec.action_search_moves()
        action = done_rec.action_confirm_payment()
        wizard = env["account.payment.register"].browse(action["res_id"])
        wizard.write(
            {
                "journal_id": bank_journal.id,
                "payment_method_line_id": manual_in_line.id,
            }
        )
        selected_moves = done_rec.line_ids.filtered("is_selected").mapped("move_id").exists()
        _wizard_create_payments(
            wizard,
            selected_moves.ids,
            extra_context=action["context"],
        )
        done_rec.invalidate_recordset()
        done_rec = done_rec.exists()
    elif done_rec.generated_payment_ids:
        return draft_rec, done_rec

    return draft_rec, done_rec


def _ensure_outbound_cheque(vendor_bill, *, journal, cheque_line, cheque_leaf_no, memo, state):
    existing = _search_one("cheque.inbound.outbound", [("memo", "=", memo), ("cheque_type", "=", "inbound")])
    if existing:
        cheque = existing
    else:
        wizard = _create_payment_register_for_moves([vendor_bill.id], journal=journal, payment_method_line=cheque_line)
        leaf = _get_cheque_leaf(_ensure_cheque_book(journal), cheque_leaf_no)
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
        _wizard_create_payments(wizard, [vendor_bill.id])
        cheque = _search_one("cheque.inbound.outbound", [("memo", "=", memo), ("cheque_type", "=", "inbound")])

    if state in ("bank_deposit", "paid") and cheque.state == "confirmed":
        cheque.write({"clearing_date": TODAY})
        cheque.action_bank_deposit()
    if state == "paid" and cheque.state == "bank_deposit":
        cheque.action_validate()
    if state == "void" and cheque.state != "return":
        if cheque.state == "confirmed":
            cheque.write({"clearing_date": TODAY})
            cheque.action_bank_deposit()
        if cheque.state == "bank_deposit":
            cheque.action_validate()
        wiz = env["cheque.return.wizard"].with_context(active_ids=cheque.ids).create(
            {
                "void_reason": "UAT manual void example",
                "cheque_no": cheque.name,
            }
        )
        wiz.action_void()
        cheque.invalidate_recordset()
        cheque = cheque.exists()
    return cheque


def _ensure_inbound_cheque(customer_invoice, *, journal, cheque_line, memo, state):
    existing = _search_one("cheque.inbound.outbound", [("memo", "=", memo), ("cheque_type", "=", "outbound")])
    if existing:
        cheque = existing
    else:
        bank = _search_one("res.bank", [], order="id asc")
        if not bank:
            raise ValueError("No bank found for inbound cheque sample")
        wizard = _create_payment_register_for_moves([customer_invoice.id], journal=journal, payment_method_line=cheque_line)
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
        _wizard_create_payments(wizard, [customer_invoice.id])
        cheque = _search_one("cheque.inbound.outbound", [("memo", "=", memo), ("cheque_type", "=", "outbound")])

    if state in ("bank_deposit", "paid") and cheque.state == "confirmed":
        cheque.write({"clearing_date": TODAY})
        cheque.action_bank_deposit()
    if state == "paid" and cheque.state == "bank_deposit":
        cheque.action_validate()
    return cheque


def _move_lines_summary(move):
    return [
        {
            "move": move.name,
            "account_code": line.account_id.code,
            "account_name": line.account_id.name,
            "label": line.name,
            "partner": line.partner_id.display_name,
            "debit": line.debit,
            "credit": line.credit,
        }
        for line in move.line_ids.sorted(key=lambda l: (l.debit == 0, l.account_id.code, l.id))
    ]


def _payment_summary(payments):
    result = []
    for pay in payments:
        result.append(
            {
                "id": pay.id,
                "name": pay.name,
                "amount": pay.amount,
                "partner": pay.partner_id.display_name,
                "state": pay.state,
                "move_name": pay.move_id.name if pay.move_id else None,
                "move_lines": _move_lines_summary(pay.move_id) if pay.move_id else [],
            }
        )
    return result


def _cheque_summary(cheque):
    return {
        "id": cheque.id,
        "name": cheque.name,
        "type": cheque.cheque_type,
        "state": cheque.state,
        "partner": cheque.pay_partner_id.display_name,
        "amount": cheque.amount,
        "memo": cheque.memo,
        "payment_ids": cheque.payment_ids.ids,
        "payment_move_lines": _payment_summary(cheque.payment_ids | cheque.payment_id),
        "bank_deposit_move": {
            "name": cheque.cheque_journal_entry_id.name if cheque.cheque_journal_entry_id else None,
            "lines": _move_lines_summary(cheque.cheque_journal_entry_id) if cheque.cheque_journal_entry_id else [],
        },
        "void_move": {
            "name": cheque.cheque_return_journal_move_id.name if cheque.cheque_return_journal_move_id else None,
            "lines": _move_lines_summary(cheque.cheque_return_journal_move_id) if cheque.cheque_return_journal_move_id else [],
        },
    }


def main():
    bank_journal = _get_bank_journal()
    _ensure_cheque_template_on_journal(bank_journal)
    cheque_book = _ensure_cheque_book(bank_journal)
    draft_leaves = cheque_book.cheque_book_lines.filtered(lambda l: l.status == "draft").sorted(key=lambda l: l.id)
    if len(draft_leaves) < 3:
        raise ValueError(f"Cheque book {cheque_book.name} does not have enough available cheque leaves")

    manual_in_line = _get_payment_method_line(bank_journal, "inbound", code="manual")
    cheque_out_line = _get_payment_method_line(bank_journal, "outbound", code="cheque", flag_field="is_cheque_outgoing_line")
    cheque_in_line = _get_payment_method_line(bank_journal, "inbound", code="cheque", flag_field="is_cheque_incoming_line")

    group = _ensure_group()
    customer_a = _ensure_partner(f"UAT Manual Customer A {TODAY_TAG}", customer_rank=1, group=group)
    customer_b = _ensure_partner(f"UAT Manual Customer B {TODAY_TAG}", customer_rank=1, group=group)
    customer_c = _ensure_partner(f"UAT Manual Customer C {TODAY_TAG}", customer_rank=1)
    customer_d = _ensure_partner(f"UAT Manual Customer D {TODAY_TAG}", customer_rank=1)
    vendor = _ensure_partner(f"UAT Manual Vendor {TODAY_TAG}", supplier_rank=1)

    inv_group_a = _ensure_invoice(customer_a, "out_invoice", f"UAT-MANUAL-GROUP-INV-A-{TODAY_TAG}", 12000.0, "410001")
    inv_group_b = _ensure_invoice(customer_b, "out_invoice", f"UAT-MANUAL-GROUP-INV-B-{TODAY_TAG}", 8000.0, "410001")
    inv_rcv_out = _ensure_invoice(customer_c, "out_invoice", f"UAT-MANUAL-RCV-OUT-{TODAY_TAG}", 9500.0, "410001")
    inv_rcv_paid = _ensure_invoice(customer_d, "out_invoice", f"UAT-MANUAL-RCV-PAID-{TODAY_TAG}", 11000.0, "410001")

    bill_pay_out = _ensure_invoice(vendor, "in_invoice", f"UAT-MANUAL-PAY-OUT-{TODAY_TAG}", 15000.0, "510000")
    bill_pay_paid = _ensure_invoice(vendor, "in_invoice", f"UAT-MANUAL-PAY-PAID-{TODAY_TAG}", 18000.0, "510000")
    bill_pay_void = _ensure_invoice(vendor, "in_invoice", f"UAT-MANUAL-PAY-VOID-{TODAY_TAG}", 9000.0, "510000")

    gp_draft, gp_done = _ensure_group_payment_records(
        group,
        customer_a,
        customer_b,
        bank_journal,
        manual_in_line,
        inv_group_a | inv_group_b,
    )
    outbound_confirmed = _ensure_outbound_cheque(
        bill_pay_out,
        journal=bank_journal,
        cheque_line=cheque_out_line,
        cheque_leaf_no=draft_leaves[0].name,
        memo=f"UAT MANUAL CHEQUE PAY OUTSTANDING {TODAY_TAG}",
        state="confirmed",
    )
    outbound_paid = _ensure_outbound_cheque(
        bill_pay_paid,
        journal=bank_journal,
        cheque_line=cheque_out_line,
        cheque_leaf_no=draft_leaves[1].name,
        memo=f"UAT MANUAL CHEQUE PAY PAID {TODAY_TAG}",
        state="paid",
    )
    outbound_void = _ensure_outbound_cheque(
        bill_pay_void,
        journal=bank_journal,
        cheque_line=cheque_out_line,
        cheque_leaf_no=draft_leaves[2].name,
        memo=f"UAT MANUAL CHEQUE PAY VOID {TODAY_TAG}",
        state="void",
    )
    inbound_confirmed = _ensure_inbound_cheque(
        inv_rcv_out,
        journal=bank_journal,
        cheque_line=cheque_in_line,
        memo=f"UAT MANUAL CHEQUE RECEIVE OUTSTANDING {TODAY_TAG}",
        state="confirmed",
    )
    inbound_paid = _ensure_inbound_cheque(
        inv_rcv_paid,
        journal=bank_journal,
        cheque_line=cheque_in_line,
        memo=f"UAT MANUAL CHEQUE RECEIVE PAID {TODAY_TAG}",
        state="paid",
    )

    result = {
        "bank_journal": {"id": bank_journal.id, "code": bank_journal.code, "name": bank_journal.name},
        "cheque_book": {
            "id": cheque_book.id,
            "name": cheque_book.name,
            "state": cheque_book.state,
            "draft_leaves": draft_leaves[:5].mapped("name"),
        },
        "group_payment": {
            "draft_id": gp_draft.id,
            "draft_name": gp_draft.name,
            "done_id": gp_done.id,
            "done_name": gp_done.name,
            "done_payment_ids": gp_done.generated_payment_ids.ids,
            "done_payments": _payment_summary(gp_done.generated_payment_ids),
        },
        "vendor_bill_outstanding": {"id": bill_pay_out.id, "name": bill_pay_out.name, "ref": bill_pay_out.ref},
        "vendor_bill_paid": {"id": bill_pay_paid.id, "name": bill_pay_paid.name, "ref": bill_pay_paid.ref},
        "vendor_bill_void": {"id": bill_pay_void.id, "name": bill_pay_void.name, "ref": bill_pay_void.ref},
        "customer_invoice_outstanding": {"id": inv_rcv_out.id, "name": inv_rcv_out.name, "ref": inv_rcv_out.ref},
        "customer_invoice_paid": {"id": inv_rcv_paid.id, "name": inv_rcv_paid.name, "ref": inv_rcv_paid.ref},
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
