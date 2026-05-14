
import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor

db_name = 'UAT'
db_user = 'odoo'
db_password = '123456'
db_port = 5811

def check_branch_padding_v3():
    try:
        conn = psycopg2.connect(dbname=db_name, user=db_user, password=db_password, host='localhost', port=db_port)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check for branch IDs that are not 5 digits long (either shorter or longer)
        # And also check if they are numeric
        cur.execute("""
            SELECT id, name, branch, length(trim(branch)) as trimmed_len 
            FROM res_partner 
            WHERE branch IS NOT NULL 
            AND (length(trim(branch)) != 5)
            LIMIT 20
        """)
        rows = cur.fetchall()
        print(f"Partners with non-5-digit branches (trimmed):")
        for row in rows:
            print(f"ID: {row['id']}, Name: {row['name']}, Branch: '{row['branch']}' (Len: {row['trimmed_len']})")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_branch_padding_v3()
