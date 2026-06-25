import sys
sys.path.insert(0, r"C:\365_project\TheCool18e\Dev\server")
import odoo
from odoo import api, SUPERUSER_ID

def run_test():
    odoo.tools.config.parse_config(['-c', r'C:\365_project\TheCool18e\Dev\server\odoo.conf'])
    registry = odoo.registry('GoldMints_Uat_Manu')
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        
        move = env['account.move'].search([
            ('move_type', '=', 'in_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ('not_paid', 'partial')),
        ], limit=1)
        
        if not move:
            print("No active move found!")
            return
            
        print("Vendor Bill:", move.name)
        active_ids = move.ids
        
        # Simulate creation context
        ctx = {
            'active_model': 'account.move',
            'active_ids': active_ids,
        }
        
        # Create wizard in memory or DB
        wizard = env['account.payment.register'].with_context(ctx).create({
            'journal_id': 51,
        })
        
        print("Initial fields:")
        print("  is_cheque_outgoing:", wizard.is_cheque_outgoing)
        
        # Get all payment methods
        print("Available payment method lines:")
        for line in wizard.available_payment_method_line_ids:
            print(f"  Line: {line.name} (ID: {line.id}, Code: {line.code})")
            
        cheque_line = wizard.available_payment_method_line_ids.filtered(lambda l: l.code == 'cheque')
        if not cheque_line:
            # Maybe another name? Let's check cheque_outgoing
            cheque_line = wizard.available_payment_method_line_ids.filtered(lambda l: 'cheque' in l.code)
            
        if cheque_line:
            print(f"Selected cheque line: {cheque_line[0].name} (ID: {cheque_line[0].id}, Code: {cheque_line[0].code})")
            
            # Simulate what the web client does when changing payment_method_line_id:
            # It calls onchange with the dict of values.
            specs = wizard._onchange_spec()
            print("Specs for is_cheque_outgoing in view:", 'is_cheque_outgoing' in specs)
            
            # Let's perform onchange call
            values = {
                'payment_method_line_id': cheque_line[0].id,
            }
            res = wizard.onchange(values, ['payment_method_line_id'], specs)
            print("ONCHANGE RESULT VALUES:")
            for k, v in res.get('value', {}).items():
                if 'cheque' in k or 'draft' in k:
                    print(f"  {k}: {v}")
        else:
            print("No cheque payment method line found!")

run_test()
