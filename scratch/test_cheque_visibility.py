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
        
        print("Vendor Bill:", move.name if move else "None")
        if not move:
            return
            
        active_ids = move.ids
        register_wizard = env['account.payment.register'].with_context(
            active_model='account.move',
            active_ids=active_ids,
        ).create({
            'journal_id': 51,
        })
        
        print("Payment Type:", register_wizard.payment_type)
        print("Available payment method lines:")
        for line in register_wizard.available_payment_method_line_ids:
            print(f"  Line: {line.name} (ID: {line.id}, Code: {line.code}, is_cheque_outgoing_line: {line.is_cheque_outgoing_line})")
            
        print("Current selected line:", register_wizard.payment_method_line_id.name if register_wizard.payment_method_line_id else "None")
        print("is_cheque_outgoing:", register_wizard.is_cheque_outgoing)
        print("is_bank_draft_outgoing:", register_wizard.is_bank_draft_outgoing)
        
        cheque_line = register_wizard.available_payment_method_line_ids.filtered(lambda l: l.code == 'cheque')
        if cheque_line:
            register_wizard.payment_method_line_id = cheque_line[0].id
            register_wizard._compute_instrument_payment_method()
            print("AFTER SELECTING CHEQUE:")
            print("Current selected line:", register_wizard.payment_method_line_id.name)
            print("is_cheque_outgoing:", register_wizard.is_cheque_outgoing)
            print("is_bank_draft_outgoing:", register_wizard.is_bank_draft_outgoing)
            
run_test()
