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
print("ROOT CAUSE ANALYSIS: column account_account.is_view does not exist")
print("="*80)
print("""
ERROR: psycopg2.errors.UndefinedColumn: column account_account.is_view does not exist

CALL STACK:
  account_account._compute_code()
    -> accesses record.code_store
       -> triggers SQL query on account_account
          -> fails because column 'is_view' does not exist in the DB

This means: The account module was UPGRADED/UPDATED in code but the DB schema
was NOT updated (migration script not run, or upgrade not applied to DB).

The field 'is_view' was introduced in Odoo 18's account.account model.
It stores whether the account is of type 'view' (group/section account).
""")

print("="*80)
print("CHECK: account.account fields available in the ORM")
print("="*80)

acc_fields, err = call_kw('account.account', 'fields_get', [], {'attributes': ['string', 'type', 'store']})
if err:
    print(f"Error: {err}")
else:
    is_view_field = acc_fields.get('is_view')
    code_store_field = acc_fields.get('code_store')
    code_field = acc_fields.get('code')
    account_type_field = acc_fields.get('account_type')
    print(f"  'is_view' field in ORM: {is_view_field}")
    print(f"  'code_store' field in ORM: {code_store_field}")
    print(f"  'code' field in ORM: {code_field}")
    print(f"  'account_type' field in ORM: {account_type_field}")

print("\n" + "="*80)
print("CHECK: Try to read account.account with 'code' field (triggers the error path)")
print("="*80)

test_acc, err = call_kw('account.account', 'search_read',
    [[['company_ids', 'in', [1]]]],
    {'fields': ['name', 'code', 'account_type'], 'limit': 3}
)
if err:
    print(f"[ERROR reading account.account with 'code']: {err.get('data', {}).get('message', '')}")
else:
    print(f"[OK] account.account readable:")
    for a in (test_acc or []):
        print(f"  - {a.get('code')} | {a.get('name')} | {a.get('account_type')}")

print("\n" + "="*80)
print("CHECK: account module version on UAT server")
print("="*80)

acc_mod, err = call_kw('ir.module.module', 'search_read',
    [[['name', '=', 'account']]],
    {'fields': ['name', 'state', 'latest_version', 'installed_version']}
)
if err:
    print(f"Error: {err}")
else:
    print(f"account module: {acc_mod}")

print("\n" + "="*80)
print("CHECK: account modules that were recently updated")
print("="*80)

updated_mods, err = call_kw('ir.module.module', 'search_read',
    [[['state', '=', 'installed'], ['write_date', '>=', '2026-06-01 00:00:00']]],
    {'fields': ['name', 'state', 'latest_version', 'write_date'], 'limit': 30, 'order': 'write_date desc'}
)
if err:
    print(f"Error: {err}")
else:
    print(f"Modules written/updated since Jun 2026 ({len(updated_mods or [])}):")
    for m in (updated_mods or []):
        print(f"  - {m['name']} v{m['latest_version']} | updated {m['write_date']}")

print("\n" + "="*80)
print("DIAGNOSIS SUMMARY")
print("="*80)
print("""
PROBLEM:  account_account table missing column 'is_view'
TRIGGER:  Any operation that reads account.account.code triggers _compute_code()
          which reads code_store which reads is_view -> DB error

AFFECTED:
  - Any view/form/list that shows account code (journal entries, invoices, etc.)
  - Specifically: account.move with line items that reference account_id

WHEN THE ERROR OCCURS:
  - User opens an invoice/credit note with line items
  - OR reads account.move with account_id fields
  - OR any display_name computation on account.account

ROOT CAUSE OPTIONS:
  1. Odoo server code was updated but 'odoo --upgrade' was NOT run
  2. The account module migration script for 'is_view' column was skipped
  3. A custom module conflicted with account module migration

FIX:
  Option A (Recommended): Run 'odoo -d goldmints_uat -u account' to trigger migration
  Option B: Manually add the column via SQL:
     ALTER TABLE account_account ADD COLUMN IF NOT EXISTS is_view boolean DEFAULT false;
     UPDATE account_account SET is_view = (account_type = 'off_balance');
  
  NOTE: Cannot add column from local - must be done on server 14
""")

print("=== DONE ===")
