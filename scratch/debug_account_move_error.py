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
        print(f"[ERROR] {model}.{method}: {result['error']}")
        return None
    return result.get('result')

print("\n" + "="*80)
print("STEP 1: Check installed modules that extend account.move")
print("="*80)

modules = call_kw('ir.module.module', 'search_read',
    [[['state', '=', 'installed'], ['name', 'like', 'account']]],
    {'fields': ['name', 'state', 'latest_version'], 'limit': 100}
)
if modules:
    print(f"Found {len(modules)} installed account-related modules:")
    for m in modules:
        print(f"  - {m['name']} v{m['latest_version']}")

print("\n" + "="*80)
print("STEP 2: Check recent ir.logging for account.move errors")
print("="*80)

logs = call_kw('ir.logging', 'search_read',
    [[['level', 'in', ['ERROR', 'CRITICAL']], ['func', 'ilike', 'account']]],
    {'fields': ['name', 'level', 'message', 'func', 'create_date'], 'limit': 20,
     'order': 'create_date desc'}
)
if logs:
    print(f"Found {len(logs)} recent error logs:")
    for log in logs:
        print(f"\n  Date: {log['create_date']}")
        print(f"  Level: {log['level']}")
        print(f"  Func: {log['func']}")
        print(f"  Message: {log['message'][:500]}")
else:
    print("No recent error logs found in ir.logging")

print("\n" + "="*80)
print("STEP 3: Inspect account.move fields - check for custom fields")
print("="*80)

fields_info = call_kw('account.move', 'fields_get',
    [],
    {'attributes': ['string', 'type', 'required', 'related', 'store']}
)
if fields_info:
    custom_fields = {k: v for k, v in fields_info.items() if k.startswith('x_')}
    print(f"Custom fields on account.move (x_ prefix): {len(custom_fields)}")
    for fname, finfo in custom_fields.items():
        print(f"  - {fname}: {finfo.get('type')} '{finfo.get('string')}'")

print("\n" + "="*80)
print("STEP 4: Check transform_product_advanced module interactions")
print("="*80)

transform_module = call_kw('ir.module.module', 'search_read',
    [[['name', '=', 'transform_product_advanced'], ['state', '=', 'installed']]],
    {'fields': ['name', 'state', 'latest_version']}
)
if transform_module:
    print(f"transform_product_advanced is INSTALLED: {transform_module}")
else:
    print("transform_product_advanced is NOT installed or not found")

print("\n" + "="*80)
print("STEP 5: Check recent account.move records (last 5 created today)")
print("="*80)

moves = call_kw('account.move', 'search_read',
    [[['create_date', '>=', '2026-06-10 00:00:00']]],
    {'fields': ['name', 'state', 'move_type', 'create_date', 'write_date'],
     'limit': 10, 'order': 'create_date desc'}
)
if moves:
    print(f"Recent account.move records (today):")
    for m in moves:
        print(f"  - {m['name']} | type={m['move_type']} | state={m['state']} | created={m['create_date']}")
else:
    print("No account.move records created today")

print("\n" + "="*80)
print("STEP 6: Check models that inherit account.move")
print("="*80)

inherit_models = call_kw('ir.model', 'search_read',
    [[['model', '=', 'account.move']]],
    {'fields': ['name', 'model', 'info']}
)
if inherit_models:
    for m in inherit_models:
        print(f"  Model: {m['model']} | Name: {m['name']}")

print("\n" + "="*80)
print("DONE")
print("="*80)
