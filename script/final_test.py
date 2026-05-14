import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Duplicate SOD-263215
so_orig = env['sale.order'].search([('name', '=', 'SOD-263215')], limit=1)
new_so = so_orig.copy()
print("New SO Created: %s" % new_so.name)

# Confirm SO
new_so.action_confirm()
env.cr.commit()
print("SO Confirmed: %s" % new_so.name)

# Find Internal Transfers for THIS SO
# We search for pickings where any move originates from THIS SO's procurement group
picks = env['stock.picking'].search([
    ('group_id', '=', new_so.procurement_group_id.id),
    ('picking_type_id.code', '=', 'internal'),
    ('state', '!=', 'cancel'),
])

print("\n--- PICKING MERGE RESULT (Target: 1 per route/type) ---")
print("Total internal transfers: %d" % len(picks))

for p in picks:
    src = p.location_id.display_name
    dst = p.location_dest_id.display_name
    mfg = p.manufacturing_type or 'NONE'
    print("\n%s | %s -> %s | MfgType: %s" % (p.name, src, dst, mfg))
    
    # Check for product line merging
    prod_counts = {}
    for m in p.move_ids.filtered(lambda x: x.state != 'cancel'):
        pname = m.product_id.display_name
        prod_counts[pname] = prod_counts.get(pname, 0) + 1
    
    dups = {pname: count for pname, count in prod_counts.items() if count > 1}
    if dups:
        print("  !!! FRAGMENTED PRODUCT LINES FOUND:")
        for pname, count in dups.items():
            print("    - %s: %d lines" % (pname, count))
    else:
        print("  ✅ Product lines merged perfectly (Total: %d items)" % len(prod_counts))

# Verify route consistency
routes_found = set((p.location_id.id, p.location_dest_id.id, p.manufacturing_type) for p in picks)
if len(routes_found) == len(picks):
    print("\n>>> SUCCESS: Each route has exactly one picking. <<<")
else:
    print("\n>>> FAILURE: Some routes still have multiple pickings. <<<")

env.cr.rollback()
