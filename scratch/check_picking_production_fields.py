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

# Fetch stock.picking fields related to production or mrp
fields_info, err = call_kw('stock.picking', 'fields_get', [], {'attributes': ['string', 'type', 'relation']})
if err:
    print("Error fetching fields:", err)
else:
    production_fields = {k: v for k, v in fields_info.items() if 'production' in k or 'mrp' in k or 'mo' in k}
    print("Fields in stock.picking matching production/mrp/mo:")
    for k, v in production_fields.items():
        print(f"  - {k}: type={v.get('type')}, string={v.get('string')}, relation={v.get('relation')}")

    # Let's read the specific pickings and MOs mentioned:
    # MO 1: GMP/MOPL/00169
    # MO 2: GMP/MOPL/00170
    # Merged Transfer No.: GMP/TRPL/00059
    print("\nReading UAT records for validation:")
    mos, err = call_kw('mrp.production', 'search_read', [
        [('name', 'in', ['GMP/MOPL/00169', 'GMP/MOPL/00170'])],
        ['name', 'state', 'origin', 'picking_ids']
    ], {})
    if mos:
        for m in mos:
            print(f"MO: {m['name']} | State: {m['state']} | Origin: {m['origin']} | Pickings: {m['picking_ids']}")
    else:
        print("MOs not found or error:", err)
        
    picking, err = call_kw('stock.picking', 'search_read', [
        [('name', '=', 'GMP/TRPL/00059')],
        []
    ], {})
    if picking:
        p = picking[0]
        print(f"\nPicking: {p['name']} | State: {p['state']} | Origin: {p.get('origin')}")
        # Print fields containing production or mrp or mo
        for k in p:
            if 'production' in k or 'mrp' in k or 'mo' in k or k in ['origin', 'group_id']:
                print(f"  {k}: {p[k]}")
    else:
        print("Picking not found or error:", err)
