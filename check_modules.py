import sys
sys.path.append(r'C:\365_project\TheCool18e\Dev\server')
import odoo

try:
    odoo.tools.config.parse_config(['-c', r'C:\365_project\TheCool18e\Dev\server\odoo.conf', '-d', 'GoldMints_Uat_Manu'])
    registry = odoo.registry('GoldMints_Uat_Manu')
    with registry.cursor() as cr:
        cr.execute("SELECT name, state FROM ir_module_module WHERE name = 'stock'")
        res = cr.fetchone()
        if res:
            print(f"Module 'stock' status: {res[1]}")
        else:
            print("Module 'stock' not found in ir_module_module table.")
except Exception as e:
    print(f"Error: {e}")
