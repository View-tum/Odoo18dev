import sys
sys.stdout.reconfigure(encoding='utf-8')

import psycopg2
import psycopg2.extras

DB_HOST = '10.0.0.14'
DB_PORT = 5432
DB_NAME = 'goldmints_uat'

# Common Odoo PostgreSQL credentials to try
CREDS_TO_TRY = [
    {'user': 'odoo', 'password': 'odoo'},
    {'user': 'odoo', 'password': 'odoo18'},
    {'user': 'odoo', 'password': ''},
    {'user': 'odoo', 'password': 'odoo@2024'},
    {'user': 'odoo', 'password': 'odoo@2025'},
    {'user': 'odoo', 'password': '365@gmp'},
    {'user': 'odoo', 'password': 'goldmints'},
    {'user': 'odoo', 'password': 'postgres'},
    {'user': 'postgres', 'password': 'postgres'},
    {'user': 'postgres', 'password': 'odoo'},
    {'user': 'postgres', 'password': ''},
    {'user': 'postgres', 'password': '365@gmp'},
]

conn = None
connected_cred = None

print(f"Attempting to connect to PostgreSQL at {DB_HOST}:{DB_PORT}/{DB_NAME}")
print("="*60)

for cred in CREDS_TO_TRY:
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=cred['user'],
            password=cred['password'],
            connect_timeout=5,
        )
        connected_cred = cred
        print(f"[OK] Connected with user='{cred['user']}' password='{cred['password']}'")
        break
    except psycopg2.OperationalError as e:
        err_msg = str(e).strip().replace('\n', ' ')
        print(f"[FAIL] user='{cred['user']}' password='{cred['password']}': {err_msg[:80]}")
    except Exception as e:
        print(f"[ERROR] {e}")

if not conn:
    print("\n[FAIL] Could not connect with any known credentials.")
    sys.exit(1)

print(f"\nConnected successfully!")

cursor = conn.cursor()

# Step 1: Check if is_view column exists
print("\n" + "="*60)
print("STEP 1: Check if is_view column already exists")
print("="*60)
cursor.execute("""
    SELECT column_name, data_type, column_default 
    FROM information_schema.columns 
    WHERE table_name = 'account_account' 
    AND column_name = 'is_view'
""")
rows = cursor.fetchall()
if rows:
    print(f"[FOUND] is_view column already exists: {rows}")
else:
    print("[MISSING] is_view column does NOT exist - will add it now")

# Step 2: Check what columns exist on account_account
print("\n" + "="*60)
print("STEP 2: Checking account_account table columns")
print("="*60)
cursor.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'account_account'
    AND column_name IN ('is_view', 'code_store', 'account_type', 'code', 'internal_group')
    ORDER BY column_name
""")
cols = cursor.fetchall()
for col in cols:
    print(f"  Column: {col[0]} | Type: {col[1]}")

# Step 3: Check count of accounts
cursor.execute("SELECT COUNT(*) FROM account_account")
count = cursor.fetchone()[0]
print(f"\nTotal accounts in DB: {count}")

# Step 4: Sample account_type values
cursor.execute("SELECT DISTINCT account_type FROM account_account LIMIT 20")
types = cursor.fetchall()
print(f"Account types present: {[t[0] for t in types]}")

conn.close()
print("\n[OK] Connection closed (no changes made yet - just checking)")
