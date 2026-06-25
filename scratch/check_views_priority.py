import sys
sys.path.insert(0, r"C:\365_project\TheCool18e\Dev\server")
import odoo
from odoo import api, SUPERUSER_ID

def run_test():
    odoo.tools.config.parse_config(['-c', r'C:\365_project\TheCool18e\Dev\server\odoo.conf'])
    registry = odoo.registry('GoldMints_Uat_Manu')
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        
        views = env['ir.ui.view'].search([
            ('model', '=', 'account.payment.register'),
            ('type', '=', 'form'),
        ])
        for v in views:
            print(f"ID: {v.id}, Name: {v.name}, Priority: {v.priority}, Active: {v.active}, Inherit ID: {v.inherit_id.name if v.inherit_id else 'None'}, XML ID: {v.get_metadata()[0].get('xmlid')}")
            
run_test()
