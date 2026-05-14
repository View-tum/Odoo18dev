
import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor

db_name = 'UAT'
db_user = 'odoo'
db_password = '123456'
db_port = 5811

def find_branch_column():
    try:
        conn = psycopg2.connect(dbname=db_name, user=db_user, password=db_password, host='localhost', port=db_port)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT table_name, column_name FROM information_schema.columns WHERE column_name = 'branch' AND table_schema = 'public'")
        rows = cur.fetchall()
        for row in rows:
            print(f"Table: {row['table_name']}, Column: {row['column_name']}")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    find_branch_column()
