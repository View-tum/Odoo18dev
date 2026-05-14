import sys
sys.path.append(r'C:\365_project\TheCool18e\Dev\server')
import odoo

try:
    odoo.tools.config.parse_config(['-c', r'C:\365_project\TheCool18e\Dev\server\odoo.conf', '-d', 'GoldMints_Uat_Manu'])
    registry = odoo.registry('GoldMints_Uat_Manu')
    with registry.cursor() as cr:
        env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
        
        print(f"--- Models in Env (Sample) ---")
        models = list(env.keys())
        print(f"Total models: {len(models)}")
        print(f"First 10 models: {models[:10]}")
        
        # Check specifically for stock models
        stock_models = [m for m in models if 'stock' in m]
        print(f"Stock related models: {stock_models[:20]}")
        
        if 'stock.location.route' in env:
            print("SUCCESS: stock.location.route FOUND")
            print(f"Count: {env['stock.location.route'].search_count([])}")
        else:
            print("FAILURE: stock.location.route NOT FOUND")
            
except Exception as e:
    print(f"Error: {e}")
