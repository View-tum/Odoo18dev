import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

so = env['sale.order'].search([('name', '=', 'SOD-263229')], limit=1)

print("=" * 70)
print("DUPLICATE PRODUCT ANALYSIS - GMP/TRPL/02157 & 02158")
print("=" * 70)

for pname in ['GMP/TRPL/02157', 'GMP/TRPL/02158']:
    p = env['stock.picking'].search([('name', '=', pname)], limit=1)
    print("\n--- %s: %s -> %s ---" % (p.name, p.location_id.complete_name, p.location_dest_id.complete_name))
    
    prod_map = {}
    for m in p.move_ids.filtered(lambda x: x.state != 'cancel').sorted(lambda x: x.product_id.display_name):
        pid = m.product_id.id
        if pid not in prod_map:
            prod_map[pid] = []
        prod_map[pid].append(m)
    
    for pid, mvs in prod_map.items():
        dup_mark = " *** DUPLICATE" if len(mvs) > 1 else ""
        for mv in mvs:
            dest_mos = mv.move_dest_ids.mapped('raw_material_production_id.name')
            print("  %s | qty=%.0f | origin=%s | dest_mo=%s%s" % (
                mv.product_id.display_name[:35], mv.product_uom_qty,
                mv.origin or 'N/A', ','.join(dest_mos) or 'N/A', dup_mark))

print("\n" + "=" * 70)
print("ROUTE STRUCTURE ANALYSIS")
print("=" * 70)

print("\nPlastic route rules:")
rules = env['stock.rule'].search([('route_id.name', 'ilike', 'Auto Transfer RM (Plastic)')])
for r in rules.sorted(lambda x: x.sequence):
    print("  seq=%d | %s | %s -> %s | action=%s | procure=%s" % (
        r.sequence, r.name, r.location_src_id.complete_name, r.location_dest_id.complete_name,
        r.action, r.procure_method))

print("\nPackaging route rules:")
rules = env['stock.rule'].search([('route_id.name', 'ilike', 'Auto Transfer RM (Packaging)')])
for r in rules.sorted(lambda x: x.sequence):
    print("  seq=%d | %s | %s -> %s | action=%s | procure=%s" % (
        r.sequence, r.name, r.location_src_id.complete_name, r.location_dest_id.complete_name,
        r.action, r.procure_method))

print("\nPharma route rules (RM):")
rules = env['stock.rule'].search([('route_id.name', 'ilike', 'Auto Transfer RM (Pharma)')])
for r in rules.sorted(lambda x: x.sequence):
    print("  seq=%d | %s | %s -> %s | action=%s | procure=%s" % (
        r.sequence, r.name, r.location_src_id.complete_name, r.location_dest_id.complete_name,
        r.action, r.procure_method))

print("\nPharma route rules (Semi):")
rules = env['stock.rule'].search([('route_id.name', 'ilike', 'Auto Transfer Semi (Pharma)')])
for r in rules.sorted(lambda x: x.sequence):
    print("  seq=%d | %s | %s -> %s | action=%s | procure=%s" % (
        r.sequence, r.name, r.location_src_id.complete_name, r.location_dest_id.complete_name,
        r.action, r.procure_method))

print("\n" + "=" * 70)
print("WHY 2-STEP ROUTE? (Stock->RM->Klang vs Stock->Klang)")
print("=" * 70)

p1 = env['stock.picking'].search([('name', '=', 'GMP/TRPL/02157')], limit=1)
p2 = env['stock.picking'].search([('name', '=', 'GMP/TRPL/02158')], limit=1)

print("\nGMP/TRPL/02157 (Stock -> Klang) - moves:")
for m in p1.move_ids[:3]:
    print("  %s | rule=%s | procure=%s" % (
        m.product_id.display_name[:30],
        m.rule_id.name if m.rule_id else 'N/A',
        m.procure_method))
    for orig in m.move_orig_ids:
        print("    orig: %s -> %s (pick=%s)" % (
            orig.location_id.complete_name, orig.location_dest_id.complete_name,
            orig.picking_id.name or 'NONE'))

print("\nGMP/TRPL/02158 (RM -> Klang) - moves:")
for m in p2.move_ids[:3]:
    print("  %s | rule=%s | procure=%s" % (
        m.product_id.display_name[:30],
        m.rule_id.name if m.rule_id else 'N/A',
        m.procure_method))
    for orig in m.move_orig_ids:
        print("    orig: %s -> %s (pick=%s)" % (
            orig.location_id.complete_name, orig.location_dest_id.complete_name,
            orig.picking_id.name or 'NONE'))

print("\n" + "=" * 70)
print("MOVE MERGE CHECK - Same product, can they merge?")
print("=" * 70)

for pname in ['GMP/TRPL/02157', 'GMP/TRPL/02158']:
    p = env['stock.picking'].search([('name', '=', pname)], limit=1)
    prod_map = {}
    for m in p.move_ids.filtered(lambda x: x.state != 'cancel'):
        pid = m.product_id.id
        if pid not in prod_map:
            prod_map[pid] = []
        prod_map[pid].append(m)
    
    dups = {k: v for k, v in prod_map.items() if len(v) > 1}
    if dups:
        print("\n%s - %d duplicate products:" % (pname, len(dups)))
        for pid, mvs in list(dups.items())[:3]:
            print("  Product: %s" % mvs[0].product_id.display_name[:35])
            for mv in mvs:
                dest_mos = mv.move_dest_ids.mapped('raw_material_production_id.name')
                print("    id=%d qty=%.0f uom=%s dest_mo=%s origin=%s date=%s" % (
                    mv.id, mv.product_uom_qty, mv.product_uom.name,
                    ','.join(dest_mos), mv.origin or 'N/A',
                    mv.date.strftime('%Y-%m-%d %H:%M')))

env.cr.rollback()
