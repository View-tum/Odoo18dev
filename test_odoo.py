
import urllib.request, json
import urllib.parse

db = 'goldmints_uat'
user = 'admin'
pwd = '365@gmp'
url = 'http://10.0.0.14/web/session/authenticate'

data = json.dumps({'jsonrpc': '2.0', 'method': 'call', 'params': {'db': db, 'login': user, 'password': pwd}, 'id': 1}).encode()
req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
resp = urllib.request.urlopen(req)
result = json.loads(resp.read().decode()).get('result')

cookie = resp.info().get('Set-Cookie')
if cookie:
    session_id = cookie.split(';')[0]
    
    call_url = 'http://10.0.0.14/web/dataset/call_kw/account.asset/fields_get'
    call_data = json.dumps({
        'jsonrpc': '2.0',
        'method': 'call',
        'params': {
            'model': 'account.asset',
            'method': 'fields_get',
            'args': [],
            'kwargs': {'attributes': ['string', 'type', 'help']}
        },
        'id': 2
    }).encode()
    call_req = urllib.request.Request(call_url, data=call_data, headers={'Content-Type': 'application/json', 'Cookie': session_id})
    call_resp = urllib.request.urlopen(call_req).read().decode()
    fields = json.loads(call_resp).get('result')
    with open('asset_fields.json', 'w', encoding='utf-8') as f:
        json.dump(fields, f, ensure_ascii=False, indent=2)

