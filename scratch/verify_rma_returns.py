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
    r = session.post(f"{URL}/web/dataset/call_kw", json=payload, timeout=60)
    result = r.json()
    if 'error' in result:
        return None, result['error']
    return result.get('result'), None

print("\n" + "="*70)
print("1. Checking rma.transform.return records status:")
print("="*70)
returns, err = call_kw('rma.transform.return', 'search_read', [[], ['name', 'date', 'state', 'product_from_id', 'product_to_id', 'qty_return', 'source_picking_id', 'return_picking_id', 'credit_note_id']], {'limit': 10, 'order': 'id desc'})
if err:
    print("Error reading rma.transform.return:", err)
else:
    for r in returns:
        print(f"  - {r['name']} | Date: {r['date']} | State: {r['state']}")
        print(f"    Sold: {r['product_from_id']} | Returned: {r['product_to_id']} (qty: {r['qty_return']})")
        print(f"    Source Picking: {r['source_picking_id']}")
        print(f"    Return Picking: {r['return_picking_id']}")
        print(f"    Credit Note: {r['credit_note_id']}")
        print("-" * 40)

if returns:
    last_r = returns[0]
    print("\n" + "="*70)
    print(f"2. Checking moves for the latest RMA return: {last_r['name']}")
    print("="*70)
    
    # Check related picking and moves
    picking_id = last_r['return_picking_id']
    if picking_id:
        picking, err = call_kw('stock.picking', 'search_read', [[['id', '=', picking_id[0]]], ['name', 'state', 'move_ids']], {})
        if picking:
            p = picking[0]
            print(f"Return Picking: {p['name']} | State: {p['state']}")
            if p['move_ids']:
                moves, err = call_kw('stock.move', 'search_read', [[['id', 'in', p['move_ids']]], ['name', 'state', 'quantity', 'product_qty', 'price_unit', 'stock_valuation_layer_ids']], {})
                if moves:
                    print("Moves details:")
                    for m in moves:
                        print(f"  - Move ID {m['id']}: {m['name']} | State: {m['state']} | Qty: {m.get('quantity')} / {m.get('product_qty')} | Cost: {m.get('price_unit')}")
                        print(f"    SVLs: {m['stock_valuation_layer_ids']}")
        else:
            print("No picking found or error:", err)
            
    # Check if there are any other validation layers or errors
