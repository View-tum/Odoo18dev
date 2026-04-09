# Purchase Training: Page, Table, and Field Reference

เอกสารนี้อธิบายแต่ละหน้าที่ใช้ใน training purchase แบบละเอียด โดยเน้น 3 มุมพร้อมกัน

1. หน้านี้ใช้ทำอะไรใน business flow
2. แต่ละ table หรือ section สำคัญตรงไหน
3. ส่วนไหนเป็น Odoo standard และส่วนไหนเป็น custom ของเรา

เอกสารนี้ใช้คู่กับ

- [purchase_training_uat_detailed_20260331.pptx](./purchase_training_uat_detailed_20260331.pptx)
- [purchase_training_uat_detailed_speaker_20260331.txt](./purchase_training_uat_detailed_speaker_20260331.txt)
- [05_trainer_click_guide.md](./05_trainer_click_guide.md)
- [06_expected_questions_qa.md](./06_expected_questions_qa.md)

## 1. ภาพรวมว่า training purchase ชุดนี้อิงอะไร

### Odoo Standard ที่ใช้
- `purchase` สำหรับ RFQ, PO, vendor, purchase order lines
- `stock` สำหรับ receipt, move lines, lot, scrap
- `account` สำหรับ vendor bill และ journal items
- `account_asset` สำหรับ asset accounting ถ้ามีการเปิดใช้งาน category และ automation
- `product` สำหรับ product category และสินค้าพื้นฐาน

### Custom / Ecosystem ของเรา ที่เข้ามาเกี่ยว
- `purchase_request`
  ใช้ PR เป็นจุดเริ่มต้นของ flow
- `purchase_request_department`
  เพิ่มมุม department ใน PR และ PR line
- `purchase_request_analytic_required`
  บังคับให้บางกรณีต้องระบุ analytic
- `purchase_request_vendor`
  เพิ่มข้อมูล vendor ใน PR flow
- `purchase_request_custom`
  กันการสร้าง RFQ ซ้ำเมื่อ PR line ถูกครอบคลุมแล้ว
- `oi_workflow_purchase_request`
  approval workflow ฝั่ง PR
- `oi_workflow_purchase_order`
  approval workflow ฝั่ง PO
- `budget_control_purchase_request`
  ผูก PR เข้ากับ budget commit
- `purchase_service_acceptance`
  เพิ่มเอกสาร `Service Acceptance` เป็น “receipt ของ service”
- `po_purchase_request_smart_button`
  ช่วยเชื่อม PR กับ PO ผ่าน smart button
- `vendor_billing_note`
  เสริมข้อมูลฝั่ง billing note บน PO ในบาง flow

หมายเหตุ:
- training ชุดนี้ใช้ transaction จริงใน `uat`
- บางหน้าเป็น `standard form` แต่ behavior จริงที่ผู้ใช้เห็นอาจมีผลจาก custom ข้างต้น

## 2. หน้า 1: Home Dashboard

### Screenshot
- `01_home_dashboard.png`

### หน้านี้ใช้ทำอะไร
- เป็นจุดเริ่มต้นให้ผู้เรียนเห็นว่า flow purchase ไม่ได้อยู่ใน Purchase app อย่างเดียว
- ใช้ปูภาพรวมว่าต้องสลับดู `Purchase`, `Inventory`, `Accounting`

### Section ที่ควรอธิบาย

#### App Tiles
ไม่มี table แบบ grid แต่มี “กลุ่มเมนู” ที่ผู้เรียนต้องเข้าใจ

- `Purchase`
  ใช้สร้างหรืออนุมัติ PR/RFQ/PO
- `Inventory`
  ใช้รับของ, ดู stock movement, lot และ scrap
- `Accounting`
  ใช้สร้างหรือดู vendor bill และ journal items

### Odoo Standard
- หน้า app launcher เป็น standard

