import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

pick_names = ['GMP/TRPL/02160', 'GMP/TRPL/02161', 'GMP/TRPL/02162']
picks = env['stock.picking'].search([('name', 'in', pick_names)])

print("=== Analysis of Pickings in Screenshot ===")
for p in picks:
    print("\n[%s]" % p.name)
    print("  Source: %s" % p.location_id.complete_name)
    print("  Dest:   %s" % p.location_dest_id.complete_name)
    print("  Origin: %s" % p.origin)
    print("  Group:  %s" % p.group_id.name if p.group_id else 'N/A')
    
    for m in p.move_ids:
        # ดูว่าสินค้าตัวนี้ใช้ Rule ไหนในการสร้าง move
        rule = m.rule_id
        print("    - Product: %s | Qty: %.2f" % (m.product_id.display_name, m.product_uom_qty))
        print("      Rule: %s (id=%s)" % (rule.name if rule else 'N/A', rule.id if rule else 'N/A'))
        print("      Procure Method: %s" % rule.procure_method if rule else 'N/A')
