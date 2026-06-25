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

picking, err = call_kw('stock.picking', 'search_read', [[('name', '=', 'GMP/TRPL/00059')]], {})
if picking:
    p = picking[0]
    print(f"Picking: {p['name']} | ID: {p['id']}")
    print(f"  group_id: {p['group_id']}")
    print(f"  move_ids: {p['move_ids']}")
    
    if p['move_ids']:
        moves, err = call_kw('stock.move', 'search_read', [
            [('id', 'in', p['move_ids'])],
            ['name', 'product_id', 'group_id', 'move_dest_ids', 'raw_material_production_id']
        ])
        if err:
            print("Error reading moves:", err)
        elif moves:
            for m in moves:
                print(f"\nMove ID: {m['id']} | Name: {m['name']} | Product: {m['product_id']}")
                print(f"  group_id: {m['group_id']}")
                print(f"  raw_material_production_id: {m['raw_material_production_id']}")
                print(f"  move_dest_ids: {m['move_dest_ids']}")
                
                if m['move_dest_ids']:
                    dests, err = call_kw('stock.move', 'search_read', [
                        [('id', 'in', m['move_dest_ids'])],
                        ['name', 'product_id', 'raw_material_production_id', 'group_id']
                    ])
                    if err:
                        print("Error reading dests:", err)
                    elif dests:
                        for d in dests:
                            print(f"    -> Dest Move ID: {d['id']} | Name: {d['name']}")
                            print(f"       raw_material_production_id: {d['raw_material_production_id']}")
                            print(f"       group_id: {d['group_id']}")
        else:
            print("No moves returned.")
else:
    print("Picking not found")
