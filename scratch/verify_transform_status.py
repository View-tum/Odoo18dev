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

# 1. Let's check if the account.account read issue is resolved
print("\n" + "="*70)
print("1. Checking account.account schema / reading works:")
print("="*70)
accs, err = call_kw('account.account', 'search_read', [[], ['name', 'code', 'is_view']], {'limit': 5})
if err:
    print("Error reading account.account:", err)
else:
    print("Successfully read accounts (which means the column is_view exists and Odoo is running fine):")
    for a in accs:
        print(f"  - {a.get('code')} | {a.get('name')} | is_view={a.get('is_view')}")

# 2. Check the product transforms
print("\n" + "="*70)
print("2. Checking product.transform records status:")
print("="*70)
transforms, err = call_kw('product.transform', 'search_read', [[], ['name', 'date', 'state', 'product_from_id', 'product_to_id', 'qty_from', 'qty_to', 'picking_id', 'rma_claim_id']], {'limit': 10, 'order': 'id desc'})
if err:
    print("Error reading product.transform:", err)
else:
    for t in transforms:
        print(f"  - {t['name']} | Date: {t['date']} | State: {t['state']}")
        print(f"    From: {t['product_from_id']} (qty: {t['qty_from']})")
        print(f"    To: {t['product_to_id']} (qty: {t['qty_to']})")
        print(f"    Picking: {t['picking_id']} | RMA Claim: {t['rma_claim_id']}")
        print("-" * 40)

# 3. Check stock.move status for the moves linked to the most recent product.transform
if transforms:
    last_t = transforms[0]
    print("\n" + "="*70)
    print(f"3. Checking moves and valuation for the latest transform: {last_t['name']}")
    print("="*70)
    
    # Read detailed fields of the last transform
    t_detail, err = call_kw('product.transform', 'search_read', [[['id', '=', last_t['id']]], ['move_out_id', 'move_in_id', 'svl_count']], {})
    if t_detail:
        det = t_detail[0]
        print(f"Move Out ID: {det['move_out_id']} | Move In ID: {det['move_in_id']} | SVL Count: {det['svl_count']}")
        
        # Check moves
        move_ids = []
        if det['move_out_id']:
            move_ids.append(det['move_out_id'][0])
        if det['move_in_id']:
            move_ids.append(det['move_in_id'][0])
            
        if move_ids:
            moves, err = call_kw('stock.move', 'search_read', [[['id', 'in', move_ids]], ['name', 'state', 'quantity', 'product_qty', 'price_unit']], {})
            if moves:
                print("Moves details:")
                for m in moves:
                    print(f"  - Move ID {m['id']}: {m['name']} | State: {m['state']} | Qty: {m.get('quantity')} / {m.get('product_qty')} | Cost: {m.get('price_unit')}")
            else:
                print("No moves found or error:", err)
                
            # Check valuation layers (SVLs)
            svls, err = call_kw('stock.valuation.layer', 'search_read', [[['stock_move_id', 'in', move_ids]], ['product_id', 'quantity', 'value', 'unit_cost', 'description']], {})
            if svls:
                print("Valuation Layers details:")
                for s in svls:
                    print(f"  - SVL {s['id']}: {s['description']} | Product: {s['product_id']} | Qty: {s['quantity']} | Value: {s['value']} | Unit Cost: {s['unit_cost']}")
            else:
                print("No SVLs found or error:", err)
                
        # Check if any credit notes or invoices were generated / updated or failed
        print("\n" + "="*70)
        print("4. Checking RMA status and credit note / invoice status:")
        print("="*70)
        # Search for account.move referencing this transform or RMA claim
        # Check our rma_transform_return_id or rma_transform_claim_id on account.move
        moves, err = call_kw('account.move', 'search_read', [
            ['|', ('rma_transform_return_id', '=', last_t['id']), ('rma_transform_claim_id', '!=', False)],
            ['name', 'state', 'move_type', 'amount_total', 'rma_transform_return_id', 'rma_transform_claim_id']
        ], {'limit': 5})
        if moves:
            print("Linked invoices / credit notes:")
            for m in moves:
                print(f"  - {m['name']} | {m['move_type']} | State: {m['state']} | Total: {m['amount_total']}")
                print(f"    rma_transform_return_id: {m['rma_transform_return_id']}")
                print(f"    rma_transform_claim_id: {m['rma_transform_claim_id']}")
        else:
            print("No linked account.moves found or error:", err)
