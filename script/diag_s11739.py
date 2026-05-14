import sys

def run():
    so_name = 'S11739'
    so = env['sale.order'].search([('name', '=', so_name)], limit=1)

    with open('C:\\365_project\\TheCool18e\\Dev\\diag_s11739.txt', 'w', encoding='utf-8') as f:
        f.write(f"--- Sale Order {so_name} ---\n")
        if not so:
            f.write("Not found\n")
            return
        
        f.write(f"State: {so.state}\n")
        
        pickings = so.picking_ids
        f.write(f"\nTransfers ({len(pickings)}):\n")
        for pick in pickings:
            f.write(f"  - {pick.name} (State: {pick.state}) | Origin: {pick.origin}\n")
            for move in pick.move_ids:
                f.write(f"      [MOVE] {move.product_id.display_name} Qty: {move.product_uom_qty} | State: {move.state} | ID: {move.id}\n")
                f.write(f"             orig_ids: {move.move_orig_ids.mapped('id')} | dest_ids: {move.move_dest_ids.mapped('id')}\n")
            
        mto_mos = env['mrp.production'].search([('source_sale_order_id', '=', so.id)])
        f.write(f"\nMOs linked via source_sale_order_id ({len(mto_mos)}):\n")
        for mo in mto_mos:
            f.write(f"  - {mo.name} (ID: {mo.id}) | Product: {mo.product_id.display_name} | Qty: {mo.product_qty} | State: {mo.state}\n")
            f.write(f"    Origin: {mo.origin}\n")
            for raw in mo.move_raw_ids:
                f.write(f"      [RAW] {raw.product_id.display_name} Qty: {raw.product_uom_qty} | State: {raw.state} | ID: {raw.id}\n")
                f.write(f"            orig_ids: {raw.move_orig_ids.mapped('id')} | dest_ids: {raw.move_dest_ids.mapped('id')}\n")
            for fin in mo.move_finished_ids:
                f.write(f"      [FIN] {fin.product_id.display_name} Qty: {fin.product_uom_qty} | State: {fin.state} | ID: {fin.id}\n")
                f.write(f"            orig_ids: {fin.move_orig_ids.mapped('id')} | dest_ids: {fin.move_dest_ids.mapped('id')}\n")

        pos = env['purchase.order'].search([('origin', 'ilike', so_name)])
        f.write(f"\nPOs ({len(pos)}):\n")
        for po in pos:
            f.write(f"  - {po.name} (State: {po.state}) | Origin: {po.origin}\n")
            for line in po.order_line:
                f.write(f"      [LINE] {line.product_id.display_name} Qty: {line.product_qty}\n")

run()
