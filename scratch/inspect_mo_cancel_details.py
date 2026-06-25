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
    pass
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

# Search for both MOs on UAT
mos, err = call_kw('mrp.production', 'search_read', [
    [('name', 'in', ['GMP/MOPL/00169', 'GMP/MOPL/00170'])],
    ['id', 'name', 'state', 'write_uid', 'write_date']
])

if mos:
    for m in mos:
        print(f"\nMO: {m['name']} | ID: {m['id']} | State: {m['state']} | Changed by: {m['write_uid']} | Date: {m['write_date']}")
        
        # Read ir.logging or audit log if any, or mail messages with tracking values
        messages, err = call_kw('mail.message', 'search_read', [
            [('model', '=', 'mrp.production'), ('res_id', '=', m['id'])],
            ['id', 'body', 'date', 'tracking_value_ids']
        ])
        if messages:
            for msg in messages:
                print(f"  Message ID {msg['id']} at {msg['date']}: body='{msg['body']}'")
                tracking_ids = msg.get('tracking_value_ids')
                if tracking_ids:
                    trackings, err = call_kw('mail.tracking.value', 'search_read', [
                        [('id', 'in', tracking_ids)],
                        ['field_id', 'old_value_char', 'new_value_char', 'old_value_integer', 'new_value_integer']
                    ])
                    if trackings:
                        for t in trackings:
                            print(f"    - Field: {t['field_id']} | Old: {t['old_value_char'] or t['old_value_integer']} | New: {t['new_value_char'] or t['new_value_integer']}")
else:
    print("Not found or error:", err)
