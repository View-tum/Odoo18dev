
import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor

db_user = 'odoo'
db_password = '123456'
db_port = 5811

def check_db(name):
    print(f"\nChecking database: {name}")
    try:
        conn = psycopg2.connect(dbname=name, user=db_user, password=db_password, host='localhost', port=db_port)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check res_partner columns
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'res_partner' AND column_name = 'branch'")
        res = cur.fetchone()
        print(f"res_partner has 'branch': {res is not None}")
        
        # Check account_move_tax_invoice columns
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'account_move_tax_invoice' AND column_name = 'branch'")
        res = cur.fetchone()
        print(f"account_move_tax_invoice has 'branch': {res is not None}")
        
        if res:
             # If branch exists, check for non-padded values
             cur.execute("SELECT count(*) FROM account_move_tax_invoice WHERE branch IS NOT NULL AND length(branch) < 5")
             count = cur.fetchone()['count']
             print(f"account_move_tax_invoice non-padded branches: {count}")
             
             if count > 0:
                 cur.execute("SELECT id, branch FROM account_move_tax_invoice WHERE branch IS NOT NULL AND length(branch) < 5 LIMIT 10")
                 rows = cur.fetchall()
                 print(f"Sample non-padded rows: {rows}")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error connecting to {name}: {e}")

if __name__ == "__main__":
    check_db('UAT')
    check_db('uat')
