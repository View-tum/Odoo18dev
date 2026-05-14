
import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor

db_name = 'UAT'
db_user = 'odoo'
db_password = '123456'
db_port = 5811

def check_partner_branch_v2():
    try:
        conn = psycopg2.connect(dbname=db_name, user=db_user, password=db_password, host='localhost', port=db_port)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT branch, count(*) FROM res_partner WHERE branch IS NOT NULL GROUP BY branch ORDER BY count(*) DESC")
        rows = cur.fetchall()
        print("Branch distribution in res_partner:")
        for row in rows:
            print(f" - '{row['branch']}': {row['count']} records")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_partner_branch_v2()
