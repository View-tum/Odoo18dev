# coding: utf-8
po = env['purchase.order'].search([('name', '=', 'P01050')])
for line in po.order_line:
    print("Line", line.id, "Product:", line.product_id.id, "Tmpl:", line.product_id.product_tmpl_id.id, "Is Apportion:", line.product_id.product_tmpl_id.is_apportion_discount, "Price:", line.price_unit)
