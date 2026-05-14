import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

so = env['sale.order'].search([('name', '=', 'SOD-263228')])
print("SO: %s | state: %s" % (so.name, so.state))

all_mos = env['mrp.production'].search([('source_sale_order_id', '=', so.id), ('state', '!=', 'cancel')])
print("Active MOs: %d" % len(all_mos))

all_pg_ids = list(set(m.procurement_group_id.id for m in all_mos))
all_pg_ids.append(so.procurement_group_id.id)
picks = env['stock.picking'].search([
    ('group_id', 'in', all_pg_ids),
    ('picking_type_id.code', '=', 'internal'),
    ('state', '!=', 'cancel'),
])
print("Active internal transfers: %d" % len(picks))

print("\nCancelling MOs...")
for mo in all_mos:
    if mo.state not in ('done', 'cancel'):
        mo.action_cancel()
print("MOs cancelled")

picks_to_cancel = env['stock.picking'].search([
    ('group_id', 'in', all_pg_ids),
    ('state', 'not in', ('done', 'cancel')),
])
print("Cancelling %d pickings..." % len(picks_to_cancel))
picks_to_cancel.action_cancel()
print("Pickings cancelled")

print("\nCancelling SO...")
so.action_cancel()
print("SO cancelled")

env.cr.commit()
print("\nDONE - Ready for fresh test")
