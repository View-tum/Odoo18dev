import requests
import json
import io
import sys
sys.stdout.reconfigure(encoding='utf-8')

URL = 'http://localhost:3000/api'

# Create dummy csv files in memory
cust_csv = io.BytesIO(b"cust_code,cust_name,tax_no\nC001,John Doe,1234567890123\nC002,Jane Smith,9876543210987\n")
prod_csv = io.BytesIO(b"sku,name,sale_price\nP001,Blue Pen,15.50\nP002,Red Notebook,45.00\n")

print("=" * 100)
print("INTEGRATION TEST: Odoo AI Migration Master Pipeline")
print("=" * 100)

# 1. Create Project
print("\n1. Creating project...")
r = requests.post(f"{URL}/projects", json={"name": "UAT Integration Test"})
print("Response:", r.status_code, r.text)
project_id = r.json()["id"]
print(f"Project ID: {project_id}")

# 2. Scan Odoo (using our UAT connection)
print("\n2. Scanning Odoo...")
conn_payload = {
    "url": "http://10.0.0.14",
    "db": "goldmints_uat",
    "username": "admin",
    "api_key": "365@gmp",
    "mode": "read_only"
}
r2 = requests.post(f"{URL}/projects/{project_id}/scan-odoo", json=conn_payload)
print("Response Status:", r2.status_code)
scan_result = r2.json()
print("Models scanned count:", len(scan_result.get("models_scanned", [])))
print("Reference models count:", len(scan_result.get("reference_models_scanned", [])))

# 3. Upload multiple files
print("\n3. Uploading multiple files...")
files = [
    ("files", ("customers_test.csv", cust_csv, "text/csv")),
    ("files", ("products_test.csv", prod_csv, "text/csv"))
]
r3 = requests.post(f"{URL}/projects/{project_id}/upload", files=files)
print("Response Status:", r3.status_code)
upload_result = r3.json()
print("Upload Result JSON:")
print(json.dumps(upload_result, indent=2, ensure_ascii=False))

# 4. Get Mappings
print("\n4. Retrieving mapping state...")
r4 = requests.get(f"{URL}/projects/{project_id}/mappings")
print("Response Status:", r4.status_code)
mappings_result = r4.json()
for filename, m_data in mappings_result.items():
    print(f"  File: {filename}")
    print(f"    Target Model: {m_data.get('target_model')}")
    print(f"    Mappings Count: {len(m_data.get('mappings', []))}")
    print(f"    Issues Count: {len(m_data.get('issues', []))}")

# 5. Evaluate Cutover
print("\n5. Evaluating Cutover gates...")
gates_payload = {
    "Odoo Connection scanned": True,
    "Source Files Uploaded": True,
    "Schema Mapping Passed": True,
    "TB = GL = JL Reconciled": True
}
r5 = requests.post(f"{URL}/projects/{project_id}/cutover/evaluate", json=gates_payload)
print("Response Status:", r5.status_code)
print(json.dumps(r5.json(), indent=2))

# 6. Run Staging Dry-run
print("\n6. Running Staging Dry-run...")
r6 = requests.post(f"{URL}/projects/{project_id}/migrate", params={"dry_run": True})
print("Response Status:", r6.status_code)
print(json.dumps(r6.json(), indent=2))

print("\nSUCCESS!")
