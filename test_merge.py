import sys

def check_transfers():
    print("Checking internal transfers...")
    pickings = env['stock.picking'].search([('state', '=', 'confirmed'), ('picking_type_id.code', '=', 'internal')], limit=10)
    print(f"Found {len(pickings)} internal pickings")

    for p in pickings:
        print(f"\nPicking: {p.name} (ID: {p.id}), Origin: {p.origin}, Group: {p.group_id.name if p.group_id else 'None'}")
        for m in p.move_ids:
            print(f"  Move: {m.product_id.name}, group_id: {m.group_id.name if m.group_id else 'None'}")
            if hasattr(m, '_get_mto_transfer_merge_group'):
                mg = m._get_mto_transfer_merge_group()
                print(f"    -> merge_group: {mg.name if mg else 'None'}")

check_transfers()
