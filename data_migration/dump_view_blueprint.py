import sys, json
sys.path.insert(0, r"C:\365_project\TheCool18e\Dev\server")
import odoo
from odoo import api, SUPERUSER_ID

odoo.tools.config.parse_config(['-c', r'C:\365_project\TheCool18e\Dev\server\odoo.conf'])

registry = odoo.registry('view')
blueprint = {}

with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})

    pts = env['stock.picking.type'].search([
        '|', '|',
        ('name', 'ilike', 'Pharma'),
        ('name', 'ilike', 'Plastic'),
        ('name', 'ilike', 'Packaging')
    ])
    blueprint['picking_types'] = []
    for pt in pts:
        blueprint['picking_types'].append({
            'name': pt.name,
            'code': pt.code,
            'sequence_code': pt.sequence_code,
            'warehouse_name': pt.warehouse_id.name or '',
            'loc_src_complete': pt.default_location_src_id.complete_name or '',
            'loc_dest_complete': pt.default_location_dest_id.complete_name or '',
            'use_create_lots': pt.use_create_lots,
            'use_existing_lots': pt.use_existing_lots,
        })

    routes = env['stock.route'].search([
        '|', '|',
        ('name', 'ilike', 'Pharma'),
        ('name', 'ilike', 'Plastic'),
        ('name', 'ilike', 'Packaging')
    ])
    blueprint['routes'] = []
    for r in routes:
        route_data = {
            'name': r.name,
            'product_selectable': r.product_selectable,
            'product_categ_selectable': r.product_categ_selectable,
            'warehouse_selectable': r.warehouse_selectable,
            'rules': [],
        }
        for rule in r.rule_ids:
            route_data['rules'].append({
                'name': rule.name,
                'action': rule.action,
                'procure_method': rule.procure_method,
                'picking_type_name': rule.picking_type_id.name,
                'loc_src_complete': rule.location_src_id.complete_name or '',
                'loc_dest_complete': rule.location_dest_id.complete_name or '',
                'group_propagation': rule.group_propagation_option,
                'auto': rule.auto,
            })
        blueprint['routes'].append(route_data)

    products = env['product.template'].search([
        ('manufacturing_type', '!=', False),
        ('manufacturing_type', '!=', ''),
        ('active', '=', True),
    ])
    blueprint['products'] = []
    for p in products:
        route_names = p.route_ids.mapped('name')
        blueprint['products'].append({
            'default_code': p.default_code or '',
            'name_en': p.with_context(lang='en_US').name or '',
            'manufacturing_type': p.manufacturing_type,
            'route_names': sorted(route_names),
        })

    workcenters = env['mrp.workcenter'].search([
        ('manufacturing_type', '!=', False),
        ('manufacturing_type', '!=', ''),
    ])
    blueprint['workcenters'] = []
    for wc in workcenters:
        blueprint['workcenters'].append({
            'name': wc.name,
            'code': wc.code or '',
            'manufacturing_type': wc.manufacturing_type,
        })

    all_routes = env['stock.route'].search([])
    blueprint['all_route_names'] = sorted(all_routes.mapped('name'))

    orderpoints = env['stock.warehouse.orderpoint'].search([('active', '=', True)])
    blueprint['orderpoints'] = []
    for op in orderpoints:
        blueprint['orderpoints'].append({
            'product_code': op.product_id.default_code or '',
            'product_name': op.product_id.with_context(lang='en_US').name or '',
            'product_tmpl_code': op.product_id.product_tmpl_id.default_code or '',
            'location_complete': op.location_id.complete_name or '',
            'product_min_qty': op.product_min_qty,
            'product_max_qty': op.product_max_qty,
            'qty_multiple': op.qty_multiple,
            'trigger': op.trigger,
            'route_name': op.route_id.name if op.route_id else '',
        })

out_path = r"C:\365_project\TheCool18e\Dev\data_migration\view_full_blueprint.json"
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(blueprint, f, indent=2, ensure_ascii=False)

print(f"Blueprint saved: {out_path}")
print(f"  Picking Types: {len(blueprint['picking_types'])}")
print(f"  Routes: {len(blueprint['routes'])}")
total_rules = sum(len(r['rules']) for r in blueprint['routes'])
print(f"  Rules: {total_rules}")
print(f"  Products with mfg_type: {len(blueprint['products'])}")
print(f"  Workcenters with mfg_type: {len(blueprint['workcenters'])}")
print(f"  Orderpoints (Replenishment): {len(blueprint['orderpoints'])}")

