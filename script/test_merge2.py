import sys

def check_transfers():
    with open('merge_out.txt', 'w', encoding='utf-8') as f:
        pickings = env['stock.picking'].search([('state', 'in', ['waiting', 'confirmed']), ('picking_type_id.name', 'ilike', 'Transfer Plastic')], limit=20)
        f.write(f"Found {len(pickings)} Transfer Plastic pickings\n")

        for p in pickings:
            f.write(f"\nPicking: {p.name} (ID: {p.id}), Origin: {p.origin}, Group: {p.group_id.name if p.group_id else 'None'}, State: {p.state}\n")
            for m in p.move_ids:
                f.write(f"  Move: {m.product_id.name}, group_id: {m.group_id.name if m.group_id else 'None'}\n")
                if hasattr(m, '_get_mto_transfer_merge_group'):
                    mg = m._get_mto_transfer_merge_group()
                    f.write(f"    -> merge_group: {mg.name if mg else 'None'}\n")
                
                # Check what m_type returns
                m_type = m._get_mo_manufacturing_type()
                f.write(f"    -> m_type: {m_type}\n")

check_transfers()
