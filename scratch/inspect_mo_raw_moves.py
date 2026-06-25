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

# Fetch raw moves for GMP/MOPL/00169 and GMP/MOPL/00170
mos, err = call_kw('mrp.production', 'search_read', [
    [('name', 'in', ['GMP/MOPL/00169', 'GMP/MOPL/00170'])],
    ['id', 'name', 'move_raw_ids']
])

if mos:
    for m in mos:
        print(f"\nMO: {m['name']} | ID: {m['id']}")
        if m['move_raw_ids']:
            raw_moves, err = call_kw('stock.move', 'search_read', [
                [('id', 'in', m['move_raw_ids'])],
                ['name', 'product_id', 'state', 'move_orig_ids', 'move_dest_ids']
            ])
            if raw_moves:
                for rm in raw_moves:
                    print(f"  Raw Move: {rm['product_id']} | State: {rm['state']}")
                    print(f"    move_orig_ids (replenishment sources): {rm['move_orig_ids']}")
                    print(f"    move_dest_ids: {rm['move_dest_ids']}")
            else:
                print("  No raw moves details returned or error:", err)
else:
    print("MOs not found or error:", err)
