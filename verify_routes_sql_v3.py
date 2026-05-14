import sys
sys.path.append(r'C:\365_project\TheCool18e\Dev\server')
import odoo

def get_count_sql(db_name):
    try:
        odoo.tools.config.parse_config(['-c', r'C:\365_project\TheCool18e\Dev\server\odoo.conf', '-d', db_name])
        # Use direct cursor without loading full registry if possible
        db = odoo.sql_db.db_connect(db_name)
        with db.cursor() as cr:
            # Find the relation table for route_ids on product.template
            cr.execute("SELECT relation FROM ir_model_fields WHERE model = 'product.template' AND name = 'route_ids'")
            res = cr.fetchone()
            if not res:
                return "Field route_ids not found"
            rel_table = res[0].replace('.', '_') # Sometimes it's dot separated in meta but underscore in DB
            
            # Actually let's just find all tables with route and product in name
            cr.execute("SELECT table_name FROM information_schema.tables WHERE table_name LIKE '%route%product%'")
            tables = [r[0] for r in cr.fetchall()]
            
            if not tables:
                return 0
                
            counts = {}
            for table in tables:
                try:
                    cr.execute(f"SELECT COUNT(DISTINCT product_template_id) FROM {table}")
                    counts[table] = cr.fetchone()[0]
                except:
                    cr.rollback()
                    try:
                        cr.execute(f"SELECT COUNT(DISTINCT product_id) FROM {table}")
                        counts[table] = cr.fetchone()[0]
                    except:
                        cr.rollback()
            return counts
    except Exception as e:
        return f"Error: {e}"

print(f"UAT: {get_count_sql('UAT')}")
print(f"GoldMints_Uat_Manu: {get_count_sql('GoldMints_Uat_Manu')}")
