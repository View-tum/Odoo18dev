import psycopg2

try:
    conn = psycopg2.connect(
        host="localhost",
        port=5811,
        user="odoo",
        password="123456",
        database="postgres"
    )
    cur = conn.cursor()
    cur.execute("SELECT datname FROM pg_database WHERE datistemplate = false;")
    dbs = cur.fetchall()
    print("Local databases:")
    for db in dbs:
        print(f"  - {db[0]}")
    cur.close()
    conn.close()
except Exception as e:
    print("Error connecting to PostgreSQL:", e)
