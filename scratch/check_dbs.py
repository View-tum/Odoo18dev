
import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor

db_user = 'odoo'
db_password = '123456'
db_port = 5811

def check_databases():
    try:
        conn = psycopg2.connect(dbname='postgres', user=db_user, password=db_password, host='localhost', port=db_port)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT datname FROM pg_database WHERE datistemplate = false")
        dbs = cur.fetchall()
        print(f"Databases: {[d['datname'] for d in dbs]}")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_databases()
