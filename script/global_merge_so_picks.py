import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ค้นหา SO และรายการโอนสินค้าทั้งหมดที่เกี่ยวข้อง
so = env['sale.order'].search([('name', '=', 'SOD-263228')], limit=1)
if not so:
    print("ERROR: SO SOD-263228 not found")
    sys.exit()

picks = env['stock.picking'].search([
    ('group_id', '=', so.procurement_group_id.id),
    ('picking_type_id.code', '=', 'internal'),
    ('state', 'not in', ('cancel', 'done'))
])

print("Scanning %d pickings for SO %s..." % (len(picks), so.name))

for pick in picks:
    print("\n--- Checking %s ---" % pick.name)
    moves = pick.move_ids.filtered(lambda x: x.state not in ('cancel', 'done'))
    products = moves.mapped('product_id')
    
    any_merged = False
    for product in products:
        p_moves = moves.filtered(lambda x: x.product_id == product)
        if len(p_moves) > 1:
            print("  Merging Duplicate Product: %s (%d lines)" % (product.display_name, len(p_moves)))
            
            main_move = p_moves[0]
            other_moves = p_moves[1:]
            
            total_qty = sum(p_moves.mapped('product_uom_qty'))
            all_orig = list(set(p_moves.mapped('move_orig_ids')))
            all_dest = list(set(p_moves.mapped('move_dest_ids')))
            
            main_move.write({
                'product_uom_qty': total_qty,
                'move_orig_ids': [(6, 0, [o.id for o in all_orig])],
                'move_dest_ids': [(6, 0, [d.id for d in all_dest])],
            })
            
            for m in other_moves:
                m._do_unreserve()
                m._action_cancel()
            
            any_merged = True
            print("  ✅ Done.")
            
    if not any_merged:
        print("  ✅ No duplicate product lines found.")
    else:
        pick.action_assign() # จองสินค้าใหม่

env.cr.commit()
print("\n=== GLOBAL PRODUCT LINE CHECK COMPLETED ===")
