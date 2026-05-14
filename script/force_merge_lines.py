import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

pick_name = 'GMP/TRPL/02161'
pick = env['stock.picking'].search([('name', '=', pick_name)], limit=1)

if not pick:
    print("ERROR: Picking %s not found" % pick_name)
    sys.exit()

print("Processing Picking: %s" % pick.name)

# ดึง Move ทั้งหมดที่ไม่ถูกยกเลิก
moves = pick.move_ids.filtered(lambda x: x.state not in ('cancel', 'done'))
products = moves.mapped('product_id')

for product in products:
    p_moves = moves.filtered(lambda x: x.product_id == product)
    if len(p_moves) > 1:
        print("\nMerging Product: %s" % product.display_name)
        
        # ใช้บรรทัดแรกเป็นบรรทัดหลัก
        main_move = p_moves[0]
        other_moves = p_moves[1:]
        
        total_qty = sum(p_moves.mapped('product_uom_qty'))
        print("  - Original lines: %d" % len(p_moves))
        print("  - Total Qty to merge: %.2f" % total_qty)
        
        # ย้ายความเชื่อมโยง (Origin, Destination) มาที่บรรทัดหลัก
        all_orig = list(set(p_moves.mapped('move_orig_ids')))
        all_dest = list(set(p_moves.mapped('move_dest_ids')))
        
        # อัปเดตบรรทัดหลัก
        main_move.write({
            'product_uom_qty': total_qty,
            'move_orig_ids': [(6, 0, [o.id for o in all_orig])],
            'move_dest_ids': [(6, 0, [d.id for d in all_dest])],
        })
        
        # ลบบรรทัดอื่นทิ้ง
        for m in other_moves:
            m._do_unreserve() # คืนค่าการจองก่อนลบ
            m.write({'state': 'draft'}) # เปลี่ยนเป็น draft เพื่อให้ลบได้
            m.unlink()
        
        print("  - Result: 1 Line with Qty %.2f ✅" % total_qty)

# สั่งให้ Odoo ลองจองสินค้าใหม่อีกครั้งเพื่อให้ยอดถูกต้อง
pick.action_assign()

env.cr.commit()
print("\n=== PRODUCT LINES IN %s MERGED SUCCESSFULLY ===" % pick_name)
