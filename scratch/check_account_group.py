import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.append(r"C:\365_project\TheCool18e\Dev\server")
import odoo
from odoo import api, SUPERUSER_ID

odoo.tools.config.parse_config(['-c', r'C:\365_project\TheCool18e\Dev\server\odoo.conf'])

db_name = 'GoldMints_Uat_Manu'
registry = odoo.registry(db_name)

with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    menu = env.ref('account_accountant.menu_account_group')
    print("=== Menu Details ===")
    print(f"Menu ID: {menu.id}")
    print(f"Name: {menu.name}")
    print(f"Active: {menu.active}")
    print(f"Sequence: {menu.sequence}")
    print(f"Action: {menu.action}")
    
    # Groups
    groups = menu.groups_id
    print("\n=== Current Groups ===")
    for g in groups:
        print(f"Group ID={g.id} | Name={g.name} | Category={g.category_id.name if g.category_id else 'None'} | XML ID={g.get_external_id().get(g.id, 'None')}")
        
    # Parent Chain
    print("\n=== Parent Chain ===")
    curr = menu
    while curr:
        print(f"-> Name={curr.name} (ID={curr.id}, XML ID={curr.get_external_id().get(curr.id, 'None')})")
        curr = curr.parent_id
