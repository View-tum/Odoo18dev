import sys
sys.path.append(r'C:\365_project\TheCool18e\Dev\server')
import odoo

def get_product_route_count_sql(db_name):
    try:
        odoo.tools.config.parse_config(['-c', r'C:\365_project\TheCool18e\Dev\server\odoo.conf', '-d', db_name])
        registry = odoo.registry(db_name)
        with registry.cursor() as cr:
            # Query the many2many table between product.template and stock.route
            # The table name is usually product_route_rel or stock_route_product
            # Let's find the table name first
            cr.execute("SELECT relation FROM ir_model_fields WHERE model = 'product.template' AND name = 'route_ids'")
            rel_table = cr.fetchone()[0]
            
            cr.execute(f"SELECT COUNT(DISTINCT product_template_id) FROM {rel_table}")
            return cr.fetchone()[0]
    except Exception as e:
        return f"Error: {e}"

uat_count = get_product_route_count_sql('UAT')
target_count = get_product_route_count_sql('GoldMints_Uat_Manu')

print(f"UAT Product Route Count: {uat_count}")
print(f"GoldMints_Uat_Manu Product Route Count: {target_count}")
