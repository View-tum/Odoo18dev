import sys
sys.path.append(r'C:\365_project\TheCool18e\Dev\server')
import odoo

def get_count(db_name):
    try:
        odoo.tools.config.parse_config(['-c', r'C:\365_project\TheCool18e\Dev\server\odoo.conf', '-d', db_name])
        registry = odoo.registry(db_name)
        with registry.cursor() as cr:
            # Check for the M2M table for product.template and routes
            # Usually it is stock_route_product or stock_location_route_product_template_rel
            cr.execute("SELECT table_name FROM information_schema.tables WHERE table_name LIKE '%route%product%'")
            tables = [r[0] for r in cr.fetchall()]
            if not tables:
                return 0
            
            # Count distinct product templates in the relation table
            total = 0
            for table in tables:
                cr.execute(f"SELECT COUNT(DISTINCT product_template_id) FROM {table}")
                total += cr.fetchone()[0]
            return total
    except Exception as e:
        return f"Error: {e}"

print(f"UAT: {get_count('UAT')}")
print(f"GoldMints_Uat_Manu: {get_count('GoldMints_Uat_Manu')}")
