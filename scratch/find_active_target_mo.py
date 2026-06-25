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

# Search for any mrp.production whose origin contains GMP/MOPL/00169 or GMP/MOPL/00170
mos, err = call_kw('mrp.production', 'search_read', [
    ['|', ('origin', 'ilike', 'GMP/MOPL/00169'), ('origin', 'ilike', 'GMP/MOPL/00170')],
    ['id', 'name', 'state', 'origin', 'picking_ids']
])

if mos:
    print("Found matching MOs by origin:")
    for m in mos:
        print(f"  MO: {m['name']} | State: {m['state']} | Origin: {m['origin']} | Pickings: {m['picking_ids']}")
else:
    print("No matching MOs found by origin, or error:", err)
