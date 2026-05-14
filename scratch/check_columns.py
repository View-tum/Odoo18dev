
import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor

db_name = 'UAT'
db_user = 'odoo'
db_password = '123456'
db_port = 5811

def check_columns():
    try:
        conn = psycopg2.connect(dbname=db_name, user=db_user, password=db_password, host='localhost', port=db_port)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'res_partner' AND column_name LIKE '%branch%'")
        cols = cur.fetchall()
        print(f"res_partner branch-like columns: {[c['column_name'] for c in cols]}")
        
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'account_move_tax_invoice' AND column_name LIKE '%branch%'")
        cols = cur.fetchall()
        print(f"account_move_tax_invoice branch-like columns: {[c['column_name'] for c in cols]}")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_columns()
