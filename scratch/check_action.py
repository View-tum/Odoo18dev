
import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor

db_name = 'UAT'
db_user = 'odoo'
db_password = '123456'
db_port = 5811

def check_action():
    try:
        conn = psycopg2.connect(dbname=db_name, user=db_user, password=db_password, host='localhost', port=db_port)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT res_model FROM ir_act_window WHERE name->>'en_US' = 'Tax Invoices'")
        row = cur.fetchone()
        if row:
            print(f"Action 'Tax Invoices' uses model: {row['res_model']}")
        else:
            print("Action 'Tax Invoices' not found")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_action()
