
import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor

db_name = 'UAT'
db_user = 'odoo'
db_password = '123456'
db_port = 5811

def check_account_move_cols():
    try:
        conn = psycopg2.connect(dbname=db_name, user=db_user, password=db_password, host='localhost', port=db_port)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'account_move' AND column_name LIKE '%branch%'")
        rows = cur.fetchall()
        print(f"account_move branch-like columns: {[r['column_name'] for r in rows]}")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_account_move_cols()
