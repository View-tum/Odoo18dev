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
    
    menu = env.ref('account_accountant.menu_account_group', raise_if_not_found=False)
    if menu:
        print("Before update:")
        print(f"Menu ID: {menu.id} | Groups: {menu.groups_id.mapped('name')}")
        
        # Change groups to standard accounting users
        group_user = env.ref('account.group_account_user', raise_if_not_found=False)
        if group_user:
            menu.write({'groups_id': [(6, 0, [group_user.id])]})
            env.cr.commit()
            print("Successfully updated menu groups to 'Show Full Accounting Features' (Accountant) group.")
        else:
            # Fallback: clear groups so it inherits parent's groups
            menu.write({'groups_id': [(5, 0, 0)]})
            env.cr.commit()
            print("Cleared menu groups constraint.")
            
        print("After update:")
        print(f"Menu ID: {menu.id} | Groups: {menu.groups_id.mapped('name')}")
    else:
        print("Account Groups menu not found.")
