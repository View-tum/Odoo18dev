
import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor

db_name = 'UAT'
db_user = 'odoo'
db_password = '123456'
db_port = 5811

def check_module():
    try:
        conn = psycopg2.connect(dbname=db_name, user=db_user, password=db_password, host='localhost', port=db_port)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT name, state FROM ir_module_module WHERE name LIKE 'l10n_th_account_tax%'")
        rows = cur.fetchall()
        for row in rows:
            print(f"Module: {row['name']}, State: {row['state']}")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_module()
