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
print("CHECK: account.move custom fields from transform_product_advanced")
print("="*80)

fields_info, err = call_kw('account.move', 'fields_get', [], {'attributes': ['string', 'type', 'required']})
if err:
    print(f"Error getting fields: {err}")
else:
    transform_fields = {k: v for k, v in fields_info.items() if 'transform' in k.lower() or 'rma' in k.lower()}
    print(f"RMA/Transform related fields on account.move: {len(transform_fields)}")
    for fname, finfo in transform_fields.items():
        print(f"  - {fname}: {finfo.get('type')} '{finfo.get('string')}'")

print("\n" + "="*80)
print("CHECK: account.move.line custom fields from transform_product_advanced")
print("="*80)

line_fields, err = call_kw('account.move.line', 'fields_get', [], {'attributes': ['string', 'type', 'required']})
if err:
    print(f"Error getting fields: {err}")
else:
    transform_line_fields = {k: v for k, v in line_fields.items() if 'transform' in k.lower() or 'rma' in k.lower()}
    print(f"RMA/Transform related fields on account.move.line: {len(transform_line_fields)}")
    for fname, finfo in transform_line_fields.items():
        print(f"  - {fname}: {finfo.get('type')} '{finfo.get('string')}'")

print("\n" + "="*80)
print("CHECK: stock.move custom fields from transform_product_advanced")
print("="*80)

sm_fields, err = call_kw('stock.move', 'fields_get', [], {'attributes': ['string', 'type', 'required']})
if err:
    print(f"Error getting fields: {err}")
else:
    sm_transform_fields = {k: v for k, v in sm_fields.items() if 'transform' in k.lower() or 'rma_transform' in k.lower()}
    print(f"RMA/Transform fields on stock.move: {len(sm_transform_fields)}")
    for fname, finfo in sm_transform_fields.items():
        print(f"  - {fname}: {finfo.get('type')} '{finfo.get('string')}'")

print("\n" + "="*80)
print("CHECK: rma.transform.return model exists?")
print("="*80)

rta_model, err = call_kw('ir.model', 'search_read',
    [[['model', '=', 'rma.transform.return']]],
    {'fields': ['name', 'model', 'state']}
)
if err:
    print(f"Error: {err}")
elif rta_model:
    print(f"rma.transform.return EXISTS: {rta_model}")
else:
    print("rma.transform.return does NOT exist on UAT server!")

print("\n" + "="*80)
print("CHECK: transform_product_advanced module version on UAT")
print("="*80)

mod, err = call_kw('ir.module.module', 'search_read',
    [[['name', '=', 'transform_product_advanced']]],
    {'fields': ['name', 'state', 'latest_version', 'installed_version']}
)
if err:
    print(f"Error: {err}")
elif mod:
    print(f"Module info: {mod}")
else:
    print("Module not found!")

print("\n" + "="*80)
print("CHECK: Try to read account.move to see if rma_transform_return_id field works")
print("="*80)

test_read, err = call_kw('account.move', 'search_read',
    [[['id', '>', 0]]],
    {'fields': ['name', 'move_type', 'rma_transform_return_id', 'rma_transform_claim_id'], 'limit': 3}
)
if err:
    print(f"[ERROR] reading account.move with transform fields: {err.get('message', err)}")
    print(f"[DATA] {err.get('data', {}).get('message', '')}")
else:
    print(f"[OK] account.move fields readable. Sample:")
    for rec in (test_read or []):
        print(f"  - {rec}")

print("\n" + "="*80)
print("CHECK: Try to read crm.claim.ept to verify rma_transform_return_id field")
print("="*80)

crm_fields, err = call_kw('crm.claim.ept', 'fields_get', [], {'attributes': ['string', 'type']})
if err:
    print(f"Error: {err}")
else:
    crm_transform_fields = {k: v for k, v in crm_fields.items() if 'transform' in k.lower()}
    print(f"Transform fields on crm.claim.ept: {len(crm_transform_fields)}")
    for fname, finfo in crm_transform_fields.items():
        print(f"  - {fname}: {finfo.get('type')} '{finfo.get('string')}'")

print("\n" + "="*80)
print("CHECK: Look at the error traceback context - account.move RPC error")
print("Check account.move last write/create to find where error occurred")
print("="*80)

recent_moves, err = call_kw('account.move', 'search_read',
    [[['write_date', '>=', '2026-06-10 06:40:00']]],
    {'fields': ['name', 'move_type', 'state', 'write_date', 'create_date'], 'limit': 20, 'order': 'write_date desc'}
)
if err:
    print(f"Error: {err}")
else:
    print(f"account.move records recently modified:")
    for m in (recent_moves or []):
        print(f"  - {m.get('name')} | type={m.get('move_type')} | state={m.get('state')} | write={m.get('write_date')}")

print("\n=== DONE ===")
