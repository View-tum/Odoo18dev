
import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor

db_name = 'UAT'
db_user = 'odoo'
db_password = '123456'
db_port = 5811

def describe_table():
    try:
        conn = psycopg2.connect(dbname=db_name, user=db_user, password=db_password, host='localhost', port=db_port)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT * FROM account_move_tax_invoice LIMIT 0")
        colnames = [desc[0] for desc in cur.description]
        print(f"Real columns in account_move_tax_invoice: {colnames}")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    describe_table()
