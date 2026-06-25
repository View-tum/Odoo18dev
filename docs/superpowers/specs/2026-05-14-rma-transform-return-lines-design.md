ริ่ม# RMA Transform Return Lines Design

Status: design approved in chat, pending implementation approval

Date: 2026-05-14

Module: `custom/goldmints_addon-main/transform_product_advanced`

## Goal

ปรับ `RMA Transform Returns` จากเอกสารที่รองรับสินค้าเดียว ให้รองรับการคืนหลายรายการในใบเดียว โดยผู้ใช้สามารถเลือกสินค้าที่ลูกค้าคืนได้หลายบรรทัด เช่น ยาดมขายเป็นแผงแต่คืนเป็นชิ้น และพิมเสนน้ำขายเป็นแพ็คแต่คืนเป็นชิ้น ในเอกสารเดียวกัน

ระบบต้องยังตรวจสอบย้อนกลับได้ครบจาก:

- Original Delivery
- Original Lot
- Original Delivery Line
- Sale Order
- Customer Invoice
- Invoice Line
- Transform Rule
- Return Picking
- Credit Note
- Stock Valuation Layer

## Standard vs Pain Point

### Standard Odoo

Odoo standard RMA/Return ทำงานโดยอ้างอิงสินค้าที่ขายออกไปตาม Delivery เดิม สินค้าที่รับคืนโดยปกติควรเป็น product เดียวกับที่ขายออก เพราะ stock move, return picking, invoice line และ credit note ถูกผูกกับ product เดิม

### Pain Point

ธุรกิจ Gold Mints ขายเป็นหน่วยใหญ่ เช่น ลัง แผง แพ็ค แต่ลูกค้าคืนเป็นชิ้น ทำให้ product ที่รับคืนไม่ตรงกับ product ที่ขายออก ถ้าใช้ return standard ตรง ๆ จะเกิดปัญหา:

- คืนเป็นทศนิยมไม่ได้ เพราะ product/UoM บางตัวบังคับจำนวนเต็ม
- CN ผูกกับ product ที่ขายเดิม แต่ stock รับคืนเป็น product ชิ้น
- Costing ผิดได้ถ้าไม่กระจายต้นทุนจากสินค้าขายเดิมมายังสินค้าชิ้น
- เอกสารหนึ่งใบคืนหลายชนิดไม่ได้ เพราะโครงสร้างเดิมเป็น header-level product เดียว

## Design Decision

ใช้โครงสร้างแบบ Header + Product Lines เหมือนเอกสาร Odoo มาตรฐาน

### Header: `rma.transform.return`

Header เก็บข้อมูลระดับเอกสาร:

- Number
- Partner
- Company
- Date
- State
- Return To
- Customer Location
- Auto Validate Return
- Auto Create Credit Note
- Auto Post Credit Note
- RMA Reason default
- Linked RMA Claim
- Linked Return Pickings
- Linked Credit Notes
- Total Return Quantity
- Total Refund Amount
- Total Return Stock Value

Header ไม่ควรเก็บ product หลักเป็น source of truth อีกต่อไป แต่ field เดิมควรเก็บไว้ชั่วคราวเพื่อ backward compatibility และแสดงผลเอกสารเก่าหรือเอกสารที่ยังไม่มี line

### Line: `rma.transform.return.line`

Line เป็น source of truth ของแต่ละสินค้าที่คืน:

- Transform Return
- Original Delivery
- Original Lot
- Original Delivery Line
- Partner
- Sale Order
- Sale Line
- Invoice
- Invoice Line
- Transform Rule
- Sold Product
- Returned Product
- Return Quantity
- Equivalent Sold Quantity
- Already Returned Quantity
- Maximum Return Quantity
- Pieces per Sold Unit
- Returned Lot
- Return To
- Customer Location
- Refund Unit Price Excluding VAT
- Refund Amount Excluding VAT
- Return Stock Unit Cost
- Return Stock Value
- RMA Reason

แต่ละ line ต้อง auto-fill จาก Original Delivery + Lot หรือจาก wizard ที่เลือก source move line

## UI Flow

### Create New

เมื่อกด New:

- สร้างเอกสารเปล่า
- ไม่ auto-fill จากเอกสารล่าสุด
- ผู้ใช้เลือก Partner หรือกด Add Return Lines

### Add Return Lines Wizard

เพิ่มปุ่ม `Add Return Lines`

Wizard แสดงรายการสินค้าที่เคยขายให้ลูกค้ารายนั้นและมีสิทธิ์คืนได้ โดย filter:

- Same company
- Same customer/commercial partner
- Done outgoing delivery
- มี lot หรือ move line ที่ตรวจสอบย้อนกลับได้
- มี posted customer invoice line ที่สัมพันธ์กับ sale/delivery line
- มี transform rule ที่ map sold product ไป returned product
- ยังไม่คืนเกินสิทธิ์

ผู้ใช้เลือกได้หลายบรรทัดในครั้งเดียว แล้วกด Add Lines

### Return Lines Tab

แสดง one2many list แบบ product line:

- Select
- Original Delivery
- Original Lot
- Sold Product
- Returned Product
- Return Quantity
- Equivalent Sold Quantity
- Maximum Return Quantity
- Invoice
- Refund Unit Price
- Refund Amount
- Return Stock Unit Cost
- Return Stock Value

สามารถเปิด line form เพื่อดูรายละเอียดเต็มได้

