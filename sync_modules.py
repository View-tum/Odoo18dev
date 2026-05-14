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
                # Check if it has a manifest
                if any(os.path.exists(os.path.join(folder, item, m)) for m in ['__manifest__.py', '__openerp__.py']):
                    module_names.append(item)

print(f"Total custom modules found: {len(module_names)}")

try:
    odoo.tools.config.parse_config(['-c', r'C:\365_project\TheCool18e\Dev\server\odoo.conf', '-d', 'GoldMints_Uat_Manu'])
    registry = odoo.registry('GoldMints_Uat_Manu')
    with registry.cursor() as cr:
        cr.execute("SELECT name, state FROM ir_module_module WHERE name IN %s", (tuple(module_names),))
        res = cr.fetchall()
        status_map = {name: state for name, state in res}
        
        to_install = []
        to_upgrade = []
        
        for name in module_names:
            state = status_map.get(name)
            if state == 'installed':
                to_upgrade.append(name)
            else:
                to_install.append(name)
                
        print(f"To Install: {len(to_install)}")
        print(f"To Upgrade: {len(to_upgrade)}")
        
        if to_install:
            print(f"INSTALL_LIST: {','.join(to_install)}")
        if to_upgrade:
            print(f"UPGRADE_LIST: {','.join(to_upgrade)}")

except Exception as e:
    print(f"Error: {e}")
