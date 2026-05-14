
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

# Handle UTF-8 output for Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

db_params = {
    'dbname': 'UAT',
    'user': 'odoo',
    'password': '123456',
    'host': 'localhost',
    'port': 5811
}

def check_module_and_fields():
    try:
        conn = psycopg2.connect(**db_params)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 1. Check module state
        cur.execute("""
            SELECT name, state, latest_version 
            FROM ir_module_module 
            WHERE name LIKE 'l10n_th%' 
            AND state = 'installed'
        """)
        modules = cur.fetchall()
        print("Installed Localization Modules:")
        for m in modules:
            print(f"- {m['name']}: {m['state']} (v{m['latest_version']})")
        
        # 2. Check model fields for account.move.tax.invoice
        # Removing 'modules' field which caused error
        cur.execute("""
            SELECT name, field_description, ttype, state
            FROM ir_model_fields
            WHERE model = 'account.move.tax.invoice'
            ORDER BY name
        """)
        fields = cur.fetchall()
        print("\nFields in account.move.tax.invoice:")
        found_branch = False
        for f in fields:
            if f['name'] == 'branch':
                found_branch = True
            print(f"- {f['name']} ({f['ttype']}): {f['field_description']} [State: {f['state']}]")
            
        if not found_branch:
            print("\n!!! 'branch' field NOT FOUND in ir_model_fields for model 'account.move.tax.invoice'")
            
        # 3. Check if table exists and columns
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'account_move_tax_invoice'
            ORDER BY column_name
        """)
        cols = cur.fetchall()
        print("\nPhysical columns in account_move_tax_invoice:")
        if not cols:
            print("Table 'account_move_tax_invoice' DOES NOT EXIST in public schema.")
        else:
            for c in cols:
                print(f"- {c['column_name']} ({c['data_type']})")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_module_and_fields()
