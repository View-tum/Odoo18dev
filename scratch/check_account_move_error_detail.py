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

# The error from the user's message was:
# "Odoo Server Error RPC_ERROR on model account.move on 2026-06-10 06:47:52 GMT"
# Traceback truncated at 5051 bytes

# Let's try to reproduce the error by trying typical account.move operations
print("\n" + "="*80)
print("CHECK: Try to replicate the error - account.move action_post")
print("="*80)

# Look at the specific time - what account.move records exist around that time
moves, err = call_kw('account.move', 'search_read',
    [[['write_date', '>=', '2026-06-10 06:45:00'], ['write_date', '<=', '2026-06-10 06:55:00']]],
    {'fields': ['name', 'move_type', 'state', 'write_date', 'create_date', 'ref'], 'limit': 30, 'order': 'write_date desc'}
)
if err:
    print(f"Error: {err}")
else:
    print(f"account.move records around 06:47:52 GMT (total: {len(moves or [])}):")
    for m in (moves or []):
        print(f"  - ID={m.get('id')} | {m.get('name')} | type={m.get('move_type')} | state={m.get('state')} | write={m.get('write_date')} | ref={m.get('ref')}")

print("\n" + "="*80)
print("CHECK: Look at recently created credit notes (out_refund)")
print("="*80)

credit_notes, err = call_kw('account.move', 'search_read',
    [[['move_type', '=', 'out_refund'], ['create_date', '>=', '2026-06-10 00:00:00']]],
    {'fields': ['name', 'state', 'partner_id', 'amount_total', 'rma_transform_return_id', 'create_date'], 'limit': 10, 'order': 'create_date desc'}
)
if err:
    print(f"Error: {err}")
else:
    print(f"Recent credit notes today:")
    for m in (credit_notes or []):
        print(f"  - ID={m.get('id')} | {m.get('name')} | state={m.get('state')} | partner={m.get('partner_id')} | rma_transform={m.get('rma_transform_return_id')} | created={m.get('create_date')}")

print("\n" + "="*80)
print("CHECK: Look at ir.logging for recent errors (all levels)")
print("="*80)

logs, err = call_kw('ir.logging', 'search_read',
    [[['create_date', '>=', '2026-06-10 06:40:00']]],
    {'fields': ['name', 'level', 'message', 'func', 'path', 'create_date'], 'limit': 30, 'order': 'create_date desc'}
)
if err:
    print(f"Error getting logs: {err}")
else:
    print(f"Recent logs ({len(logs or [])} records):")
    for log in (logs or []):
        print(f"\n  [{log.get('level')}] {log.get('create_date')}")
        print(f"  Func: {log.get('func')} | Path: {log.get('path')}")
        print(f"  Message: {str(log.get('message', ''))[:300]}")

print("\n" + "="*80)
print("CHECK: Test a simple account.move create to see if it causes errors")
print("Specifically testing the fields mentioned in the error traceback")
print("="*80)

# The error is on account.move. Let's try to read the account.move
# with the rma_transform fields to see if there's an integrity issue

# Check if there's any account.move with rma_transform_return_id set
transform_moves, err = call_kw('account.move', 'search_read',
    [[['rma_transform_return_id', '!=', False]]],
    {'fields': ['name', 'state', 'rma_transform_return_id', 'rma_transform_claim_id', 'create_date'], 'limit': 10}
)
if err:
    print(f"Error: {err}")
else:
    print(f"account.move with rma_transform_return_id set: {len(transform_moves or [])}")
    for m in (transform_moves or []):
        print(f"  - ID={m.get('id')} | {m.get('name')} | state={m.get('state')} | rma={m.get('rma_transform_return_id')} | created={m.get('create_date')}")

print("\n" + "="*80)
print("CHECK: rma.transform.return recent records")
print("="*80)

rta_records, err = call_kw('rma.transform.return', 'search_read',
    [[['create_date', '>=', '2026-06-10 00:00:00']]],
    {'fields': ['name', 'state', 'credit_note_id', 'credit_note_ids', 'create_date'], 'limit': 10, 'order': 'create_date desc'}
)
if err:
    print(f"Error: {err}")
else:
    print(f"Recent rma.transform.return records: {len(rta_records or [])}")
    for r in (rta_records or []):
        print(f"  - {r.get('name')} | state={r.get('state')} | credit_note={r.get('credit_note_id')} | created={r.get('create_date')}")

print("\n" + "="*80)
print("CHECK: Check the crm.claim.ept for recent RMA operations")
print("="*80)

rma_claims, err = call_kw('crm.claim.ept', 'search_read',
    [[['create_date', '>=', '2026-06-10 00:00:00']]],
    {'fields': ['name', 'state', 'rma_transform_return_id', 'create_date'], 'limit': 10, 'order': 'create_date desc'}
)
if err:
    print(f"Error: {err}")
else:
    print(f"Recent crm.claim.ept records: {len(rma_claims or [])}")
    for r in (rma_claims or []):
        print(f"  - {r.get('name')} | state={r.get('state')} | rma_transform={r.get('rma_transform_return_id')} | created={r.get('create_date')}")

print("\n=== DONE ===")
