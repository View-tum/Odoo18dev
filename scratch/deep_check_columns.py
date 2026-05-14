
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
        
        table = 'account_move_tax_invoice'
        print(f"Listing all columns for {table} in {db_name}:")
        cur.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table}' ORDER BY column_name")
        cols = cur.fetchall()
        for col in cols:
            print(f" - {col['column_name']} ({col['data_type']})")
        
        print("\nSearching for any column containing 'branch' in ANY table:")
        cur.execute("SELECT table_name, column_name FROM information_schema.columns WHERE column_name LIKE '%branch%' AND table_schema = 'public' ORDER BY table_name")
        rows = cur.fetchall()
        for row in rows:
            print(f" - {row['table_name']}.{row['column_name']}")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_columns()