### Custom ของเรา
- ไม่มี custom logic หลักที่หน้าจอนี้โดยตรง
- แต่ flow ที่จะสอนถัดไปจะใช้ module custom หลายตัวในแต่ละ app

## 3. หน้า 2: Product Category - Raw Materials

### Screenshot
- `02_product_category_rm.png`

### หน้านี้ใช้ทำอะไร
- ใช้สอนว่าทำไม category สำคัญกับบัญชีและ valuation
- เป็นฐานของการตั้งค่าพวก cost method และ inventory valuation

### Section และ field สำคัญ

#### General Information
- `Category Name`
  ชื่อหมวดสินค้า ใช้จัดกลุ่มเชิงธุรกิจและ reporting
- `Parent Category`
  โครงสร้างหมวดสินค้า ใช้สืบทอด logic บางอย่างจากหมวดแม่

#### Inventory Valuation / Accounting Section
- `Costing Method`
  วิธีคำนวณต้นทุน เช่น AVCO, FIFO, Standard
- `Inventory Valuation`
  กำหนดว่าจะลงบัญชี stock อัตโนมัติหรือไม่
- `Stock Input Account`
  บัญชีรับของเข้า / GRNI / interim account
- `Stock Output Account`
  บัญชีของออก
- `Stock Valuation Account`
  บัญชี stock asset
- `Price Difference Account`
  บัญชีต่างราคาถ้ามี

### Odoo Standard
- category, costing method, inventory valuation เป็น standard Odoo

### Custom ของเรา
- ไม่มี custom field หลักใน screenshot นี้
- แต่ category ที่ตั้งถูกมีผลให้ flow ซื้อและบัญชีขององค์กรเราเดินถูก

### สิ่งที่ผู้สอนควรเน้น
- ถ้า category ผิด downstream ทางบัญชีจะผิดทั้งชุด
- ผู้ใช้งาน purchase ไม่ต้องแก้ตรงนี้เองทุกวัน แต่ต้องรู้ว่าเป็นต้นทางของ behavior

## 4. หน้า 3: Vendor Master

### Screenshot
- `03_vendor_master.png`

### หน้านี้ใช้ทำอะไร
- ใช้สอนว่าข้อมูล vendor เป็นเงื่อนไขให้ flow ซื้อจบ
- ใช้ชี้เรื่อง payment terms, bank account, purchase settings

### Section และ field สำคัญ

#### Header
- `Vendor Name`
  ชื่อคู่ค้า
- `Address`
  ที่อยู่สำหรับเอกสาร
- `Tax ID`
  ข้อมูลภาษี

#### Contacts & Addresses
- ลูกค้าหรือผู้ติดต่อย่อย
- ใช้แยก address สำหรับ billing / shipping / contact person

#### Sales & Purchase Tab
- `Payment Terms`
  กำหนดเงื่อนไขการจ่าย
- `Purchase Currency`
  สกุลเงินซื้อ
- `Vendor Reference`
  รหัสอ้างอิง supplier

#### Accounting Tab
- `Bank Accounts`
  ใช้โดยฝ่ายการเงิน
- `Payable Account`
  บัญชีเจ้าหนี้

### Odoo Standard
- partner master, payment term, bank account เป็น standard

### Custom ของเรา
- ถ้ามี module เช่น `purchase_request_vendor` ผู้ใช้จะเห็นความเชื่อม vendor กับ PR flow ชัดขึ้น
- บาง flow ของเราอาศัย vendor data เพื่อเร่งการสร้าง RFQ/PO

### สิ่งที่ผู้สอนควรเน้น
- ไม่มี vendor หรือข้อมูลไม่ครบ flow จะไปต่อได้ไม่สุด
- vendor ไม่ใช่แค่ชื่อ แต่เป็น master ที่กระทบ purchase และ accounting พร้อมกัน

## 5. หน้า 4: Create Purchase Requisition (PR Draft)

### Screenshot
- `04_create_pr.png`

### เอกสารตัวอย่าง
- `PR00004`

