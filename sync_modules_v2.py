import sys
import os
sys.path.append(r'C:\365_project\TheCool18e\Dev\server')
import odoo

custom_folders = [
    r'C:\365_project\TheCool18e\Dev\custom\goldmints_addon-main',
    r'C:\365_project\TheCool18e\Dev\custom\view_dev'
]

module_names = []
for folder in custom_folders:
    if os.path.exists(folder):
        for item in os.listdir(folder):
            if os.path.isdir(os.path.join(folder, item)):
                if any(os.path.exists(os.path.join(folder, item, m)) for m in ['__manifest__.py', '__openerp__.py']):
                    module_names.append(item)

def get_installed_modules(db_name, filter_names):
    try:
        odoo.tools.config.parse_config(['-c', r'C:\365_project\TheCool18e\Dev\server\odoo.conf', '-d', db_name])
        registry = odoo.registry(db_name)
        with registry.cursor() as cr:
            cr.execute("SELECT name FROM ir_module_module WHERE name IN %s AND state = 'installed'", (tuple(filter_names),))
            return [r[0] for r in cr.fetchall()]
    except Exception as e:
        print(f"Error fetching from {db_name}: {e}")
        return []

print("Fetching installed modules from UAT...")
uat_installed = get_installed_modules('UAT', module_names)
print(f"Total installed in UAT from custom folders: {len(uat_installed)}")

print("Fetching status in GoldMints_Uat_Manu...")
target_installed = get_installed_modules('GoldMints_Uat_Manu', uat_installed)

to_install = [m for m in uat_installed if m not in target_installed]
to_upgrade = target_installed

print(f"To Install: {len(to_install)}")
print(f"To Upgrade: {len(to_upgrade)}")

with open('to_install.txt', 'w') as f:
    f.write(','.join(to_install))
with open('to_upgrade.txt', 'w') as f:
    f.write(','.join(to_upgrade))
