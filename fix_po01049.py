# coding: utf-8
po = env['purchase.order'].search([('name', '=', 'P01049')])

# 1. Fix the product
for line in po.order_line:
    if line.price_unit < 0:
        product = line.product_id
        tmpl = product.product_tmpl_id
        tmpl.write({"is_apportion_discount": True, "type": "service", "purchase_method": "purchase"})

# 2. Run Apportion
po.action_apportion_discount()

# 3. Fix qty_received
for line in po.order_line:
    if line.product_id.product_tmpl_id.is_apportion_discount:
        line.qty_received = line.product_qty

env.cr.commit()
print("Fix complete. Check PO01049 and create Billing Note again.")