### หน้านี้ใช้ทำอะไร
- เป็นจุดเริ่มต้นของ flow ซื้อ
- ใช้สอนการขอซื้อจาก user/requester ไม่ใช่จาก buyer

### Section และ table สำคัญ

#### Header Fields
- `PR Number`
  เลขเอกสาร PR
- `Requested By`
  คนขอซื้อ
- `Department`
  แผนกผู้ขอ
- `Date`
  วันที่ขอ
- `Origin`
  reference ต้นทาง ถ้ามี
- `Analytic Account`
  ศูนย์ต้นทุนหรือแผนกที่รับภาระต้นทุน

#### PR Line Table
เป็น table ที่สำคัญที่สุดของหน้า PR

- `Product`
  สินค้าที่ขอซื้อ
- `Description`
  รายละเอียดเพิ่มเติมของรายการ
- `Quantity`
  จำนวนที่ต้องการ
- `UoM`
  หน่วยนับ
- `Required Date`
  วันที่ต้องการใช้งาน
- `Estimated Cost`
  มุมมองงบประมาณเบื้องต้น ถ้ามี
- `Vendor`
  supplier ที่แนะนำ ถ้ามี
- `Analytic`
  การผูกต้นทุนราย line ถ้ามี

### Odoo Standard / OCA
- โครงหลักของ `purchase.request` มาจาก module ฝั่ง purchase request

### Custom ของเรา
- `purchase_request_department`
  ทำให้ PR/line ผูกกับ department
- `purchase_request_analytic_required`
  บังคับ analytic ในกรณีที่กำหนด
- `purchase_request_vendor`
  ทำให้ line รองรับ vendor information มากขึ้น
- `budget_control_purchase_request`
  ใช้ PR line เป็นฐานของ budget commit

### สิ่งที่ผู้สอนควรเน้น
- PR เป็นเอกสาร “ขอซื้อ” ไม่ใช่ “สั่งซื้อ”
- table ของ PR line เป็นจุดที่ข้อมูลผิดแล้ว downstream จะผิดทั้งหมด

## 6. หน้า 5: Approved PR / Create RFQ

### Screenshot
- `05_approve_pr.png`

### เอกสารตัวอย่าง
- `PR00006`

### หน้านี้ใช้ทำอะไร
- ใช้สอน approval step และการส่งต่อไป RFQ/PO

### Section และ table สำคัญ

#### Header / Statusbar
- `State`
  draft, to approve, approved ฯลฯ
- `Approval Buttons`
  ปุ่มที่เกี่ยวกับ workflow เช่น approve, reject, create RFQ

#### PR Line Table
field หลักยังเหมือน draft แต่ตอนนี้เน้นดูว่า line ไหนพร้อมไปซื้อแล้ว

#### Smart Buttons / Related Documents
- ปุ่มเปิด RFQ/PO ที่สร้างจาก PR
- ปุ่ม trace เอกสาร downstream

### Odoo Standard / OCA
- purchase request core ใช้สร้าง RFQ จาก PR line

### Custom ของเรา
- `oi_workflow_purchase_request`
  approval workflow แบบหลายชั้น
- `purchase_request_custom`
  กันการสร้าง RFQ ซ้ำจาก line ที่ถูกครอบคลุมแล้ว
- `budget_control_purchase_request`
  เชื่อม budget check เข้ากับ PR approve

### สิ่งที่ผู้สอนควรเน้น
- PR approved ไม่ได้แปลว่า supplier ได้รับ order แล้ว
- PR approved เป็นแค่จุดที่ buyer เริ่มทำ RFQ/PO ได้

## 7. หน้า 6: Confirm PO

### Screenshot
- `06_confirm_po.png`

### เอกสารตัวอย่าง
- `P00017`

### หน้านี้ใช้ทำอะไร
- ใช้สอนการเปลี่ยนจาก RFQ เป็น PO จริง
- ใช้เชื่อม PO กับ receipt และ bill

