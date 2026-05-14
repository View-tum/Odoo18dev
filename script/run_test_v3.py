import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=== STARTING AUTOMATED VALIDATION TEST ===")

# 1. ค้นหา SO ต้นแบบ (SOD-263215) เพื่อนำสินค้ามาใช้
so_template = env['sale.order'].search([('name', '=', 'SOD-263215')], limit=1)
if not so_template:
    print("ERROR: Template SO not found")
    sys.exit()

# 2. สร้าง SO ใหม่
print("STEP 1: Creating New Sales Order...")
new_so = so_template.copy({
    'client_order_ref': 'TEST-MERGE-AUTO-01',
})
print("  - Created SO: %s" % new_so.name)

# 3. ยืนยัน SO
print("STEP 2: Confirming Sales Order (Triggering MTO)...")
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
    
    # นับจำนวนบรรทัดแยกตามสินค้า
    prod_data = {}
    for m in p.move_ids.filtered(lambda x: x.state != 'cancel'):
        pname = m.product_id.display_name
        prod_data[pname] = prod_data.get(pname, 0) + m.product_uom_qty
    
    # แสดงรายการสินค้าในใบ
    print("  Lines in this picking:")
    for pname, qty in prod_data.items():
        # ตรวจสอบจำนวนบรรทัดจริงใน Odoo (ต้องเป็น 1 ถ้า Merge สำเร็จ)
        actual_lines = len(p.move_ids.filtered(lambda x: x.product_id.display_name == pname and x.state != 'cancel'))
        status = "✅ MERGED (1 Line)" if actual_lines == 1 else "❌ SPLIT (%d Lines)" % actual_lines
        print("    - %s: Qty %.2f | %s" % (pname, qty, status))

# 5. สรุปผล
mfg_types_found = picks.mapped('manufacturing_type')
unique_routes = set((p.location_id.id, p.location_dest_id.id, p.manufacturing_type) for p in picks)

print("\n=== TEST SUMMARY ===")
if len(picks) == len(unique_routes):
    print("RESULT 1: Consolidation per Route/Type -> ✅ PASSED")
else:
    print("RESULT 1: Consolidation per Route/Type -> ❌ FAILED (Found %d picks for %d unique routes)" % (len(picks), len(unique_routes)))

all_merged = all(len(p.move_ids.filtered(lambda x: x.state != 'cancel')) == len(set(p.move_ids.mapped('product_id'))) for p in picks)
if all_merged:
    print("RESULT 2: Product Line Merging -> ✅ PASSED")
else:
    print("RESULT 2: Product Line Merging -> ❌ FAILED")

print("\n>>> All tests completed. Please check the results above. <<<")
