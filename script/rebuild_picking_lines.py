import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

pick_name = 'GMP/TRPL/02161'
pick = env['stock.picking'].search([('name', '=', pick_name)], limit=1)

if not pick:
    print("ERROR: Picking %s not found" % pick_name)
    sys.exit()

print("Force Re-building Picking: %s" % pick.name)

# 1. รวบรวมข้อมูลสินค้าที่ซ้ำ
moves = pick.move_ids.filtered(lambda x: x.state not in ('cancel', 'done'))
product_map = {} # product_id -> {qty, orig_ids, dest_ids, vals}

for m in moves:
    pid = m.product_id.id
    if pid not in product_map:
        product_map[pid] = {
            'qty': 0,
            'orig_ids': set(),
            'dest_ids': set(),
            'template_move': m # ใช้เป็นต้นแบบ copy ค่าต่างๆ
        }
    
    product_map[pid]['qty'] += m.product_uom_qty
    for o in m.move_orig_ids: product_map[pid]['orig_ids'].add(o.id)
    for d in m.move_dest_ids: product_map[pid]['dest_ids'].add(d.id)

# 2. ลบ Moves เดิมทั้งหมดในใบนี้ (ยกเว้นตัวที่ Cancel/Done ไปแล้ว)
print("Removing old lines...")
moves.write({'state': 'draft'}) # ปลดล็อก state
moves.unlink()

# 3. สร้างใหม่แบบบรรทัดเดียวต่อ 1 สินค้า
print("Re-creating consolidated lines...")
for pid, data in product_map.items():
    tm = data['template_move']
    new_move = env['stock.move'].create({
        'name': tm.name,
        'product_id': pid,
        'product_uom_qty': data['qty'],
        'product_uom': tm.product_uom.id,
        'location_id': pick.location_id.id,
        'location_dest_id': pick.location_dest_id.id,
        'picking_id': pick.id,
        'picking_type_id': pick.picking_type_id.id,
        'group_id': pick.group_id.id,
        'origin': pick.origin,
        'route_ids': [(6, 0, tm.route_ids.ids)],
        'warehouse_id': tm.warehouse_id.id,
        'procure_method': tm.procure_method,
        'move_orig_ids': [(6, 0, list(data['orig_ids']))],
        'move_dest_ids': [(6, 0, list(data['dest_ids']))],
    })
    print("  - Consolidated %s -> Qty %.2f" % (new_move.product_id.display_name, data['qty']))

# 4. ยืนยันและจองสินค้า
pick.action_confirm()
pick.action_assign()

env.cr.commit()
print("\n=== RE-BUILD COMPLETED: %s IS NOW CLEAN ===" % pick_name)
