import sys

def run_diagnostic():
    params = env['ir.config_parameter'].sudo()
    enabled = params.get_param('mrp_auto_merge.enabled', 'True')
    date_range = params.get_param('mrp_auto_merge.date_range', '7')
    
    with open('C:\\365_project\\TheCool18e\\Dev\\diag_result.txt', 'w', encoding='utf-8') as f:
        f.write(f"--- Settings ---\n")
        f.write(f"mrp_auto_merge.enabled = {enabled}\n")
        f.write(f"mrp_auto_merge.date_range = {date_range}\n")
        
        f.write("\n--- Recent MOs ---\n")
        mos = env['mrp.production'].search([], order='id desc', limit=20)
        for mo in mos:
            prod_name = mo.product_id.display_name if mo.product_id else "None"
            so_name = mo.source_sale_order_id.name if mo.source_sale_order_id else "None"
            f.write(f"MO: {mo.name} (ID: {mo.id}) | Product: {prod_name} | BoM: {mo.bom_id.id} | State: {mo.state}\n")
            f.write(f"    Date: {mo.date_start} | Origin: {mo.origin} | MTO: {mo.is_mto} | Source SO: {so_name}\n")
            f.write(f"    Picking Type: {mo.picking_type_id.id} | Planned: {mo.is_planned} | Backorder: {mo.backorder_sequence}\n")

run_diagnostic()
