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

# Let's inspect INV-E/26/05/00021
moves, err = call_kw('account.move', 'search_read', [
    [('name', '=', 'INV-E/26/05/00021')],
    ['name', 'invoice_origin', 'invoice_line_ids']
], {})

if moves:
    m = moves[0]
    print(f"Invoice: {m['name']} | Origin: {m['invoice_origin']}")
    lines, err = call_kw('account.move.line', 'search_read', [
        [('id', 'in', m['invoice_line_ids'])],
        ['name', 'product_id', 'sale_line_ids', 'purchase_line_id']
    ], {})
    if lines:
        for l in lines:
            print(f"  Line: {l['name']} | Product: {l['product_id']}")
            print(f"    sale_line_ids: {l['sale_line_ids']}")
            print(f"    purchase_line_id: {l['purchase_line_id']}")
else:
    print("Not found")
