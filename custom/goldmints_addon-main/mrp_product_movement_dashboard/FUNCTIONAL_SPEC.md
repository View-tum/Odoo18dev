# Functional Spec: MRP Product Movement Dashboard

## 1. Objective
สร้างรายงานหน้าเดียวสำหรับ Planner / Production / Inventory Manager เพื่อดูข้อมูลต่อสินค้าในมุมเดียวกัน ได้แก่:

1. ผลิต
2. รับเข้า
3. จ่ายออก
4. คงเหลือ
5. Min
6. Max
7. สถานะต่ำกว่า Min / สูงกว่า Max

รายงานต้องสามารถแบ่งตาม `Product Group` ได้ 6 กลุ่มหรือมากกว่าในอนาคต โดยไม่ผูกติดกับ `manufacturing_type` เดิมที่มีแค่ `plastic/pharma`

## 2. Business Problem
ข้อมูลที่ผู้ใช้ต้องการอยู่กระจายหลายหน้า:

1. Replenishment / Orderpoint -> Min/Max/Forecast
2. Forecasted Report -> Movement รับ/จ่าย
3. Manufacturing Orders -> ยอดผลิต
4. Custom บางตัว -> แยกเฉพาะ MPS หรือเฉพาะ MO summary

ผลคือ Planner ต้องเปิดหลายจอและไม่มีหน้าเดียวสำหรับตัดสินใจ

## 3. In Scope
รายงานนี้ครอบคลุม:

1. สินค้าประเภท storable product
2. บริษัทเดียวต่อหนึ่งรอบ generate
3. คลัง 1 หรือหลายคลังในรอบเดียว
4. ช่วงวันที่สำหรับ Movement
5. Current on hand ณ วันที่ generate
6. Min/Max จาก Reordering Rule
7. Product Group ใหม่สำหรับ reporting
8. Filter manufacturing type ถ้ามี custom field อยู่ในระบบ

## 4. Out of Scope (Phase 1)
ยังไม่รวม:

1. Forecast demand แบบ MPS matrix
2. Cost / variance จาก MO summary
3. Drilldown แบบ graph ขั้นสูง
4. KPI card แบบ executive dashboard
5. Real-time autorefresh

## 5. Key Users
1. Planner
2. Production Manager
3. Inventory Manager
4. Supply Chain Manager

## 6. Main Process
1. ผู้ใช้สร้างเอกสาร Dashboard Run
2. ระบุ Company, Date From, Date To และ Warehouse
3. กด `Generate Lines`
4. ระบบคำนวณและสร้าง line ต่อ `Product + Warehouse`
5. ผู้ใช้เปิดดูในหน้า Form, Tree หรือ Pivot

## 7. Product Group
เพิ่ม master ใหม่:

1. `Product Report Group`
2. ผูกไว้ที่ `product.template`

เหตุผล:

1. ไม่ไปเปลี่ยน meaning ของ product category
2. ไม่ชนกับ custom `manufacturing_type`
3. รองรับ 6 กลุ่มวันนี้และขยายได้ในอนาคต

## 8. Definitions
### 8.1 Produced Qty
จำนวนที่ผลิตเสร็จในช่วงวันที่เลือก

นิยาม Phase 1:

1. ใช้ `stock.move` ที่ `state = done`
2. source usage = `production`
3. destination อยู่ใน location ภายใต้ warehouse view location

### 8.2 Received Qty
จำนวนรับเข้าที่ไม่ใช่การผลิต

นิยาม Phase 1:

1. ใช้ `stock.move` ที่ `state = done`
2. destination อยู่ใน warehouse internal tree
3. source usage เป็นหนึ่งใน:
   - supplier
   - customer
   - inventory
   - transit

### 8.3 Issued Qty
จำนวนจ่ายออกจากคลังไปลูกค้า

นิยาม Phase 1:

1. ใช้ `stock.move` ที่ `state = done`
2. source อยู่ใน warehouse internal tree
3. destination usage = `customer`

### 8.4 On Hand Qty
คงเหลือปัจจุบัน ณ เวลาที่กด generate

นิยาม Phase 1:

1. ใช้ `stock.quant.quantity`
2. รวมเฉพาะ internal locations ภายใต้ warehouse

### 8.5 Min Qty / Max Qty
ค่าจาก `stock.warehouse.orderpoint`

## 9. Output Fields
ต่อหนึ่ง line:

1. Company
2. Warehouse
3. Product Group
4. Product Category
5. Product
6. Internal Reference
7. UoM
8. Manufacturing Type
9. Produced Qty
10. Received Qty
11. Issued Qty
12. Net Movement Qty
13. On Hand Qty
14. Min Qty
15. Max Qty
16. Below Min
17. Above Max
18. Shortage Qty
19. Excess Qty

## 10. Existing Custom Reuse
### 10.1 Reuse now
1. `mrp_mps_manufacturing_type`
   - ใช้ field `manufacturing_type` ถ้ามี
2. `mrp_production_summary`
   - ใช้เป็น reference และ extension phase ถัดไปเรื่อง cost/variance/drilldown
3. `mrp_mps_mo_tracking`
   - ใช้เป็น extension ได้ถ้าจะ filter from MPS ใน phase ถัดไป

### 10.2 Not reused directly in phase 1
1. `mrp_auto_merge`
2. `mrp_parallel_console`

สองตัวนี้ยังเกี่ยวกับ execution flow มากกว่า report layer
