import os

paths_to_check = [
    r'c:\365_project',
    r'c:\odoo_ai_migration_master',
    r'c:\odoo',
]

for p in paths_to_check:
    if os.path.exists(p):
        print(f"Checking {p}...")
        for root, dirs, files in os.walk(p):
            if 'odoo-bin' in files or 'odoo-bin.exe' in files:
                print(f"  [FOUND] odoo-bin in: {root}")
            # limit depth to not take too long
            depth = root[len(p):].count(os.sep)
            if depth >= 4:
                # prune dirs
                dirs[:] = []
