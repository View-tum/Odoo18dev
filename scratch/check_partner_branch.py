
import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor

db_name = 'UAT'
db_user = 'odoo'
db_password = '123456'
db_port = 5811

def check_partner_branch():
    try:
        conn = psycopg2.connect(dbname=db_name, user=db_user, password=db_password, host='localhost', port=db_port)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT count(*) FROM res_partner WHERE branch IS NOT NULL AND length(branch) < 5")
        count = cur.fetchone()['count']
        print(f"res_partner non-padded branches count: {count}")
        
        if count > 0:
            cur.execute("SELECT id, name, branch FROM res_partner WHERE branch IS NOT NULL AND length(branch) < 5 LIMIT 20")
            rows = cur.fetchall()
            print("Sample non-padded partners:")
            for row in rows:
                print(f"ID: {row['id']}, Name: {row['name']}, Branch: '{row['branch']}'")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_partner_branch()
