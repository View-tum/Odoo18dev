import sys
import psycopg2
from psycopg2.extras import RealDictCursor

sys.stdout.reconfigure(encoding='utf-8')

db_name = 'GoldMints_Uat_Manu'
db_user = 'odoo'
db_password = '123456'
db_port = 5811

def inspect():
    try:
        conn = psycopg2.connect(dbname=db_name, user=db_user, password=db_password, host='localhost', port=db_port)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT id, name, is_cheque_incoming, is_cheque_outgoing, is_bank_draft_incoming, is_bank_draft_outgoing 
            FROM account_journal
            WHERE id = 51
        """)
        journals = cur.fetchall()
        print("JOURNAL 51:")
        for j in journals:
            print(f"ID: {j['id']}, Name: {j['name']}, is_cheque_incoming: {j['is_cheque_incoming']}, is_cheque_outgoing: {j['is_cheque_outgoing']}, is_bank_draft_incoming: {j['is_bank_draft_incoming']}, is_bank_draft_outgoing: {j['is_bank_draft_outgoing']}")
            
            cur.execute("""
                SELECT l.id, l.name, l.is_cheque_incoming_line, l.is_cheque_outgoing_line, l.payment_method_id, pm.code
                FROM account_payment_method_line l
                LEFT JOIN account_payment_method pm ON pm.id = l.payment_method_id
                WHERE l.journal_id = %s
            """, (j['id'],))
            lines = cur.fetchall()
            print("  PAYMENT METHOD LINES:")
            for l in lines:
                print(f"    Line ID: {l['id']}, Name: {l['name']}, Code: {l['code']}, is_cheque_incoming_line: {l['is_cheque_incoming_line']}, is_cheque_outgoing_line: {l['is_cheque_outgoing_line']}, payment_method_id: {l['payment_method_id']}")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error in inspect: {type(e).__name__}: {e}")

if __name__ == "__main__":
    inspect()
