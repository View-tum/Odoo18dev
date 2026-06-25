import requests

try:
    r = requests.get('http://localhost:8812', timeout=3)
    print("Local Odoo on 8812 is responsive:", r.status_code)
except Exception as e:
    print("Local Odoo on 8812 is not responsive:", e)
