# coding: utf-8
po = env['purchase.order'].search([('name', '=', 'P01050')])
print("PO:", po.name, "State:", po.state)
for line in po.order_line:
    print("Line ID:", line.id, "Price:", line.price_unit, "Qty:", line.product_qty, "Received:", line.qty_received, "Discount:", line.fixed_discount)
