import sys
sys.path.append(r'C:\365_project\TheCool18e\Dev\server')
import odoo

def get_product_route_count(db_name):
    try:
        odoo.tools.config.parse_config(['-c', r'C:\365_project\TheCool18e\Dev\server\odoo.conf', '-d', db_name])
        registry = odoo.registry(db_name)
        with registry.cursor() as cr:
            env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
            # In Odoo 18, it might be stock.route
            route_model = 'stock.route' if 'stock.route' in env else 'stock.location.route'
            return env['product.template'].search_count([('route_ids', '!=', False)])
    except Exception as e:
        return f"Error: {e}"

uat_count = get_product_route_count('UAT')
target_count = get_product_route_count('GoldMints_Uat_Manu')

print(f"UAT Product Route Count: {uat_count}")
print(f"GoldMints_Uat_Manu Product Route Count: {target_count}")
