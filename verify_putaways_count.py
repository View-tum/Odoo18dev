import sys
sys.path.append(r'C:\365_project\TheCool18e\Dev\server')
import odoo

def get_putaway_count(db_name):
    try:
        odoo.tools.config.parse_config(['-c', r'C:\365_project\TheCool18e\Dev\server\odoo.conf', '-d', db_name])
        db = odoo.sql_db.db_connect(db_name)
        with db.cursor() as cr:
            cr.execute("SELECT COUNT(*) FROM stock_putaway_rule")
            return cr.fetchone()[0]
    except Exception as e:
        return f"Error: {e}"

print(f"UAT Putaways: {get_putaway_count('UAT')}")
print(f"GoldMints_Uat_Manu Putaways: {get_putaway_count('GoldMints_Uat_Manu')}")
