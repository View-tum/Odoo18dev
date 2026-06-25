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

# Search for the field in ir.model.fields
fields_rec, err = call_kw('ir.model.fields', 'search_read', [
    [('model', '=', 'stock.picking'), ('name', '=', 'production_ids')],
    ['name', 'ttype', 'relation', 'compute', 'depends', 'store', 'readonly']
], {})

if fields_rec:
    print("Field Definition of production_ids on stock.picking:")
    for f in fields_rec:
        print(f"  Name: {f['name']}")
        print(f"  Type: {f['ttype']}")
        print(f"  Relation: {f['relation']}")
        print(f"  Compute: {f['compute']}")
        print(f"  Depends: {f['depends']}")
        print(f"  Store: {f['store']}")
        print(f"  Readonly: {f['readonly']}")
else:
    print("Field not found or error:", err)
