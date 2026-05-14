import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Look for pickings generated recently
domain = [('picking_type_id.code', '=', 'internal'), ('state', 'not in', ['done', 'cancel'])]
picks = env['stock.picking'].search(domain, order='id desc', limit=20)

print(f"Found {len(picks)} recent internal transfers:")
for p in picks:
    print(f"Picking: {p.name} (id={p.id})")
    print(f"  group_id: {p.group_id.name if p.group_id else 'None'} (id={p.group_id.id if p.group_id else 'None'})")
    print(f"  location: {p.location_id.name} -> {p.location_dest_id.name}")
    print(f"  origin: {p.origin}")
    print(f"  mfg_type: {p.manufacturing_type}")
    
    for m in p.move_ids[:3]:
        print(f"    Move: {m.product_id.name} qty={m.product_qty}")
        print(f"      move.group_id: {m.group_id.name if m.group_id else 'None'} (id={m.group_id.id if m.group_id else 'None'})")
        print(f"      merge_group: {m._get_mto_transfer_merge_group().name if hasattr(m, '_get_mto_transfer_merge_group') and m._get_mto_transfer_merge_group() else 'None'}")
        
    print("-" * 50)
