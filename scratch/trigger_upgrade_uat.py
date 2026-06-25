import requests
import json
import sys
import time
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
    r = session.post(f"{URL}/web/dataset/call_kw", json=payload, timeout=60)
    result = r.json()
    if 'error' in result:
        return None, result['error']
    return result.get('result'), None

print("\n" + "="*70)
print("STEP 1: Check current module states")
print("="*70)

# Modules related to account_financial_report and account customizations
modules_to_check = [
    'account_financial_report',
    'account',
    'mbr_financial_report',
    'l10n_th_account_tax',
    'l10n_th_account_tax_report',
]

for mod_name in modules_to_check:
    mod, err = call_kw('ir.module.module', 'search_read',
        [[['name', '=', mod_name]]],
        {'fields': ['name', 'state', 'latest_version', 'installed_version']}
    )
    if err:
        print(f"  [{mod_name}] Error: {err.get('data', {}).get('message', err)}")
    elif mod:
        m = mod[0]
        status = "✓" if m['state'] == 'installed' else "⚠"
        print(f"  {status} {m['name']} | state={m['state']} | v{m['latest_version']}")
    else:
        print(f"  ? {mod_name} | not found")

print("\n" + "="*70)
print("STEP 2: Check modules in 'to upgrade' state")
print("="*70)

to_upgrade, err = call_kw('ir.module.module', 'search_read',
    [[['state', 'in', ['to upgrade', 'to install']]]],
    {'fields': ['name', 'state']}
)
if err:
    print(f"Error: {err}")
elif to_upgrade:
    print(f"Modules pending upgrade/install:")
    for m in to_upgrade:
        print(f"  - {m['name']} | {m['state']}")
else:
    print("No modules pending upgrade")

print("\n" + "="*70)
print("STEP 3: Mark account_financial_report for upgrade")
print("="*70)

# Get module ID
mod_rec, err = call_kw('ir.module.module', 'search_read',
    [[['name', '=', 'account_financial_report']]],
    {'fields': ['id', 'name', 'state']}
)
if err or not mod_rec:
    print(f"Error finding module: {err}")
    sys.exit(1)

mod_id = mod_rec[0]['id']
mod_state = mod_rec[0]['state']
print(f"Found account_financial_report: ID={mod_id}, state={mod_state}")

if mod_state == 'installed':
    print(f"Calling button_upgrade() on module ID={mod_id}...")
    result, err = call_kw('ir.module.module', 'button_upgrade',
        [[mod_id]],
        {}
    )
    if err:
        print(f"[FAIL] button_upgrade error: {err.get('data', {}).get('message', err)}")
    else:
        print(f"[OK] button_upgrade() called. Result: {result}")
else:
    print(f"Module state is '{mod_state}' - skip")

print("\n" + "="*70)
print("STEP 4: Verify module is now 'to upgrade'")
print("="*70)

mod_rec2, err = call_kw('ir.module.module', 'search_read',
    [[['name', '=', 'account_financial_report']]],
    {'fields': ['id', 'name', 'state']}
)
if mod_rec2:
    print(f"account_financial_report state: {mod_rec2[0]['state']}")

print("\n" + "="*70)
print("STEP 5: Trigger upgrade_all to actually run the upgrade")
print("="*70)

print("Calling upgrade_all()...")
result, err = call_kw('ir.module.module', 'upgrade_all',
    [[]],
    {}
)
if err:
    err_msg = err.get('data', {}).get('message', str(err))
    print(f"[INFO] upgrade_all result: {err_msg[:200]}")
else:
    print(f"[OK] upgrade_all() result: {result}")

print("\n" + "="*70)
print("STEP 6: Wait 10s then verify upgrade completed")
print("="*70)

print("Waiting 10 seconds for upgrade to complete...")
time.sleep(10)

mod_final, err = call_kw('ir.module.module', 'search_read',
    [[['name', '=', 'account_financial_report']]],
    {'fields': ['id', 'name', 'state', 'latest_version', 'installed_version']}
)
if mod_final:
    m = mod_final[0]
    print(f"account_financial_report: state={m['state']} | v{m['latest_version']}")

print("\n" + "="*70)
print("STEP 7: Test if error is resolved - read account.account with code")
print("="*70)

test_acc, err = call_kw('account.account', 'search_read',
    [[['company_ids', 'in', [1]]]],
    {'fields': ['name', 'code', 'account_type'], 'limit': 3}
)
if err:
    print(f"[STILL FAILING] account.account code read error:")
    print(f"  {err.get('data', {}).get('message', '')[:200]}")
else:
    print(f"[RESOLVED!] account.account readable with 'code' field:")
    for a in (test_acc or []):
        print(f"  - {a.get('code')} | {a.get('name')} | {a.get('account_type')}")

print("\n=== DONE ===")
