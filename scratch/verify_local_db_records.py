import psycopg2

try:
    conn = psycopg2.connect(
        host="localhost",
        port=5811,
        user="odoo",
        password="123456",
        database="GoldMints_Uat_Manu"
    )
    cur = conn.cursor()
    
    # 1. Check if column warehouse_id exists in account_move
    cur.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='account_move' AND column_name='warehouse_id';
    """)
    res = cur.fetchone()
    if res:
        print("[OK] Column 'warehouse_id' exists in 'account_move' table!")
    else:
        print("[FAIL] Column 'warehouse_id' does NOT exist in 'account_move' table.")
        
    # 2. Check a few computed warehouse values
    cur.execute("""
        SELECT name, invoice_origin, warehouse_id 
        FROM account_move 
        WHERE warehouse_id IS NOT NULL AND name IS NOT NULL 
        LIMIT 5;
    """)
    rows = cur.fetchall()
    if rows:
        print("\nSuccessfully computed warehouse values for existing records:")
        for r in rows:
            print(f"  Invoice: {r[0]} | Origin: {r[1]} | Warehouse ID: {r[2]}")
    else:
        print("\nNo records found with non-null warehouse_id (or they haven't been computed yet).")
        
    cur.close()
    conn.close()
except Exception as e:
    print("Error:", e)
