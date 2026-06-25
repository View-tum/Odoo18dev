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
    
    # Let's search for picking record with comma in origin to see if we can find merged pickings
    cur.execute("""
        SELECT id, name, origin 
        FROM stock_picking 
        WHERE origin LIKE '%,%' AND picking_type_id IN (
            SELECT id FROM stock_picking_type WHERE code = 'internal'
        )
        LIMIT 5;
    """)
    rows = cur.fetchall()
    if rows:
        print("Merged Internal Transfers found in local database:")
        for r in rows:
            picking_id = r[0]
            name = r[1]
            origin = r[2]
            print(f"  - Picking: {name} (ID: {picking_id}) | Origin: {origin}")
            
            # Check production_ids (mrp_production_ids) linked via group_id or other links
            # Wait, since standard Odoo computes production_ids dynamically (Store=False),
            # it is not stored in any direct database column of stock_picking.
            # But let's check what the parser would find:
            import re
            mo_names = re.findall(r"\b(?:GMP|M-WH|WH)/MO[A-Z]*/\d+\b", origin or "")
            print(f"    -> Parsed MO Names: {mo_names}")
    else:
        print("No merged internal transfers (comma in origin) found in local database.")
        
    cur.close()
    conn.close()
except Exception as e:
    print("Error:", e)
