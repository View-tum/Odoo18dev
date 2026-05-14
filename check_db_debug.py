import sys
sys.path.append(r'C:\365_project\TheCool18e\Dev\server')
import odoo

try:
    odoo.tools.config.parse_config(['-c', r'C:\365_project\TheCool18e\Dev\server\odoo.conf', '-d', 'GoldMints_Uat_Manu'])
    registry = odoo.registry('GoldMints_Uat_Manu')
    with registry.cursor() as cr:
        cr.execute("SELECT model FROM ir_model WHERE model LIKE 'stock.location.route'")
        res = cr.fetchone()
        print(f"Model stock.location.route in ir_model: {res}")
        
        cr.execute("SELECT name, state FROM ir_module_module WHERE name = 'stock'")
        mod = cr.fetchone()
        print(f"Module stock status: {mod}")
except Exception as e:
    print(f"Error: {e}")
