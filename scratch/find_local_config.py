import os

server_path = r'c:\365_project\TheCool18e\Dev\server'
if os.path.exists(server_path):
    print("Files in server directory:")
    for f in os.listdir(server_path):
        if f.endswith('.conf') or f.endswith('.conf.txt') or f.endswith('.ini') or 'odoo' in f:
            print(f"  - {f}")
else:
    print("Server path does not exist")
