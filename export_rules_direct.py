import sys
import os

sys.path.append(r'C:\365_project\TheCool18e\Dev\server')
import odoo

odoo.tools.config.parse_config(['-c', r'C:\365_project\TheCool18e\Dev\server\odoo.conf', '-d', 'UAT'])
registry = odoo.registry('UAT')

import csv

export_dir = r"C:\365_project\TheCool18e\Dev\Exported_Config"
if not os.path.exists(export_dir):
    os.makedirs(export_dir)

with registry.cursor() as cr:
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})

    with open(os.path.join(export_dir, 'putaway_rules_export.csv'), 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['ID', 'Product', 'Category', 'When product arrives in', 'Store to', 'Company'])
        for rule in env['stock.putaway.rule'].search([]):
            writer.writerow([
                rule.id,
                rule.product_id.display_name if rule.product_id else '',
                rule.category_id.display_name if rule.category_id else '',
                rule.location_in_id.display_name if rule.location_in_id else '',
                rule.location_out_id.display_name if rule.location_out_id else '',
                rule.company_id.name if rule.company_id else ''
            ])

    with open(os.path.join(export_dir, 'product_routes_export.csv'), 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Product ID', 'Product', 'Routes'])
        for pt in env['product.template'].search([('route_ids', '!=', False)]):
            routes = ', '.join(pt.route_ids.mapped('name'))
            writer.writerow([pt.id, pt.display_name, routes])

    with open(os.path.join(export_dir, 'stock_rules_export.csv'), 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Route', 'Action', 'Operation Type', 'Source Location', 'Destination Location'])
        for rule in env['stock.rule'].search([]):
            writer.writerow([
                rule.route_id.name if rule.route_id else '',
                rule.action,
                rule.picking_type_id.name if rule.picking_type_id else '',
                rule.location_src_id.display_name if rule.location_src_id else '',
                rule.location_dest_id.display_name if rule.location_dest_id else ''
            ])

print("EXPORT_SUCCESSFUL")
