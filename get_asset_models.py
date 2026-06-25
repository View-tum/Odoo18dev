
import urllib.request, json

db = 'goldmints_uat'
user = 'admin'
pwd = '365@gmp'
url = 'http://10.0.0.14/web/session/authenticate'

data = json.dumps({'jsonrpc': '2.0', 'method': 'call', 'params': {'db': db, 'login': user, 'password': pwd}, 'id': 1}).encode()
req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
resp = urllib.request.urlopen(req)

cookie = resp.info().get('Set-Cookie')
if cookie:
    session_id = cookie.split(';')[0]
    
    call_url = 'http://10.0.0.14/web/dataset/call_kw/account.asset/search_read'
    call_data = json.dumps({
        'jsonrpc': '2.0',
        'method': 'call',
        'params': {
            'model': 'account.asset',
            'method': 'search_read',
            'args': [[['state', '=', 'model']]],
            'kwargs': {'fields': ['name', 'method_number', 'method_period', 'prorata_computation_type', 'account_asset_id', 'account_depreciation_id', 'account_depreciation_expense_id', 'journal_id', 'method', 'method_progress_factor']}
        },
        'id': 2
    }).encode()
    call_req = urllib.request.Request(call_url, data=call_data, headers={'Content-Type': 'application/json', 'Cookie': session_id})
    call_resp = urllib.request.urlopen(call_req).read().decode()
    records = json.loads(call_resp).get('result', [])
    
    md = '# ??????? Asset Models ??????????????? Odoo 14 (10.0.0.14)\n\n'
    md += '| ID | ???? Asset Model (Name) | ???????????????? (Method) | ???????? (Duration) | ?????????????? | ?????????????????? | ?????????????? (Expense) |\n'
    md += '|---|---|---|---|---|---|---|\n'
    
    for r in records:
        name = r.get('name', '')
        method = r.get('method', '')
        duration = f"{r.get('method_number', 0)} {r.get('method_period', '')}"
        
        acc_asset = r.get('account_asset_id', [0, ''])[1] if r.get('account_asset_id') else ''
        acc_depr = r.get('account_depreciation_id', [0, ''])[1] if r.get('account_depreciation_id') else ''
        acc_exp = r.get('account_depreciation_expense_id', [0, ''])[1] if r.get('account_depreciation_expense_id') else ''
        
        md += f'| {r.get("id")} | {name} | {method} | {duration} | {acc_asset} | {acc_depr} | {acc_exp} |\n'
        
    with open('asset_models_list.md', 'w', encoding='utf-8') as f:
        f.write(md)

