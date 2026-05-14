import sys
sys.path.append(r'C:\365_project\TheCool18e\Dev\server')
import odoo

try:
    odoo.tools.config.parse_config(['-c', r'C:\365_project\TheCool18e\Dev\server\odoo.conf', '-d', 'GoldMints_Uat_Manu'])
    registry = odoo.registry('GoldMints_Uat_Manu')
    with registry.cursor() as cr:
        env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
        
        print("Searching for route-like models...")
        for m in env.keys():
            if 'route' in m:
                print(f"Found model: {m}")
        
        # Check stock.route if it exists
        if 'stock.route' in env:
            print(f"stock.route count: {env['stock.route'].search_count([])}")
            
        if 'stock.rule' in env:
            print(f"stock.rule count: {env['stock.rule'].search_count([])}")

        if 'stock.putaway.rule' in env:
            print(f"stock.putaway.rule count: {env['stock.putaway.rule'].search_count([])}")
            
except Exception as e:
    print(f"Error: {e}")
