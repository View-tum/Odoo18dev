import requests
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

URL = 'http://10.0.0.14'
DB = 'goldmints_uat'
USERNAME = 'admin'
PASSWORD = '365@gmp'

session = requests.Session()

login_payload = {
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
        "db": DB,
        "login": USERNAME,
        "password": PASSWORD,
    }
}
r = session.post(f"{URL}/web/session/authenticate", json=login_payload, timeout=15)
res = r.json()
if res.get('result', {}).get('uid'):
    print(f"[OK] Logged in as uid={res['result']['uid']}")
else:
    print("[FAIL] Login failed:", res)
    sys.exit(1)

def call_kw(model, method, args, kwargs=None):
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "model": model,
            "method": method,
            "args": args,
            "kwargs": kwargs or {},
        }
    }
    r = session.post(f"{URL}/web/dataset/call_kw", json=payload, timeout=30)
    result = r.json()
    if 'error' in result:
        return None, result['error']
    return result.get('result'), None

print("\n" + "="*80)
print("DETAIL: Inspect credit note CCND/26/06/00001 (ID=69830)")
print("="*80)

cn, err = call_kw('account.move', 'search_read',
    [[['id', '=', 69830]]],
    {'fields': ['name', 'state', 'move_type', 'partner_id', 'amount_total', 'currency_id',
                'invoice_date', 'invoice_date_due', 'journal_id', 'ref', 'reversed_entry_id',
                'rma_transform_return_id', 'rma_transform_claim_id', 'invoice_line_ids',
                'line_ids', 'create_date', 'write_date', 'invoice_origin']}
)
if err:
    print(f"Error: {err}")
else:
    print(f"Credit Note details:")
    for k, v in (cn[0] if cn else {}).items():
        print(f"  {k}: {v}")

print("\n" + "="*80)
print("DETAIL: Inspect credit note LINES of CCND/26/06/00001")
print("="*80)

cn_lines, err = call_kw('account.move.line', 'search_read',
    [[['move_id', '=', 69830]]],
    {'fields': ['name', 'product_id', 'quantity', 'price_unit', 'price_subtotal',
                'account_id', 'tax_ids', 'rma_transform_return_id', 'rma_transform_return_line_id',
                'rma_transform_source_invoice_line_id', 'move_id']}
)
if err:
    print(f"Error: {err}")
else:
    print(f"Credit Note lines ({len(cn_lines or [])} records):")
    for line in (cn_lines or []):
        print(f"\n  Line ID={line.get('id')}:")
        for k, v in line.items():
            print(f"    {k}: {v}")

print("\n" + "="*80)
print("DETAIL: Inspect RMATR/2026/06/000013 (ID=13)")
print("="*80)

rmatr, err = call_kw('rma.transform.return', 'search_read',
    [[['id', '=', 13]]],
    {'fields': ['name', 'state', 'credit_note_id', 'credit_note_ids',
                'return_picking_id', 'return_picking_ids', 'rma_claim_id',
                'source_picking_id', 'partner_id', 'company_id',
                'auto_post_credit_note', 'auto_create_credit_note',
                'create_date', 'write_date']}
)
if err:
    print(f"Error: {err}")
else:
    print(f"RMATR details:")
    for k, v in (rmatr[0] if rmatr else {}).items():
        print(f"  {k}: {v}")

print("\n" + "="*80)
print("DETAIL: What was the original invoice for this CN?")
print("="*80)

# CCND/26/06/00001 reversed_entry_id
cn_data = cn[0] if cn else {}
reversed_id = cn_data.get('reversed_entry_id')
if reversed_id:
    orig_inv, err = call_kw('account.move', 'search_read',
        [[['id', '=', reversed_id[0]]]],
        {'fields': ['name', 'state', 'move_type', 'amount_total', 'partner_id', 'invoice_date']}
    )
    if err:
        print(f"Error: {err}")
    elif orig_inv:
        print(f"Original invoice: {orig_inv[0]}")
    else:
        print("Original invoice not found")
else:
    print("No reversed_entry_id set")

print("\n" + "="*80)
print("DETAIL: Try to simulate what might cause the error on account.move at 06:47:52")
print("Checking if crm.claim.ept 'create_refund' was the culprit")
print("="*80)

# Check the crm.claim.ept ID for this RMATR
claim, err = call_kw('crm.claim.ept', 'search_read',
    [[['rma_transform_return_id', '=', 13]]],
    {'fields': ['id', 'name', 'state', 'rma_transform_return_id', 'refund_invoice_ids',
                'return_picking_id', 'create_date', 'write_date']}
)
if err:
    print(f"Error: {err}")
else:
    print(f"CRM claim for RMATR/13:")
    for r in (claim or []):
        print(f"  - ID={r.get('id')} | {r.get('name')} | state={r.get('state')}")
        print(f"    refund_invoice_ids={r.get('refund_invoice_ids')}")
        print(f"    return_picking_id={r.get('return_picking_id')}")
        print(f"    write_date={r.get('write_date')}")

print("\n" + "="*80)
print("DETAIL: Try a mock action_post on the draft credit notes (ID=69286, 69283)")
print("These are 'False' named drafts associated with RMATR/2026/05/000005")
print("="*80)

drafts, err = call_kw('account.move', 'search_read',
    [[['rma_transform_return_id', '!=', False], ['state', '=', 'draft']]],
    {'fields': ['id', 'name', 'state', 'move_type', 'rma_transform_return_id', 'invoice_line_ids', 'journal_id', 'partner_id']}
)
if err:
    print(f"Error: {err}")
else:
    print(f"Draft account.move with rma_transform_return_id: {len(drafts or [])}")
    for d in (drafts or []):
        print(f"  - ID={d.get('id')} | name={d.get('name')} | type={d.get('move_type')} | partner={d.get('partner_id')}")
        print(f"    rma_transform={d.get('rma_transform_return_id')} | journal={d.get('journal_id')}")
        print(f"    invoice_line_ids={d.get('invoice_line_ids')}")

print("\n=== DONE ===")
