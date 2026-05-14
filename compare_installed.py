import sys
sys.path.append(r'C:\365_project\TheCool18e\Dev\server')
import odoo

def get_installed_count(db_name):
    try:
        odoo.tools.config.parse_config(['-c', r'C:\365_project\TheCool18e\Dev\server\odoo.conf', '-d', db_name])
        registry = odoo.registry(db_name)
        with registry.cursor() as cr:
            cr.execute("SELECT count(*) FROM ir_module_module WHERE state = 'installed'")
            return cr.fetchone()[0]
    except Exception as e:
        return f"Error: {e}"

print(f"UAT Installed Count: {get_installed_count('UAT')}")
print(f"GoldMints_Uat_Manu Installed Count: {get_installed_count('GoldMints_Uat_Manu')}")
