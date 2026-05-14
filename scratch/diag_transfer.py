import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

so = env['sale.order'].search([('name', '=', 'SOD-263228')])
all_mos = env['mrp.production'].search([('source_sale_order_id', '=', so.id), ('state', '!=', 'cancel')])
test_mo = all_mos[0]
print("Test MO: %s" % test_mo.name)

raw_moves = test_mo.move_raw_ids.filtered(lambda x: x.state != 'cancel' and x.move_orig_ids)
if raw_moves:
    upstream_moves = raw_moves[0].move_orig_ids.filtered(lambda x: x.picking_id and x.state != 'cancel')
    if upstream_moves:
        sample_pick = upstream_moves[0].picking_id
        print("Sample picking: %s" % sample_pick.name)
        pick_moves = sample_pick.move_ids
        print("Moves in this picking: %d" % len(pick_moves))

        print("\n--- Testing merge group resolution for each move ---")
        for m in pick_moves:
            mg = m._get_mto_transfer_merge_group()
            print("  move %d: group=%s merge_group=%s (id=%s) pt=%s" % (
                m.id, m.group_id.name, mg.name if mg else 'EMPTY', mg.id if mg else 'N/A', m.picking_type_id.code))

        print("\n--- Testing mapped() behavior ---")
        merge_groups = pick_moves.mapped(lambda move: move._get_mto_transfer_merge_group())
        print("merge_groups type: %s" % type(merge_groups))
        print("merge_groups: %s" % merge_groups)
        print("len(merge_groups): %d" % len(merge_groups))
        filtered = merge_groups.filtered(lambda g: g)
        print("filtered: %s" % filtered)
        print("len(filtered): %d" % len(filtered))

        print("\n--- Simulating _get_new_picking_values ---")
        vals = pick_moves._get_new_picking_values()
        print("vals group_id: %s" % vals.get('group_id'))
        so_pg = so.procurement_group_id
        print("SO group_id: %s" % so_pg.id)
        print("MATCH: %s" % (vals.get('group_id') == so_pg.id))

env.cr.rollback()
