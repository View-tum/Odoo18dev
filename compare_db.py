import sys
sys.path.append(r'C:\365_project\TheCool18e\Dev\server')
import odoo

def get_product_route_count(db_name):
    try:
        odoo.tools.config.parse_config(['-c', r'C:\365_project\TheCool18e\Dev\server\odoo.conf', '-d', db_name])
        registry = odoo.registry(db_name)
        with registry.cursor() as cr:
            env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
            # Check if product.template has route_ids
            return env['product.template'].search_count([('route_ids', '!=', False)])
    except Exception as e:
        return f"Error: {e}"

print(f"UAT Product Route Count: {get_product_route_count('UAT')}")
print(f"GoldMints_Uat_Manu Product Route Count: {get_product_route_count('GoldMints_Uat_Manu')}")
