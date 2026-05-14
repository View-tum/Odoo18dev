
import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor

db_name = 'UAT'
db_user = 'odoo'
db_password = '123456'
db_port = 5811

def check_xml_id():
    try:
        conn = psycopg2.connect(dbname=db_name, user=db_user, password=db_password, host='localhost', port=db_port)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT res_id, model FROM ir_model_data WHERE module = 'l10n_th_account_tax' AND name = 'view_move_form'")
        row = cur.fetchone()
        if row:
            print(f"XML ID found: Res ID {row['res_id']}, Model {row['model']}")
            cur.execute(f"SELECT id, name, arch_db::text FROM ir_ui_view WHERE id = {row['res_id']}")
            v = cur.fetchone()
            if v:
                print(f"View Name: {v['name']}")
                print(f"Contains 'branch': {'branch' in v['arch_db']}")
        else:
            print("XML ID 'l10n_th_account_tax.view_move_form' not found")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_xml_id()
