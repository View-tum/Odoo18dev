
import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor

db_name = 'UAT'
db_user = 'odoo'
db_password = '123456'
db_port = 5811

def list_all_fields():
    try:
        conn = psycopg2.connect(dbname=db_name, user=db_user, password=db_password, host='localhost', port=db_port)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT name, ttype, store FROM ir_model_fields WHERE model = 'account.move.tax.invoice' ORDER BY name")
        rows = cur.fetchall()
        for row in rows:
            print(f"Field: {row['name']} ({row['ttype']}), Stored: {row['store']}")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_all_fields()
