import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

pick_name = 'GMP/TRPL/02161'
pick = env['stock.picking'].search([('name', '=', pick_name)], limit=1)

if not pick:
    print("ERROR: Picking %s not found" % pick_name)
    sys.exit()

print("Merging lines of %s by update/cancel method..." % pick.name)

moves = pick.move_ids.filtered(lambda x: x.state not in ('cancel', 'done'))
products = moves.mapped('product_id')

for product in products:
    p_moves = moves.filtered(lambda x: x.product_id == product)
    if len(p_moves) > 1:
        print("\nMerging Product: %s" % product.display_name)
        
        main_move = p_moves[0]
        other_moves = p_moves[1:]
        
        total_qty = sum(p_moves.mapped('product_uom_qty'))
        all_orig = list(set(p_moves.mapped('move_orig_ids')))
        all_dest = list(set(p_moves.mapped('move_dest_ids')))
        
        # 1. อัปเดตบรรทัดหลักให้เป็นยอดรวม และเก็บ Link ทั้งหมดไว้
        main_move.write({
            'product_uom_qty': total_qty,
            'move_orig_ids': [(6, 0, [o.id for o in all_orig])],
            'move_dest_ids': [(6, 0, [d.id for d in all_dest])],
        })
        
        # 2. ยกเลิกบรรทัดที่เหลือ (แทนการลบ)
        for m in other_moves:
            m._do_unreserve()
            m._action_cancel() # สั่ง Cancel ตามกระบวนการของ Odoo
            print("  - Canceled move ID: %s" % m.id)
        
        print("  - Result: Merged into ID %s with Qty %.2f" % (main_move.id, total_qty))

# สั่งจองสินค้าใหม่เพื่อให้ยอดจองกลับมาที่บรรทัดหลัก
pick.action_assign()

env.cr.commit()
print("\n=== MERGE COMPLETED VIA CANCEL METHOD ===")
