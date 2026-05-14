import os
log_path = r'c:\365_project\TheCool18e\Dev\script\merge_log.txt'

with open(log_path, 'w', encoding='utf-8') as f:
    f.write("--- GLOBAL MERGE LOG ---\n")
    
    # ลองค้นหาแบบกว้างขึ้น
    so_name = 'SO263228'
    so = env['sale.order'].search([('name', 'ilike', so_name)], limit=1)
    
    if not so:
        f.write("ERROR: SO %s not found\n" % so_name)
    else:
        f.write("FOUND SO: %s (ID: %s)\n" % (so.name, so.id))
        picks = env['stock.picking'].search([
            ('group_id', '=', so.procurement_group_id.id),
            ('picking_type_id.code', '=', 'internal'),
            ('state', 'not in', ('cancel', 'done'))
        ])
        
        f.write("Scanning %d pickings for SO %s...\n" % (len(picks), so.name))
        
        for pick in picks:
            f.write("\n--- Checking %s ---\n" % pick.name)
            moves = pick.move_ids.filtered(lambda x: x.state not in ('cancel', 'done'))
            products = moves.mapped('product_id')
            
            any_merged = False
            for product in products:
                p_moves = moves.filtered(lambda x: x.product_id == product)
                if len(p_moves) > 1:
                    f.write("  Merging Duplicate Product: %s (%d lines)\n" % (product.display_name, len(p_moves)))
                    
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
            
            if not any_merged:
                f.write("  ✅ No duplicate product lines found.\n")
            else:
                pick.action_assign()
                f.write("  ✅ Merge done and reserved.\n")

    env.cr.commit()
    f.write("\n=== COMPLETED ===")
