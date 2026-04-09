import sys, json
sys.path.insert(0, r"C:\365_project\TheCool18e\Dev\server")
import odoo
from odoo import api, SUPERUSER_ID

TARGET_DB = sys.argv[1] if len(sys.argv) > 1 else 'production'
BLUEPRINT_PATH = r"C:\365_project\TheCool18e\Dev\data_migration\view_full_blueprint.json"
DRY_RUN = '--dry-run' in sys.argv

odoo.tools.config.parse_config(['-c', r'C:\365_project\TheCool18e\Dev\server\odoo.conf'])

with open(BLUEPRINT_PATH, 'r', encoding='utf-8') as f:
    bp = json.load(f)

print(f"{'[DRY RUN] ' if DRY_RUN else ''}Migration to: {TARGET_DB}")
print(f"Blueprint: {len(bp['picking_types'])} PTs, {len(bp['routes'])} Routes, {len(bp['products'])} Products, {len(bp['workcenters'])} Workcenters")

registry = odoo.registry(TARGET_DB)
with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})

    wh = env['stock.warehouse'].search([('company_id', '=', 1)], limit=1)
    if not wh:
        print("FATAL: No warehouse found!")
        sys.exit(1)
    print(f"\nWarehouse: {wh.name} (id={wh.id})")

    def find_location(complete_name):
        if not complete_name:
            return env['stock.location']
        loc = env['stock.location'].search([('complete_name', '=', complete_name)], limit=1)
        if not loc:
            parts = complete_name.split('/')
            loc = env['stock.location'].search([('name', '=', parts[-1].strip())], limit=1)
        return loc

    log = {'pt_created': 0, 'pt_skipped': 0, 'route_created': 0, 'route_skipped': 0,
           'rule_created': 0, 'prod_updated': 0, 'prod_skipped': 0, 'prod_notfound': 0,
           'wc_updated': 0, 'wc_skipped': 0, 'wc_notfound': 0, 'route_assigned': 0, 'errors': []}

    print("\n" + "=" * 60)
    print("STEP 1: Operation Types (Picking Types)")
    print("=" * 60)

    pt_map = {}
    for pt_def in bp['picking_types']:
        existing = env['stock.picking.type'].search([
            ('name', '=', pt_def['name']),
            ('company_id', '=', 1),
        ], limit=1)
        if existing:
            pt_map[pt_def['name']] = existing
            log['pt_skipped'] += 1
            print(f"  SKIP (exists id={existing.id}): {pt_def['name']}")
            continue

        loc_src = find_location(pt_def['loc_src_complete'])
        loc_dest = find_location(pt_def['loc_dest_complete'])

        if not loc_src:
            msg = f"Location not found: {pt_def['loc_src_complete']}"
            log['errors'].append(msg)
            print(f"  ERROR: {msg}")
            continue
        if not loc_dest:
            msg = f"Location not found: {pt_def['loc_dest_complete']}"
            log['errors'].append(msg)
            print(f"  ERROR: {msg}")
            continue

        if not DRY_RUN:
            new_pt = env['stock.picking.type'].create({
                'name': pt_def['name'],
                'code': pt_def['code'],
                'sequence_code': pt_def['sequence_code'],
                'warehouse_id': wh.id,
                'default_location_src_id': loc_src.id,
                'default_location_dest_id': loc_dest.id,
                'use_create_lots': pt_def['use_create_lots'],
                'use_existing_lots': pt_def['use_existing_lots'],
                'company_id': 1,
            })
            pt_map[pt_def['name']] = new_pt
            print(f"  CREATED (id={new_pt.id}): {pt_def['name']} [{pt_def['sequence_code']}]")
        else:
            print(f"  WOULD CREATE: {pt_def['name']} [{pt_def['sequence_code']}]")
        log['pt_created'] += 1

    all_pts = env['stock.picking.type'].search([('company_id', '=', 1)])
    for pt in all_pts:
        if pt.name not in pt_map:
            pt_map[pt.name] = pt

    print("\n" + "=" * 60)
    print("STEP 2: Routes & Rules")
    print("=" * 60)

    route_map = {}
    all_existing_routes = env['stock.route'].search([('company_id', '=', 1)])
    for r in all_existing_routes:
        route_map[r.name] = r

    for route_def in bp['routes']:
        if route_def['name'] in route_map:
            log['route_skipped'] += 1
            print(f"  SKIP Route (exists id={route_map[route_def['name']].id}): {route_def['name']}")
            continue

        rule_vals_list = []
        for rule_def in route_def['rules']:
            pt = pt_map.get(rule_def['picking_type_name'])
            if not pt:
                msg = f"Picking type '{rule_def['picking_type_name']}' not found for rule '{rule_def['name']}'"
                log['errors'].append(msg)
                print(f"    ERROR: {msg}")
                continue

            loc_src = find_location(rule_def['loc_src_complete'])
            loc_dest = find_location(rule_def['loc_dest_complete'])

            rule_vals_list.append((0, 0, {
                'name': rule_def['name'],
                'action': rule_def['action'],
                'procure_method': rule_def['procure_method'],
                'picking_type_id': pt.id,
                'location_src_id': loc_src.id if loc_src else False,
                'location_dest_id': loc_dest.id if loc_dest else False,
                'group_propagation_option': rule_def['group_propagation'],
                'auto': rule_def['auto'],
                'company_id': 1,
            }))

        if not DRY_RUN:
            new_route = env['stock.route'].create({
                'name': route_def['name'],
                'product_selectable': route_def['product_selectable'],
                'product_categ_selectable': route_def['product_categ_selectable'],
                'warehouse_selectable': route_def['warehouse_selectable'],
                'company_id': 1,
                'rule_ids': rule_vals_list,
            })
            route_map[route_def['name']] = new_route
            print(f"  CREATED Route (id={new_route.id}): {route_def['name']} ({len(rule_vals_list)} rules)")
        else:
            print(f"  WOULD CREATE Route: {route_def['name']} ({len(rule_vals_list)} rules)")
        log['route_created'] += 1
        log['rule_created'] += len(rule_vals_list)

    print("\n" + "=" * 60)
    print("STEP 3: Product manufacturing_type + Route Assignment")
    print("=" * 60)

    has_mfg_col = False
    cr.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'product_template' AND column_name = 'manufacturing_type'
    """)
    has_mfg_col = bool(cr.fetchone())
    if not has_mfg_col:
        print("  WARNING: Column 'manufacturing_type' not found. Adding via SQL...")
        if not DRY_RUN:
            cr.execute("ALTER TABLE product_template ADD COLUMN manufacturing_type VARCHAR")
        has_mfg_col = True

    for pdata in bp['products']:
        if not pdata['default_code']:
            continue

        cr.execute("""
            SELECT pt.id, pt.manufacturing_type, pp.id
            FROM product_template pt
            JOIN product_product pp ON pp.product_tmpl_id = pt.id
            WHERE pt.default_code = %s AND pt.active = true LIMIT 1
        """, (pdata['default_code'],))
        row = cr.fetchone()
        if not row:
            log['prod_notfound'] += 1
            continue

        prod_tmpl_id, current_mtype, prod_prod_id = row
        needs_update = False

        if current_mtype != pdata['manufacturing_type']:
            if not DRY_RUN:
                cr.execute("""
                    UPDATE product_template SET manufacturing_type = %s WHERE id = %s
                """, (pdata['manufacturing_type'], prod_tmpl_id))
            needs_update = True

        target_route_ids = set()
        for rn in pdata['route_names']:
            r = route_map.get(rn)
            if not r:
                r = env['stock.route'].search([('name', '=', rn)], limit=1)
            if r:
                target_route_ids.add(r.id)

        cr.execute("""
            SELECT route_id FROM stock_route_product
            WHERE product_id = %s
        """, (prod_prod_id,))
        current_route_ids = set(r[0] for r in cr.fetchall())

        if target_route_ids != current_route_ids:
            if not DRY_RUN:
                cr.execute("DELETE FROM stock_route_product WHERE product_id = %s", (prod_prod_id,))
                for rid in target_route_ids:
                    cr.execute("""
                        INSERT INTO stock_route_product (product_id, route_id)
                        VALUES (%s, %s) ON CONFLICT DO NOTHING
                    """, (prod_prod_id, rid))
            needs_update = True
            log['route_assigned'] += 1

        if needs_update:
            log['prod_updated'] += 1
        else:
            log['prod_skipped'] += 1

    print(f"  Updated: {log['prod_updated']}, Skipped: {log['prod_skipped']}, Not found: {log['prod_notfound']}")
    print(f"  Routes re-assigned: {log['route_assigned']}")

    print("\n" + "=" * 60)
    print("STEP 4: Workcenter manufacturing_type")
    print("=" * 60)

    cr.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'mrp_workcenter' AND column_name = 'manufacturing_type'
    """)
    has_wc_col = bool(cr.fetchone())
    if not has_wc_col:
        print("  WARNING: Column 'manufacturing_type' not found on mrp_workcenter. Adding via SQL...")
        if not DRY_RUN:
            cr.execute("ALTER TABLE mrp_workcenter ADD COLUMN manufacturing_type VARCHAR")

    for wc_data in bp['workcenters']:
        cr.execute("SELECT id, manufacturing_type FROM mrp_workcenter WHERE name = %s LIMIT 1", (wc_data['name'],))
        row = cr.fetchone()
        if not row and wc_data['code']:
            cr.execute("SELECT id, manufacturing_type FROM mrp_workcenter WHERE code = %s LIMIT 1", (wc_data['code'],))
            row = cr.fetchone()

        if not row:
            log['wc_notfound'] += 1
            continue

        wc_id, current_wc_mtype = row
        if current_wc_mtype == wc_data['manufacturing_type']:
            log['wc_skipped'] += 1
            continue

        if not DRY_RUN:
            cr.execute("UPDATE mrp_workcenter SET manufacturing_type = %s WHERE id = %s", (wc_data['manufacturing_type'], wc_id))
        log['wc_updated'] += 1

    print(f"  Updated: {log['wc_updated']}, Skipped: {log['wc_skipped']}, Not found: {log['wc_notfound']}")

    print("\n" + "=" * 60)
    print("STEP 5: Replenishment (Orderpoints)")
    print("=" * 60)

    log['op_created'] = 0
    log['op_skipped'] = 0
    log['op_updated'] = 0
    log['op_notfound'] = 0

    for op_data in bp.get('orderpoints', []):
        if not op_data['product_code']:
            continue

        cr.execute("""
            SELECT pp.id FROM product_product pp
            JOIN product_template pt ON pp.product_tmpl_id = pt.id
            WHERE pp.default_code = %s AND pp.active = true LIMIT 1
        """, (op_data['product_code'],))
        prod_row = cr.fetchone()
        if not prod_row:
            log['op_notfound'] += 1
            continue
        product_id = prod_row[0]

        loc = find_location(op_data['location_complete'])
        if not loc:
            log['op_notfound'] += 1
            continue
        loc_id = loc.id

        op_route_id = False
        if op_data['route_name']:
            op_route = route_map.get(op_data['route_name'])
            if not op_route:
                op_route = env['stock.route'].search([('name', '=', op_data['route_name'])], limit=1)
            if op_route:
                op_route_id = op_route.id

        cr.execute("""
            SELECT id, product_min_qty, product_max_qty, trigger, route_id
            FROM stock_warehouse_orderpoint
            WHERE product_id = %s AND location_id = %s AND active = true LIMIT 1
        """, (product_id, loc_id))
        existing_row = cr.fetchone()

        if existing_row:
            op_id, cur_min, cur_max, cur_trigger, cur_route_id = existing_row
            needs_update = (
                cur_min != op_data['product_min_qty']
                or cur_max != op_data['product_max_qty']
                or cur_trigger != op_data['trigger']
                or (op_route_id and cur_route_id != op_route_id)
            )
            if needs_update:
                if not DRY_RUN:
                    cr.execute("""
                        UPDATE stock_warehouse_orderpoint
                        SET product_min_qty = %s, product_max_qty = %s,
                            qty_multiple = %s, trigger = %s, route_id = %s
                        WHERE id = %s
                    """, (op_data['product_min_qty'], op_data['product_max_qty'],
                          op_data['qty_multiple'], op_data['trigger'],
                          op_route_id or None, op_id))
                log['op_updated'] += 1
            else:
                log['op_skipped'] += 1
        else:
            if not DRY_RUN:
                wh = env['stock.warehouse'].search([('company_id', '=', 1)], limit=1)
                cr.execute("""
                    INSERT INTO stock_warehouse_orderpoint
                    (product_id, location_id, product_min_qty, product_max_qty,
                     qty_multiple, trigger, route_id, warehouse_id, company_id, active,
                     name, create_uid, create_date, write_uid, write_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1, true,
                            %s, 1, NOW(), 1, NOW())
                """, (product_id, loc_id, op_data['product_min_qty'],
                      op_data['product_max_qty'], op_data['qty_multiple'],
                      op_data['trigger'], op_route_id or None, wh.id,
                      op_data['product_code']))
            log['op_created'] += 1

    print(f"  Created: {log['op_created']}, Updated: {log['op_updated']}, Skipped: {log['op_skipped']}, Not found: {log['op_notfound']}")

    if not DRY_RUN:
        cr.commit()
        print("\n*** ALL CHANGES COMMITTED ***")
    else:
        print("\n*** DRY RUN - NO CHANGES MADE ***")

    print("\n" + "=" * 60)
    print("MIGRATION SUMMARY")
    print("=" * 60)
    print(f"  Operation Types: {log['pt_created']} created, {log['pt_skipped']} reused")
    print(f"  Routes: {log['route_created']} created, {log['route_skipped']} reused")
    print(f"  Rules: {log['rule_created']} created")
    print(f"  Products: {log['prod_updated']} updated, {log['prod_skipped']} ok, {log['prod_notfound']} not found")
    print(f"  Routes assigned to products: {log['route_assigned']}")
    print(f"  Workcenters: {log['wc_updated']} updated, {log['wc_skipped']} ok, {log['wc_notfound']} not found")
    print(f"  Orderpoints: {log['op_created']} created, {log['op_updated']} updated, {log['op_skipped']} ok, {log['op_notfound']} not found")
    if log['errors']:
        print(f"\n  ERRORS ({len(log['errors'])}):")
        for e in log['errors']:
            print(f"    - {e}")


