# coding: utf-8
po = env['purchase.order'].search([('name', '=', 'P01050')])
bns = env['vendor.billing.note'].search([('purchase_id', '=', po.id)])
for bn in bns:
    print("Billing Note:", bn.name, "State:", bn.state)
    for line in bn.line_ids:
        print("  Line:", line.product_id.name, "Qty:", line.quantity, "Price:", line.price_unit)
