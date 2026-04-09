import json

from odoo import fields


def find_or_create_partner(name, company_type="company", parent_group=None):
    partner = env["res.partner"].search([("name", "=", name)], limit=1)
    if not partner:
        partner = env["res.partner"].create(
            {
                "name": name,
                "company_type": company_type,
                "customer_rank": 1 if company_type == "company" else 0,
                "supplier_rank": 1 if company_type == "company" else 0,
                "email": f"{name.lower().replace(' ', '.')}@uat.local",
                "approval_state": "approved",
                "ecom_exempt": True,
            }
        )
    vals = {}
    if parent_group:
        vals["company_group_id"] = parent_group.id
    if partner.approval_state != "approved":
        vals["approval_state"] = "approved"
    if not partner.ecom_exempt:
        vals["ecom_exempt"] = True
    if vals:
        partner.write(vals)
    return partner


def ensure_invoice(partner, move_type, journal, account, amount, label):
    move = env["account.move"].search(
        [
            ("partner_id", "=", partner.id),
            ("move_type", "=", move_type),
            ("ref", "=", label),
            ("state", "=", "posted"),
        ],
        limit=1,
    )
    if move:
        return move

    line_vals = {
        "name": label,
        "quantity": 1.0,
        "price_unit": amount,
        "account_id": account.id,
    }
    move = env["account.move"].create(
        {
            "move_type": move_type,
            "partner_id": partner.id,
            "invoice_date": fields.Date.today(),
            "journal_id": journal.id,
            "ref": label,
            "invoice_line_ids": [(0, 0, line_vals)],
        }
    )
    move.action_post()
    return move


def main():
    company = env.company

    sale_journal = env["account.journal"].search([("type", "=", "sale")], limit=1)
    purchase_journal = env["account.journal"].search([("type", "=", "purchase")], limit=1)
    bank_journal = env["account.journal"].search([("code", "=", "PBAY1")], limit=1)
    income_account = env["account.account"].search(
        [("deprecated", "=", False), ("code", "=", "410001")], limit=1
    )
    expense_account = env["account.account"].search(
        [("deprecated", "=", False), ("code", "=", "510000")], limit=1
    )
    cheque_template = env["dynamic.cheque"].search([("name", "=", "Standard Cheque")], limit=1)

    if bank_journal and cheque_template and cheque_template not in bank_journal.dynamic_cheque_id:
        bank_journal.write({"dynamic_cheque_id": [(4, cheque_template.id)]})

    group = env["res.partner"].search([("name", "=", "UAT MANUAL GROUP"), ("is_company_group", "=", True)], limit=1)
    if not group:
        group = env["res.partner"].create(
            {
                "name": "UAT MANUAL GROUP",
                "company_type": "company",
                "is_company_group": True,
                "credit_limit": 500000.0,
                "approval_state": "approved",
                "ecom_exempt": True,
            }
        )
    else:
        group.write({"approval_state": "approved", "ecom_exempt": True})

    customer_a = find_or_create_partner("UAT Manual Customer A", parent_group=group)
    customer_b = find_or_create_partner("UAT Manual Customer B", parent_group=group)
    vendor = find_or_create_partner("UAT Manual Vendor")

    inv_a = ensure_invoice(
        customer_a,
        "out_invoice",
        sale_journal,
        income_account,
        12000.0,
        "UAT-MANUAL-GROUP-INV-A",
    )
    inv_b = ensure_invoice(
        customer_b,
        "out_invoice",
        sale_journal,
        income_account,
        8000.0,
        "UAT-MANUAL-GROUP-INV-B",
    )
    vendor_bill = ensure_invoice(
        vendor,
        "in_invoice",
        purchase_journal,
        expense_account,
        15000.0,
        "UAT-MANUAL-VENDOR-BILL-001",
    )

    cheque_book = env["cheque.book"].search([("name", "=", "UAT-MANUAL-CB-001")], limit=1)
    if not cheque_book:
        cheque_book = env["cheque.book"].create(
            {
                "name": "UAT-MANUAL-CB-001",
                "bank_account_journal_id": bank_journal.id,
                "date": fields.Date.today(),
                "cheque_qty": 10,
                "first_cheque_no_char": "10000001",
            }
        )
        cheque_book.action_submit()
        cheque_book.action_generate_cheque()
        cheque_book.action_confirm()

    result = {
        "group_id": group.id,
        "group_name": group.name,
        "customer_a_invoice": inv_a.name,
        "customer_b_invoice": inv_b.name,
        "vendor_bill": vendor_bill.name,
        "bank_journal": bank_journal.code if bank_journal else None,
        "cheque_book": cheque_book.name if cheque_book else None,
        "cheque_template": cheque_template.name if cheque_template else None,
    }
    env.cr.commit()
    print(json.dumps(result, ensure_ascii=True))


main()
