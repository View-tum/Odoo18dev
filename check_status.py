import sys
sys.path.append(r'C:\365_project\TheCool18e\Dev\server')
import odoo

try:
    odoo.tools.config.parse_config(['-c', r'C:\365_project\TheCool18e\Dev\server\odoo.conf', '-d', 'GoldMints_Uat_Manu'])
    registry = odoo.registry('GoldMints_Uat_Manu')
    with registry.cursor() as cr:
        cr.execute("SELECT name, state FROM ir_module_module WHERE name = 'account_partner_settlement'")
        res = cr.fetchone()
        print(f"Status of account_partner_settlement: {res}")
        
        # Check how many are actually installed
        cr.execute("SELECT count(*) FROM ir_module_module WHERE state = 'installed'")
        count = cr.fetchone()[0]
        print(f"Total installed modules: {count}")
except Exception as e:
    print(f"Error: {e}")
