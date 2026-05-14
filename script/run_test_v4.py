import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=== STARTING AUTOMATED VALIDATION TEST (V4) ===")

# 1. หา SO ล่าสุดที่มีสินค้า MTO
so_template = env['sale.order'].search([('state', 'in', ('sale', 'done'))], order='id desc', limit=1)
if not so_template:
    print("ERROR: No SO found in system to use as template")
    sys.exit()

print("Using Template SO: %s" % so_template.name)

# 2. สร้าง SO ใหม่
print("STEP 1: Creating New Sales Order...")
new_so = so_template.copy({
    'client_order_ref': 'TEST-MERGE-AUTO-V4',
})
print("  - Created SO: %s" % new_so.name)

# 3. ยืนยัน SO
print("STEP 2: Confirming Sales Order...")
new_so.action_confirm()
env.cr.commit()
print("  - SO Confirmed: %s" % new_so.name)

# 4. ตรวจสอบ Internal Transfers
print("\nSTEP 3: Checking Internal Transfers...")
picks = env['stock.picking'].search([
    ('group_id', '=', new_so.procurement_group_id.id),
    ('picking_type_id.code', '=', 'internal'),
    ('state', '!=', 'cancel'),
])

print("  - Total internal transfers found: %d" % len(picks))

for p in picks:
    src = p.location_id.display_name
    dst = p.location_dest_id.display_name
    mfg = p.manufacturing_type or 'N/A'
    print("\n  [Picking: %s]" % p.name)
    print("  Route: %s -> %s" % (src, dst))
    print("  Mfg Type: %s" % mfg)
    
    prod_data = {}
    for m in p.move_ids.filtered(lambda x: x.state != 'cancel'):
        pname = m.product_id.display_name
        prod_data[pname] = prod_data.get(pname, 0) + m.product_uom_qty
    
    print("  Lines in this picking:")
    for pname, qty in prod_data.items():
        actual_lines = len(p.move_ids.filtered(lambda x: x.product_id.display_name == pname and x.state != 'cancel'))
        status = "✅ MERGED (1 Line)" if actual_lines == 1 else "❌ SPLIT (%d Lines)" % actual_lines
        print("    - %s: Qty %.2f | %s" % (pname, qty, status))

# 5. สรุปผล
unique_routes = set((p.location_id.id, p.location_dest_id.id, p.manufacturing_type) for p in picks)

print("\n=== TEST SUMMARY ===")
if picks and len(picks) == len(unique_routes):
    print("RESULT 1: Consolidation per Route/Type -> ✅ PASSED")
elif not picks:
    print("RESULT 1: No internal transfers generated (Check MTO settings) -> ⚠️ WARNING")
else:
    print("RESULT 1: Consolidation per Route/Type -> ❌ FAILED")

all_merged = all(len(p.move_ids.filtered(lambda x: x.state != 'cancel')) == len(set(p.move_ids.mapped('product_id'))) for p in picks)
if picks and all_merged:
    print("RESULT 2: Product Line Merging -> ✅ PASSED")
elif not picks:
    print("RESULT 2: N/A -> ⚠️ WARNING")
else:
    print("RESULT 2: Product Line Merging -> ❌ FAILED")

print("\n>>> All tests completed. <<<")
