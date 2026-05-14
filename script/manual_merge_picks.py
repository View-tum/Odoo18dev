import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# รายชื่อใบที่ต้องการรวม
master_name = 'GMP/TRPL/02161' # จะใช้ใบนี้เป็นใบหลัก
others_names = ['GMP/TRPL/02160', 'GMP/TRPL/02162']

master = env['stock.picking'].search([('name', '=', master_name)], limit=1)
others = env['stock.picking'].search([('name', 'in', others_names)])

if not master:
    print("ERROR: Master picking %s not found" % master_name)
    sys.exit()

print("Merging into Master: %s (%s)" % (master.name, master.location_id.display_name))

for p in others:
    print("\nProcessing %s (%s)..." % (p.name, p.location_id.display_name))
    moves = p.move_ids.filtered(lambda x: x.state != 'cancel')
    
    for m in moves:
        # สำคัญ: ต้องเปลี่ยน location_id ของ move ให้ตรงกับ master ไม่งั้น Odoo จะแยกใบกลับมาใหม่
        m.write({
            'picking_id': master.id,
            'location_id': master.location_id.id
        })
        print("  - Moved product: %s" % m.product_id.display_name)
    
    # ยกเลิกใบเก่าที่ว่างแล้ว
    p.action_cancel()
    print("  - Canceled empty picking %s" % p.name)

# หลังจากรวมแล้ว ให้สั่ง Merge บรรทัดสินค้าที่ซ้ำกันในใบ Master
master.move_ids._merge_moves()

env.cr.commit()
print("\n=== CURRENT PICKINGS MERGED SUCCESSFULLY ===")
