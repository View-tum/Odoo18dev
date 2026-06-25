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

# Let's read some invoices and see what we can find for warehouse
moves, err = call_kw('account.move', 'search_read', [
    [('move_type', '=', 'out_invoice'), ('state', '=', 'posted')],
    ['name', 'invoice_origin', 'invoice_line_ids']
], {'limit': 15})

if moves:
    print("Tracing warehouse for 15 posted invoices:")
    for m in moves:
        line_ids = m['invoice_line_ids']
        warehouse = None
        if line_ids:
            # Search for sale lines in these invoice lines
            lines, err = call_kw('account.move.line', 'search_read', [
                [('id', 'in', line_ids)],
                ['product_id', 'sale_line_ids']
            ], {})
            if lines:
                sale_line_ids = []
                for l in lines:
                    if l.get('sale_line_ids'):
                        sale_line_ids.extend(l['sale_line_ids'])
                
                if sale_line_ids:
                    so_lines, err = call_kw('sale.order.line', 'search_read', [
                        [('id', 'in', sale_line_ids)],
                        ['order_id']
                    ], {})
                    if so_lines:
                        so_ids = list(set(sl['order_id'][0] for sl in so_lines if sl.get('order_id')))
                        if so_ids:
                            sos, err = call_kw('sale.order', 'search_read', [
                                [('id', 'in', so_ids)],
                                ['warehouse_id']
                            ], {})
                            if sos:
                                warehouse = sos[0]['warehouse_id']
        print(f"Invoice: {m['name']} | Origin: {m['invoice_origin']} | Computed Warehouse: {warehouse}")
else:
    print("No out_invoices found or error:", err)
