import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Find by looking for the one that is destination of 'Transfer RM' rules
rules = env['stock.rule'].search([('name', 'ilike', 'Transfer RM (copy)')])
if not rules:
    print("ERROR: No rules found")
    sys.exit()

target_loc = rules[0].location_dest_id
target_loc_id = target_loc.id
print("Target Location identified: %s (id=%s)" % (target_loc.complete_name, target_loc.id))

# Find Routes
routes = env['stock.route'].search([('name', 'ilike', 'Auto Transfer RM')])
print("Found Routes: %s" % routes.mapped('name'))

rules_to_fix = env['stock.rule'].search([('route_id', 'in', routes.ids), ('location_dest_id', '=', target_loc_id)])

for r in rules_to_fix:
    print("\nRule: %s | %s -> %s" % (r.name, r.location_src_id.complete_name, r.location_dest_id.complete_name))
    print("  Current Procure Method: %s" % r.procure_method)
    
    if r.location_src_id.name == 'RM' and r.procure_method != 'make_to_order':
        print("  -> Updating to 'make_to_order' to force chain...")
        r.write({'procure_method': 'make_to_order'})

env.cr.commit()
print("\nRoute rules optimization DONE")
