
import sys
import os

# Add odoo to path if needed, but we probably just need to run it via odoo-bin
# Actually, let's just use a simple SQL check via psycopg2 if it's installed in the venv

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("psycopg2 not found")
    sys.exit(1)

# Read config to get db details
config_path = r'c:\365_project\TheCool18e\Dev\server\odoo.conf'
db_name = 'uat'
db_user = 'odoo'
db_password = '123456'
db_port = 5811

def check_data():
    try:
        conn = psycopg2.connect(dbname=db_name, user=db_user, password=db_password, host='localhost', port=db_port)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check res_partner
        cur.execute("SELECT count(*) FROM res_partner WHERE branch IS NOT NULL AND length(branch) < 5")
        partner_count = cur.fetchone()['count']
        print(f"res_partner non-padded branches: {partner_count}")
        
        # Check account_move_tax_invoice
        cur.execute("SELECT count(*) FROM account_move_tax_invoice WHERE branch IS NOT NULL AND length(branch) < 5")
        tax_invoice_count = cur.fetchone()['count']
        print(f"account_move_tax_invoice non-padded branches: {tax_invoice_count}")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_data()
