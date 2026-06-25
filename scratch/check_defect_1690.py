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

# Fetch project.task with ID 1690
task, err = call_kw('project.task', 'search_read', [[('id', '=', 1690)]], {
    'fields': ['name', 'description', 'stage_id', 'user_ids', 'partner_id', 'create_date', 'write_date']
})

if err:
    print("Error fetching task:", err)
elif not task:
    print("Task 1690 not found.")
else:
    t = task[0]
    print(f"Task ID: 1690")
    print(f"Name: {t.get('name')}")
    print(f"Stage: {t.get('stage_id')}")
    print(f"Assigned Users: {t.get('user_ids')}")
    print(f"Partner: {t.get('partner_id')}")
    print(f"Created: {t.get('create_date')}")
    print(f"Modified: {t.get('write_date')}")
    print("\nDescription HTML:")
    print("="*60)
    print(t.get('description'))
    print("="*60)

    # Let's also fetch messages/chatter of the task to get history/discussions
    messages, err = call_kw('mail.message', 'search_read', [
        [('model', '=', 'project.task'), ('res_id', '=', 1690)],
        ['body', 'author_id', 'date', 'subtype_id']
    ], {'order': 'date asc'})
    if messages:
        print("\nChatter / History:")
        print("="*60)
        for m in messages:
            print(f"[{m.get('date')}] Author: {m.get('author_id')}")
            print(f"Body: {m.get('body')}")
            print("-" * 40)
        print("="*60)
