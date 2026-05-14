
import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor

db_name = 'UAT'
db_user = 'odoo'
db_password = '123456'
db_port = 5811

def check_tables():
    try:
        conn = psycopg2.connect(dbname=db_name, user=db_user, password=db_password, host='localhost', port=db_port)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE '%tax_invoice%'")
        tables = cur.fetchall()
        print(f"Tax invoice like tables: {[t['table_name'] for t in tables]}")
        
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'res_partner' LIMIT 10")
        cols = cur.fetchall()
        print(f"res_partner sample columns: {[c['column_name'] for c in cols]}")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_tables()
