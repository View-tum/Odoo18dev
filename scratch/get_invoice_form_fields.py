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

v_details, err = call_kw('ir.ui.view', 'search_read', [[('id', '=', 720)]], {'fields': ['arch_db']})
if v_details:
    arch = v_details[0]['arch_db']
    pos = arch.find('name="ref"')
    if pos != -1:
        print("Ref forward context:")
        print(arch[pos-100:pos+800])
