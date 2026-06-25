import requests

try:
    r = requests.get('http://localhost:8069', timeout=3)
    print("Local Odoo is responsive:", r.status_code)
except Exception as e:
    print("Local Odoo is not responsive:", e)