## Confirm Flow

เมื่อกด Confirm:

1. Validate ทุก line
2. สร้าง RMA Claim 1 ใบ
3. สร้าง RMA Claim Lines ตามจำนวน return lines
4. สร้าง Return Picking ตาม group key
5. สร้าง Credit Note ตาม original invoice
6. สร้าง/ผูก Returned Lot ให้ตรงกับ returned product
7. Validate return picking ถ้าเปิด Auto Validate Return
8. Create/Post credit note ตาม config
9. Update state เป็น Done

## Grouping Rules

### Return Picking

ควร group ตาม:

- Company
- Partner/customer location
- Return destination location
- Picking type

ถ้า line หลายรายการเข้า location เดียวกัน ให้รวมใน return picking เดียว แต่แยก stock move ตาม returned product และ lot

### Credit Note

ควร group ตาม original invoice เท่านั้น

เหตุผล: Credit Note ควรมี `reversed_entry_id` ชัดเจนและ audit กลับไป invoice เดิมได้ ถ้า line มาจากคนละ invoice ต้องสร้าง CN แยกใบ

## Costing and Valuation

### Stock Return Cost

ต้นทุนสินค้าชิ้นที่รับคืนต้องคำนวณจากต้นทุนขายเดิม ไม่ใช่ราคาขาย และไม่รวม VAT

หลักการ:

- หา original outgoing stock valuation layer ของ sold product
- คำนวณ cost per sold unit จาก valuation ของ stock move เดิม
- กระจายต้นทุนตาม `pieces_per_sold_unit`
- ได้ return stock unit cost ของ returned product

ตัวอย่าง:

- ขาย 1 ลัง
- ต้นทุนลังไม่รวม VAT = 10,000
- 1 ลังแตกเป็น 5 ชิ้น
- ต้นทุนรับคืนต่อชิ้น = 2,000

### Credit Note Price

ราคา CN ต้องใช้ราคาขายไม่รวม VAT จาก invoice line เดิม แล้วกระจายตาม factor:

- invoice line price subtotal / invoice quantity = sale price per sold unit excl. VAT
- sale price per sold unit / pieces per sold unit = refund unit price excl. VAT
- refund unit price * return quantity = CN line subtotal

VAT ให้ Odoo คำนวณจาก tax เดิมของ invoice line

## Validation Rules

ต้อง block ก่อน confirm เมื่อ:

- ไม่มี return line
- line ไม่มี original delivery line
- line ไม่มี invoice line
- line ไม่มี transform rule
- returned product ไม่มี lot แต่ product tracking บังคับ lot/serial
- return quantity <= 0
- equivalent sold quantity เกิน maximum return quantity
- original stock valuation layer หาไม่ได้สำหรับสินค้าที่ต้อง valuation
- invoice/company/currency ไม่สัมพันธ์กัน

## Cancel and Reset to Draft

Cancel แบบ Option B:

- ถ้า return picking ยังไม่ done ให้ cancel และลบ draft move ที่เกี่ยวข้องได้
- ถ้า return picking done แล้วต้องสร้าง reverse picking เพื่อล้าง stock ไม่ควรลบ stock move
- ถ้า credit note ยัง draft ให้ cancel/delete ได้ตามสิทธิ์
- ถ้า credit note posted แล้วให้สร้าง reversal หรือ cancel ตาม accounting lock rules
- RMA Claim ต้องถูก cancel ตามไปด้วย
- เอกสารต้องเก็บ trace ว่าถูก cancel เพราะอะไร

Reset to Draft:

- อนุญาตเฉพาะเอกสารที่ยังไม่มี stock/accounting posted effect หรือถูก reverse ครบแล้ว

## Backward Compatibility

เอกสารเดิมที่เป็น single-line header ต้องยังเปิดดูได้

แนวทาง migration:

- เพิ่ม line model ใหม่
- ตอน module upgrade ให้ migrate record ที่ไม่มี line แต่มี `source_move_id` เป็น 1 line
- เอกสาร done/cancel เดิมให้ line เป็น trace/read-only
- เอกสาร draft เดิมให้แก้ไขผ่าน line ใหม่หลัง migration

## Files To Change

- `models/rma_transform_return.py`
- `models/__init__.py`
- `views/rma_transform_return_views.xml`
- `security/ir.model.access.csv`

Optional if wizard is separated:

- `models/rma_transform_return_wizard.py`
- `views/rma_transform_return_wizard_views.xml`

## QA Scenarios

1. New document opens blank and does not auto-fill latest delivery
2. Add one return line from one delivery and confirm
3. Add multiple lines from same delivery and same invoice
4. Add multiple lines from different deliveries but same customer
5. Add lines from different invoices and verify separate credit notes
6. Return quantity exceeds maximum and must block
7. Returned product requires lot and lot is auto-created for returned product
8. Valuation cost equals original cost excluding VAT divided by factor
9. CN amount equals original invoice price excluding VAT divided by factor
10. Auto validate return creates done picking correctly
11. Auto create CN creates correct credit note lines
12. Cancel draft document removes generated draft documents
13. Cancel done document uses reversal flow and does not delete posted stock/accounting data
14. Existing single-line document still opens and confirms after migration

## Implementation Recommendation

Proceed with Header + Lines + Add Return Lines Wizard.

This design keeps Odoo accounting and stock traceability intact, supports multi-product returns in one document, and keeps the user flow close to standard Odoo product line UX.

