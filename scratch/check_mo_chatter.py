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

for name in ['GMP/MOPL/00169', 'GMP/MOPL/00170']:
    print(f"\n==================== MO: {name} ====================")
    mo, err = call_kw('mrp.production', 'search_read', [
        [('name', '=', name)],
        ['id', 'state', 'origin']
    ])
    if mo:
        mo_id = mo[0]['id']
        messages, err = call_kw('mail.message', 'search_read', [
            [('model', '=', 'mrp.production'), ('res_id', '=', mo_id)],
            ['body', 'author_id', 'date']
        ])
        if messages:
            for m in messages:
                print(f"[{m['date']}] Author: {m['author_id']} | Body: {m['body']}")
        else:
            print("No messages")
    else:
        print("Not found, error:", err)
