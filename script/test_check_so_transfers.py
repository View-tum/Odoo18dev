import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

so = env['sale.order'].search([('name', '=', 'SOD-263215')], limit=1)
if not so:
    print("SO not found")
    sys.exit()

pgs = env['procurement.group'].search([('sale_id', '=', so.id)])
picks = env['stock.picking'].search(['|', ('group_id', 'in', pgs.ids), ('origin', 'ilike', so.name)])

print(f"Total pickings for {so.name}: {len(picks)}")
for p in picks:
    print(f"  Picking: {p.name} | state={p.state} | {p.location_id.name} -> {p.location_dest_id.name} | origin={p.origin} | group={p.group_id.name}")
    for m in p.move_ids:
        print(f"    Move: {m.product_id.name} qty={m.product_qty} move.group={m.group_id.name} move.origin={m.origin}")

mos = env['mrp.production'].search(['|', ('source_sale_order_id', '=', so.id), ('origin', 'ilike', so.name)])
mo_picks = env['stock.picking'].search([('group_id', 'in', mos.mapped('procurement_group_id').ids)])
print(f"\nTotal pickings for MO procurement groups: {len(mo_picks)}")
for p in mo_picks:
    if p not in picks:
        print(f"  Picking: {p.name} | state={p.state} | {p.location_id.name} -> {p.location_dest_id.name} | origin={p.origin} | group={p.group_id.name}")
        for m in p.move_ids:
            print(f"    Move: {m.product_id.name} qty={m.product_qty} move.group={m.group_id.name}")
