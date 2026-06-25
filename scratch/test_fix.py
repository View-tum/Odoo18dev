import sys
sys.path.append('c:/365_project/TheCool18e/Dev/server')
import odoo
odoo.tools.config.parse_config(['-c', 'c:/365_project/TheCool18e/Dev/server/odoo.conf'])
registry = odoo.registry('GoldMints_Uat_Manu')

with registry.cursor() as cr:
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
    
    # Let's get the invoice we want to pay
    inv = env['account.move'].search([('name', '=', 'INV-E/26/02/00006')])
    
    if not inv:
        print("Invoice not found")
        sys.exit()
        
    print(f"Invoice: {inv.name}, Total: {inv.amount_total} {inv.currency_id.name}, Residual: {inv.amount_residual} {inv.currency_id.name}")
    print(f"Signed: {inv.amount_total_signed} THB")
    
    # We want to create a payment register for 100,000 THB with 'open' difference handling
    ctx = {
        'active_model': 'account.move',
        'active_ids': inv.ids,
        
    }
    
    pay_journal = env['account.journal'].search([('type', '=', 'bank'), ('company_id', '=', inv.company_id.id)], limit=1)
    thb = env.ref('base.THB')
    
    try:
        # Create wizard
        payment_register = env['account.payment.register'].with_context(**ctx).create({
            'journal_id': pay_journal.id,
            'currency_id': thb.id,
            'payment_date': '2026-05-25',
            'amount': 100000.0,
            'payment_difference_handling': 'open',
            'manual_currency_rate_active': True,
            'manual_currency_rate': 35.0,
            'custom_user_amount': 100000.0,
        })
        
        print(f"Created Wizard! Handling is: {payment_register.payment_difference_handling}")
        
        # Action create payments
        res = payment_register.action_create_payments()
        
        # Check created payment
        payment_id = res.get('res_id')
        if payment_id:
            payment = env['account.payment'].browse(payment_id)
            print(f"Created Payment: {payment.name}, Amount: {payment.amount} {payment.currency_id.name}")
            
            # Check lines
            for line in payment.move_id.line_ids:
                print(f"Line: {line.account_id.name}, Debit: {line.debit}, Credit: {line.credit}")
                
            cr.rollback() # DON'T COMMIT
        else:
            print(f"Action returned: {res}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