### Section และ table สำคัญ

#### Header Fields
- `Vendor`
  คู่ค้าที่จะซื้อ
- `Vendor Reference`
  เลขอ้างอิงจาก supplier
- `Order Deadline`
  วัน deadline การสั่ง
- `Expected Arrival`
  วันที่คาดว่าจะได้รับ
- `Currency`
  สกุลเงิน
- `State`
  RFQ / Purchase Order / Done

#### PO Line Table
- `Product`
  ของที่จะซื้อ
- `Description`
  รายละเอียด
- `Quantity`
  จำนวน
- `UoM`
  หน่วยนับ
- `Unit Price`
  ราคา
- `Taxes`
  ภาษี
- `Planned Date`
  วันที่คาดว่าจะรับ
- `Subtotal`
  มูลค่าก่อนภาษี

#### Smart Buttons
- `Receipt`
  เปิดเอกสารรับของ
- `Bills`
  เปิด vendor bills
- อาจมี smart button เชื่อม PR ถ้า module เปิดใช้

### Odoo Standard
- purchase.order form และ lines เป็น standard

### Custom ของเรา
- `oi_workflow_purchase_order`
  approval flow ฝั่ง PO
- `po_purchase_request_smart_button`
  เพิ่มการเชื่อม PO กลับไป PR
- `vendor_billing_note`
  เพิ่มข้อมูล note ฝั่ง billing ในบางมุมมอง
- บางระบบยังมี `manual currency rate` เสริมบน PO ถ้าใช้หลายสกุลเงิน

### สิ่งที่ผู้สอนควรเน้น
- PO confirm แล้วเพิ่งเริ่มมีผลต่อ warehouse ผ่าน receipt
- ผู้เรียนต้องมอง PO เป็นเอกสารกลางที่เชื่อม vendor, receipt, bill และ PR

## 8. หน้า 7: Receipt with Lot / Traceability

### Screenshot
- `07_receipt_lot.png`

### เอกสารตัวอย่าง
- `GMP/IN/00034`
- lot `TRN-RM-LOT-01`

### หน้านี้ใช้ทำอะไร
- ใช้สอนการรับของเข้า stock
- ใช้ชี้เรื่อง lot/serial และ traceability ของ RM

### Section และ table สำคัญ

#### Header Fields
- `Operation Type`
  ประเภทเอกสารรับของ
- `Source Location`
  ต้นทาง เช่น vendor
- `Destination Location`
  ปลายทาง เช่น hold / stock
- `Scheduled Date`
  วันที่รับ
- `State`
  waiting / ready / done

#### Operations / Move Lines Table
table นี้สำคัญมากกับ training purchase

- `Product`
  ของที่รับ
- `Demand`
  จำนวนที่คาดว่าจะรับ
- `Done`
  จำนวนที่รับจริง
- `UoM`
  หน่วยนับ
- `From`
  source location
- `To`
  destination location
- `Lot/Serial`
  เลข lot
- `Package`
  ถ้ามีการใช้ package

#### Traceability / Lot Link
- ช่วยให้ย้อนกลับ lot ได้
- ใช้ตอบคำถามเรื่อง RM quality และ source tracking

### Odoo Standard
- stock picking และ lot traceability เป็น standard

### Custom ของเรา
- security หรือ location restriction บางอย่างอาจจำกัดการเห็นบาง location
- แต่ flow receipt และ lot บนหน้านี้เป็น standard เป็นหลัก

### สิ่งที่ผู้สอนควรเน้น
- RM ที่ต้อง trace ต้องมี lot
- receipt คือจุดที่ stock เพิ่มจริง
- อย่าสอนเพียงว่ากด validate ให้สอนว่าทำไม lot สำคัญ

## 9. หน้า 8: Scrap Operation

### Screenshot
- `08_scrap_operation.png`

### เอกสารตัวอย่าง
- `SP/00001`

