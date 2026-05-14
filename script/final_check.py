import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Get the latest confirmed SO
so = env['sale.order'].search([('state', '=', 'sale')], order='id desc', limit=1)
print("Testing Latest SO: %s | state: %s" % (so.name, so.state))

picks = env['stock.picking'].search([
    ('group_id', '=', so.procurement_group_id.id),
    ('picking_type_id.code', '=', 'internal'),
    ('state', '!=', 'cancel'),
])

print("\n--- Picking Summary ---")
print("Total internal transfers: %d" % len(picks))

for p in picks:
    print("\n%s | %s -> %s" % (p.name, p.location_id.display_name, p.location_dest_id.display_name))
    
    # Check for product line merging
    prod_counts = {}
    for m in p.move_ids.filtered(lambda x: x.state != 'cancel'):
        prod_counts[m.product_id] = prod_counts.get(m.product_id, 0) + 1
    
    dups = {prod: count for prod, count in prod_counts.items() if count > 1}
    if dups:
        print("  !!! FRAGMENTED PRODUCT LINES FOUND:")
        for prod, count in dups.items():
            print("    %s: %d lines" % (prod.display_name, count))
    else:
        print("  ✅ All product lines merged (Total products: %d)" % len(prod_counts))

if not picks:
    print("\nNo transfers found for this SO.")
