import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

p = env['stock.picking'].search([('name','=','GMP/TRPL/02161')])
print('--- DATABASE STATUS FOR %s ---' % p.name)
print('TOTAL MOVES IN DB: %d' % len(p.move_ids))
for m in p.move_ids:
    print('  - %s | Qty: %.2f | ID: %s | State: %s' % (m.product_id.display_name, m.product_uom_qty, m.id, m.state))