### หน้านี้ใช้ทำอะไร
- ใช้สอนการตัดของเสียออกจาก stock อย่างเป็นทางการ

### Section และ field สำคัญ

#### Header Fields
- `Product`
  สินค้าที่ scrap
- `Quantity`
  ปริมาณที่ตัดออก
- `UoM`
  หน่วยนับ
- `Source Location`
  ที่ที่ของอยู่ก่อน scrap
- `Scrap Location`
  ที่ปลายทางของของเสีย
- `Lot/Serial`
  lot ที่ถูกตัด ถ้ามี
- `Source Document`
  เอกสารต้นทาง
- `State`
  draft / done

### Odoo Standard
- stock.scrap เป็น standard

### Custom ของเรา
- สิทธิ์และการ cancel scrap อาจถูกเสริมโดย module ฝั่ง cancel/permission
- แต่ logic scrap หลักใน training เป็น standard

### สิ่งที่ผู้สอนควรเน้น
- scrap ไม่ใช่แค่ “บอกว่าของเสีย” แต่เป็น stock movement จริง
- ถ้าจะตัด stock ต้องมีเอกสาร ไม่ควรแก้ on hand ตรง ๆ

## 10. หน้า 9: Asset PR

### Screenshot
- `09_asset_pr.png`

### เอกสารตัวอย่าง
- `PR00007`

### หน้านี้ใช้ทำอะไร
- ใช้สอนว่า asset ก็เริ่มจาก PR เหมือนกัน แต่เจตนาธุรกิจต่างจาก RM

### Section และ table สำคัญ

#### Header Fields
- `Requested By`
- `Department`
- `Analytic Account`
- `Origin`
- `State`

#### PR Line Table
- `Product`
  asset ที่ต้องการซื้อ
- `Quantity`
- `Description`
- `Required Date`
- `Analytic`
  เน้นมากสำหรับ asset / capex tracking

### Odoo Standard / OCA
- purchase request core

### Custom ของเรา
- analytic requirement และ department logic สำคัญมากในหน้า asset PR
- budget control อาจใช้ PR นี้เพื่อจับ commitment

### สิ่งที่ผู้สอนควรเน้น
- แม้เอกสารหน้าตาคล้าย RM PR แต่ปลายทางและความหมายทางบัญชีต่างกัน

## 11. หน้า 10: Asset Receipt / Destination Location

### Screenshot
- `10_asset_location.png`

### เอกสารตัวอย่าง
- `GMP/IN/00035`
- `GMP/Stock/Training Asset`

### หน้านี้ใช้ทำอะไร
- ใช้สอนว่าของประเภท asset ควรลง location ที่แยกจาก stock ปกติ

### Section และ table สำคัญ

#### Header Fields
- `Destination Location`
  จุดสำคัญที่สุดของหน้าจอนี้
- `State`
- `Receipt Date`

#### Operations Table
- `Product`
- `Done`
- `From`
- `To`

### Odoo Standard
- receipt และ destination location เป็น standard

### Custom ของเรา
- flow asset location เป็นการออกแบบการใช้งานขององค์กรเรา
- ไม่ใช่ custom model ใหม่ แต่เป็น process design บน Odoo

### สิ่งที่ผู้สอนควรเน้น
- แยก location ของ asset เพื่อคุมทะเบียนและการตามของ
- ทำให้ user เข้าใจว่ารับของเหมือน receipt ปกติ แต่ความหมายทางธุรกิจต่างกัน

## 12. หน้า 11: Asset Bill

### Screenshot
- `11_asset_bill.png`

### เอกสารตัวอย่าง
- bill จาก `P00018`

### หน้านี้ใช้ทำอะไร
- ใช้สอนการเชื่อม asset purchase เข้ากับ accounting

### Section และ table สำคัญ

#### Bill Header
- `Vendor`
- `Bill Date`
- `Accounting Date`
- `Invoice Origin`
  ใช้ trace กลับไป PO
- `State`

