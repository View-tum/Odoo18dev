
import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor

db_name = 'UAT'
db_user = 'odoo'
db_password = '123456'
db_port = 5811

def check_field_meta():
    try:
        conn = psycopg2.connect(dbname=db_name, user=db_user, password=db_password, host='localhost', port=db_port)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT name, field_description, ttype, store, state FROM ir_model_fields WHERE model = 'account.move.tax.invoice' AND name = 'branch'")
        row = cur.fetchone()
        if row:
            print(f"Field Meta: {row}")
        else:
            print("Field 'branch' not found in ir_model_fields for account.move.tax.invoice")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_field_meta()
