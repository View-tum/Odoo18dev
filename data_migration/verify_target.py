import sys, json
sys.path.insert(0, r"C:\365_project\TheCool18e\Dev\server")
import odoo
from odoo import api, SUPERUSER_ID

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

TARGET_DB = sys.argv[1] if len(sys.argv) > 1 else 'production'

BLUEPRINT_PATH = r"C:\365_project\TheCool18e\Dev\data_migration\view_full_blueprint.json"

odoo.tools.config.parse_config(['-c', r'C:\365_project\TheCool18e\Dev\server\odoo.conf'])

with open(BLUEPRINT_PATH, 'r', encoding='utf-8') as f:
    bp = json.load(f)

print(f"Verifying: {TARGET_DB}")
print(f"Against VIEW blueprint: {len(bp['picking_types'])} PTs, {len(bp['routes'])} Routes, {len(bp['products'])} Products\n")

registry = odoo.registry(TARGET_DB)
results = []

with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})

    print("=" * 60)
    print("CHECK 1: Operation Types")
    print("=" * 60)
    pt_ok = 0
    pt_miss = 0
    for pt_def in bp['picking_types']:
        existing = env['stock.picking.type'].search([
            ('name', '=', pt_def['name']),
            ('company_id', '=', 1),
        ], limit=1)
        if existing:
            loc_ok = True
            if pt_def['loc_src_complete'] and existing.default_location_src_id.complete_name != pt_def['loc_src_complete']:
                loc_ok = False
            if pt_def['loc_dest_complete'] and existing.default_location_dest_id.complete_name != pt_def['loc_dest_complete']:
                loc_ok = False
            status = "OK" if loc_ok else "LOCATION MISMATCH"
            print(f"  [{status}] {pt_def['name']} (id={existing.id}, seq={existing.sequence_code})")
            if loc_ok:
                pt_ok += 1
            else:
                pt_miss += 1
                print(f"       Expected src: {pt_def['loc_src_complete']}, Got: {existing.default_location_src_id.complete_name}")
                print(f"       Expected dest: {pt_def['loc_dest_complete']}, Got: {existing.default_location_dest_id.complete_name}")
        else:
            pt_miss += 1
            print(f"  [MISSING] {pt_def['name']}")
    results.append(('Operation Types', pt_ok, pt_miss, len(bp['picking_types'])))

    print("\n" + "=" * 60)
    print("CHECK 2: Routes & Rules")
    print("=" * 60)
    rt_ok = 0
    rt_miss = 0
    rl_ok = 0
    rl_miss = 0
    for route_def in bp['routes']:
        existing = env['stock.route'].search([
            ('name', '=', route_def['name']),
            ('company_id', '=', 1),
        ], limit=1)
        if existing:
            rt_ok += 1
            print(f"  [OK] {route_def['name']} (id={existing.id}, {len(existing.rule_ids)} rules)")
            existing_rule_names = set(existing.rule_ids.mapped('name'))
            for rule_def in route_def['rules']:
                if rule_def['name'] in existing_rule_names:
                    rl_ok += 1
                else:
                    rl_miss += 1
                    print(f"       [MISSING RULE] {rule_def['name']}")
        else:
            rt_miss += 1
            rl_miss += len(route_def['rules'])
            print(f"  [MISSING] {route_def['name']} ({len(route_def['rules'])} rules)")

    total_rules = sum(len(r['rules']) for r in bp['routes'])
    results.append(('Routes', rt_ok, rt_miss, len(bp['routes'])))
    results.append(('Rules', rl_ok, rl_miss, total_rules))

    print("\n" + "=" * 60)
    print("CHECK 3: Product manufacturing_type + Routes")
    print("=" * 60)
    p_ok = 0
    p_diff = 0
    p_miss = 0
    route_ok = 0
    route_diff = 0
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
            p_miss += 1
            continue

        pt_id, current_mtype, pp_id = row
        if current_mtype == pdata['manufacturing_type']:
            p_ok += 1
        else:
            p_diff += 1

        cr.execute("""
            SELECT sr.name
            FROM stock_route_product srp
            JOIN stock_route sr ON sr.id = srp.route_id
            WHERE srp.product_id = %s
        """, (pp_id,))
        rows = cr.fetchall()
        current_routes = set()
        for r in rows:
            val = r[0] if isinstance(r, (list, tuple)) else r.get('name')
            current_routes.add(val)
        target_routes = set(pdata['route_names'])
        
        if current_routes == target_routes:
            route_ok += 1
        else:
            route_diff += 1

    results.append(('Product mfg_type', p_ok, p_diff + p_miss, len(bp['products'])))
    results.append(('Product routes', route_ok, route_diff, len(bp['products']) - p_miss))
    print(f"  mfg_type: {p_ok} OK, {p_diff} differ, {p_miss} not found")
    print(f"  routes:   {route_ok} OK, {route_diff} differ")

    print("\n" + "=" * 60)
    print("CHECK 4: Workcenter manufacturing_type")
    print("=" * 60)
    wc_ok = 0
    wc_diff = 0
    wc_miss = 0

    has_wc_col = False
    cr.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'mrp_workcenter' AND column_name = 'manufacturing_type'
    """)
    has_wc_col = bool(cr.fetchone())

    for wc_data in bp['workcenters']:
        if not has_wc_col:
            wc_diff += 1
            continue

        cr.execute("SELECT manufacturing_type FROM mrp_workcenter WHERE name = %s LIMIT 1", (wc_data['name'],))
        row = cr.fetchone()
        if not row and wc_data['code']:
            cr.execute("SELECT manufacturing_type FROM mrp_workcenter WHERE code = %s LIMIT 1", (wc_data['code'],))
            row = cr.fetchone()

        if not row:
            wc_miss += 1
            continue

        if row[0] == wc_data['manufacturing_type']:
            wc_ok += 1
        else:
            wc_diff += 1

    results.append(('Workcenter mfg_type', wc_ok, wc_diff + wc_miss, len(bp['workcenters'])))
    print(f"  {wc_ok} OK, {wc_diff} differ, {wc_miss} not found")

    print("\n" + "=" * 60)
    print("CHECK 5: Replenishment (Orderpoints)")
    print("=" * 60)
    op_ok = 0
    op_diff = 0
    op_miss = 0

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
            op_miss += 1
            continue
        product_id = prod_row[0]

        loc = env['stock.location'].search([('complete_name', '=', op_data['location_complete'])], limit=1)
        if not loc:
            op_miss += 1
            continue
        loc_id = loc.id

        cr.execute("""
            SELECT product_min_qty, product_max_qty, trigger
            FROM stock_warehouse_orderpoint
            WHERE product_id = %s AND location_id = %s AND active = true LIMIT 1
        """, (product_id, loc_id))
        op_row = cr.fetchone()
        
        if not op_row:
            op_miss += 1
            continue

        cur_min, cur_max, cur_trigger = op_row
        match = (
            cur_min == op_data['product_min_qty']
            and cur_max == op_data['product_max_qty']
            and cur_trigger == op_data['trigger']
        )
        if match:
            op_ok += 1
        else:
            op_diff += 1

    total_ops = len([o for o in bp.get('orderpoints', []) if o['product_code']])
    results.append(('Orderpoints', op_ok, op_diff + op_miss, total_ops))
    print(f"  {op_ok} OK, {op_diff} differ, {op_miss} missing/not found (total: {total_ops})")

    print("\n" + "=" * 60)
    print("OVERALL VERIFICATION RESULTS")
    print("=" * 60)
    all_pass = True
    for label, ok, fail, total in results:
        status = "PASS" if fail == 0 else "FAIL"
        if fail > 0:
            all_pass = False
        print(f"  [{status}] {label}: {ok}/{total} OK ({fail} issues)")

    print(f"\n{'ALL CHECKS PASSED!' if all_pass else 'SOME CHECKS FAILED - see details above'}")

