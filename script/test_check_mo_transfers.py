import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

mos = env['mrp.production'].search([('origin', 'ilike', 'SOD-263216')], order='name asc')
print(f"Total MOs for SOD-263216: {len(mos)}")

picks = env['stock.picking'].search([('group_id', 'in', mos.mapped('procurement_group_id').ids)])
print(f"Total pickings for MO procurement groups: {len(picks)}")
for p in picks:
    print(f"  {p.name} | {p.picking_type_id.name} | {p.location_id.name} -> {p.location_dest_id.name} | origin={p.origin} | group={p.group_id.name}")
    for m in p.move_ids:
        print(f"    {m.product_id.name} qty={m.product_qty} move_group={m.group_id.name}")

# Also check any other picks containing these products
print("\nAny other picks mentioning the MOs in origin?")
other_picks = env['stock.picking'].search([('origin', 'in', mos.mapped('name'))])
for p in other_picks:
    print(f"  {p.name} | {p.picking_type_id.name} | {p.location_id.name} -> {p.location_dest_id.name} | origin={p.origin} | group={p.group_id.name}")