#### Invoice Lines Table
- `Product`
- `Description`
- `Account`
  สำคัญที่สุดในฝั่งบัญชี
- `Analytic`
- `Taxes`
- `Amount`

#### Journal Items Tab
- debit / credit lines
- account ปลายทาง
- tax / payable line

### Odoo Standard
- account.move bill form และ journal items เป็น standard

### Custom ของเรา
- ถ้ามี asset automation จาก category/setup จะทำให้ validate bill สร้าง asset record ต่อได้
- พฤติกรรมนี้เกิดจากการตั้ง category/account ไม่ใช่ custom หน้าฟอร์มหลัก

### สิ่งที่ผู้สอนควรเน้น
- asset flow ไม่ได้จบที่ receipt
- ต้อง trace ให้ถึง bill และ account mapping

## 13. หน้า 12: Consumable PR

### Screenshot
- `12_consumable_pr.png`

### เอกสารตัวอย่าง
- `PR00008`

### หน้านี้ใช้ทำอะไร
- ใช้สอนว่าของใช้สิ้นเปลืองก็ยังต้องมี PR และ approval ได้

### Section และ table สำคัญ

#### Header Fields
- requester / department / analytic

#### PR Line Table
- `Product`
- `Quantity`
- `Required Date`
- `Analytic`

### Odoo Standard / OCA
- โครง PR เหมือน RM และ Asset

### Custom ของเรา
- department / analytic / budget rules มีผลเหมือนกัน

### สิ่งที่ผู้สอนควรเน้น
- consumable ไม่ได้แปลว่าไม่ต้องคุมเอกสาร
- สิ่งที่ต่างอยู่ downstream ไม่ใช่แค่หน้า PR

## 14. หน้า 13: Consumable Receipt

### Screenshot
- `13_consumable_receipt.png`

### เอกสารตัวอย่าง
- `GMP/IN/00036`

### หน้านี้ใช้ทำอะไร
- ใช้สอนว่าของ consumable ยังมี receipt เพื่อยืนยันการรับของ

### Section และ table สำคัญ

#### Header
- operation type
- source / destination
- state

#### Operations Table
- `Product`
- `Demand`
- `Done`
- `From`
- `To`

### Odoo Standard
- stock receipt เป็น standard

### Custom ของเรา
- ไม่มี custom screen หลัก
- process interpretation ของ consumable เป็น business policy ของเรา

### สิ่งที่ผู้สอนควรเน้น
- receipt ของ consumable มีไว้ยืนยันว่าของมาถึงจริง
- downstream ของ cost/valuation อาจไม่เหมือน stockable จึงต้องอธิบายเชิง policy เพิ่ม

## 15. หน้า 14: Service PO

### Screenshot
- `14_service_po.png`

### เอกสารตัวอย่าง
- `P00019`

### หน้านี้ใช้ทำอะไร
- ใช้สอน flow ซื้อบริการ

### Section และ table สำคัญ

#### Header
- `Vendor`
- `Order Date`
- `State`
- `Currency`

#### PO Line Table
- `Service Product`
  รายการบริการ
- `Quantity`
  ปริมาณบริการ
- `Unit Price`
- `Taxes`
- `Description`

#### Smart Buttons
- `Bills`
- ปุ่มเกี่ยวกับ `Service Acceptance` ถ้าเปิดใช้ใน custom

### Odoo Standard
- purchase.order standard รองรับ service product

### Custom ของเรา
- `purchase_service_acceptance`
  เพิ่ม flow รับบริการจริงก่อนบิล
- `oi_workflow_purchase_order`
  อาจมีผลกับการอนุมัติ

### สิ่งที่ผู้สอนควรเน้น
- service ไม่มี warehouse receipt แบบ stockable
- แต่ใน process ของเรา มีจุดควบคุมชื่อ `Service Acceptance`

## 16. หน้า 15: Service Acceptance

### Screenshot
- `15_service_entry.png`

