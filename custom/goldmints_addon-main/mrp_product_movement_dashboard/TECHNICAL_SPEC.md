# Technical Spec: MRP Product Movement Dashboard

## 1. Module Name
`mrp_product_movement_dashboard`

## 2. Design Goals
1. Core-safe
2. ไม่ override core method ฝั่ง stock/mrp
3. เป็น reporting layer แยก
4. รองรับ uninstall
5. reuse custom เดิมได้ในจุดที่จำเป็น

## 3. Data Model
### 3.1 New Model: `product.report.group`
Fields:
1. `name`
2. `code`
3. `sequence`
4. `active`

### 3.2 Inherit: `product.template`
1. `report_group_id`

### 3.3 Inherit: `product.product`
1. `report_group_id`

### 3.4 New Model: `product.movement.dashboard.batch`
1. `name`
2. `company_id`
3. `date_from`
4. `date_to`
5. `warehouse_ids`
6. `state`
7. `line_ids`
8. `line_count`
9. `below_min_count`
10. `above_max_count`

### 3.5 New Model: `product.movement.dashboard.line`
1. `batch_id`
2. `company_id`
3. `warehouse_id`
4. `report_group_id`
5. `product_id`
6. `product_tmpl_id`
7. `categ_id`
8. `default_code`
9. `uom_id`
10. `manufacturing_type`
11. `produced_qty`
12. `received_qty`
13. `issued_qty`
14. `net_movement_qty`
15. `on_hand_qty`
16. `min_qty`
17. `max_qty`
18. `below_min`
19. `above_max`
20. `shortage_qty`
21. `excess_qty`

## 4. Query Sources
1. On hand -> `stock.quant`
2. Min/Max -> `stock.warehouse.orderpoint`
3. Produced -> `stock.move` done, source usage `production`, destination internal
4. Received -> `stock.move` done, destination internal, source usage `supplier/customer/inventory/transit`
5. Issued -> `stock.move` done, source internal, destination usage `customer`

## 5. Existing Custom Compatibility
1. `mrp_mps_manufacturing_type`
   - อ่าน `manufacturing_type` ถ้ามี field อยู่
2. `mrp_production_summary`
   - ใช้เป็น extension source สำหรับ phase ถัดไป
3. `mrp_mps_mo_tracking`
   - ใช้เพิ่ม filter from MPS ได้ใน phase ถัดไป

## 6. Why no core override
เหตุผล:
1. requirement เป็น reporting
2. ไม่ควรแตะ transaction flow เดิม
3. ลด risk upgrade และลดผลกระทบ production
