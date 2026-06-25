import sys
sys.path.insert(0, r"C:\365_project\TheCool18e\Dev\server")
import odoo
from odoo import api, SUPERUSER_ID

def run_test():
    odoo.tools.config.parse_config(['-c', r'C:\365_project\TheCool18e\Dev\server\odoo.conf'])
    registry = odoo.registry('GoldMints_Uat_Manu')
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        view = env.ref('account.view_account_payment_register_form')
        print("VIEW ARCH:")
        print(view.arch)

run_test()