### เอกสารตัวอย่าง
- `SA/2026/0001`

### หน้านี้ใช้ทำอะไร
- ใช้สอน “receipt ของ service” ในระบบเรา

### Section และ table สำคัญ

#### Header Fields
- `Acceptance Number`
  เลขเอกสารรับบริการ
- `Purchase Order`
  PO ที่เกี่ยวข้อง
- `Vendor`
- `Date`
- `State`

#### Acceptance Line Table
table นี้คือหัวใจของ custom หน้า service acceptance

- `Product / Service`
  บริการที่รับ
- `Ordered Quantity`
  ปริมาณที่สั่ง
- `Accepted Quantity`
  ปริมาณที่รับผลงานจริง
- `UoM`
- `Description`
- อาจมี remarks หรือสถานะย่อย แล้วแต่ form

### Odoo Standard
- ไม่มีเอกสารนี้ใน purchase standard แบบเดียวกัน

### Custom ของเรา
- มาจาก `purchase_service_acceptance`
- ใช้แทนแนวคิด receipt สำหรับ service product
- update received quantity บน PO line ตาม acceptance

### สิ่งที่ผู้สอนควรเน้น
- จุดนี้เป็นของ custom เรา ไม่ใช่ Odoo standard
- business meaning คือ “ห้ามปล่อย flow การจ่ายเงินของ service โดยไม่ยืนยันว่ารับงานแล้ว”

## 17. หน้า 16: Vendor Bill and Journal Items

### Screenshot
- `16_vendor_bill_je.png`

### เอกสารตัวอย่าง
- bill จาก `P00019`

### หน้านี้ใช้ทำอะไร
- ใช้ปิด training ด้วยมุมมองทางบัญชี

### Section และ table สำคัญ

#### Bill Header
- `Vendor`
- `Bill Date`
- `Invoice Origin`
- `State`

#### Invoice Lines Table
- `Product`
- `Description`
- `Account`
- `Analytic`
- `Taxes`
- `Subtotal`

#### Journal Items Table
table นี้สำคัญที่สุดด้าน accounting

- `Account`
  บัญชีที่ได้รับผลกระทบ
- `Label`
  คำอธิบาย line
- `Debit`
- `Credit`
- `Tax Grids`
- `Partner`
- `Analytic`

### Odoo Standard
- vendor bill และ journal items เป็น standard

### Custom ของเรา
- ถ้า PO หรือ PR มีข้อมูล analytic / department / note พิเศษ ข้อมูลบางส่วนอาจไหลลงมาถึง bill
- แต่โครงบัญชีหลักยังเป็นของ Odoo standard

### สิ่งที่ผู้สอนควรเน้น
- purchase flow ที่ดีต้อง trace จากขอซื้อจนถึงเจ้าหนี้ได้
- คนซื้อไม่ต้องลงบัญชีเอง แต่ต้องรู้ว่าผลปลายทางเป็นอย่างไร

## 18. สรุปว่าแต่ละหน้าควรอธิบาย “standard” หรือ “custom” ยังไง

### เน้นเป็น Odoo Standard
- Home
- Product Category
- Vendor Master
- PO form
- Receipt
- Scrap
- Bill / Journal Items

### เน้นว่าเป็น OCA / custom ecosystem
- PR pages
- Approval behavior บน PR/PO
- Budget / analytic / department rules ใน PR
- Service Acceptance
- PR to RFQ protection / anti-duplicate logic

## 19. ประโยคสั้นสำหรับผู้สอนเวลาอธิบายแต่ละหน้า

- “หน้านี้เป็น standard ของ Odoo แต่ behavior ปลายทางขึ้นกับ setting ของเรา”
- “หน้านี้เป็น custom ของเราเพื่อปิด gap ด้าน control”
- “table นี้คือจุดที่ข้อมูลต้นทางไหลลงทั้ง warehouse และ accounting”
- “ถ้าตรงนี้ผิด downstream จะผิดทั้ง flow”
