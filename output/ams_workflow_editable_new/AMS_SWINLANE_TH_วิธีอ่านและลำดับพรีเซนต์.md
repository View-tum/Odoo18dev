# AMS Swimlane ภาษาไทย: วิธีอ่าน Flow และลำดับการ Present

## วัตถุประสงค์ของเอกสาร

เอกสารนี้ใช้คู่กับไฟล์ `AMS_SWINLANE_TH_PRESENT.drawio` เพื่อ present Business Flow ที่แปลงจาก Excel Requirement ไปเทียบกับ Odoo AMS DB โดยยึดหลัก Standard First, Custom Later

สิ่งที่ต้องตอบระหว่าง present:

- Odoo Standard รองรับ flow นี้ตรงไหน
- จุดไหนเป็น configuration หรือ master data setup
- จุดไหนเป็น pain point ที่อาจต้อง custom/report
- จุดไหนกระทบ Stock, Costing, Accounting หรือ Approval
- ข้อมูลอะไรต้องเตรียมก่อน UAT

## วิธีอ่าน Swimlane Flow แบบละเอียด

### 1. อ่านจากซ้ายไปขวา

ให้เริ่มจากกล่อง `Start` ทางซ้าย แล้วไล่ตามลูกศรไปทางขวาเสมอ ถ้ามีลูกศรย้อนกลับ ให้ตีความเป็น loop ของงาน เช่น Rework, Replenishment, Revision หรือ Re-approval

จุดที่ไม่ควรข้ามคือ Decision เพราะเป็นจุดที่ระบบเปลี่ยนเส้นทาง เช่น `Approved?`, `QC pass?`, `Buy or Make?`, `Stock enough?`

### 2. อ่านตาม Swimlane

แต่ละ Swimlane คือเจ้าของงาน, แผนก หรือ Odoo module ที่รับผิดชอบ ถ้าเส้น flow ข้าม lane แปลว่ามีการ handoff ข้อมูลหรือเอกสารจากฝ่ายหนึ่งไปอีกฝ่ายหนึ่ง

เวลาตรวจ flow ให้ถาม 4 เรื่องที่จุดข้าม lane:

- ใครเป็น owner ของขั้นตอนนี้
- ข้อมูลส่งต่อคืออะไร
- เอกสาร Odoo ที่ถูกสร้างคืออะไร
- ต้องมี approval หรือ validation หรือไม่

### 3. อ่านจากสัญลักษณ์

| Symbol | ความหมาย | วิธีใช้ถามใน workshop |
|---|---|---|
| Start / End | จุดเริ่มหรือจบ flow | Trigger คืออะไร และจบเมื่อเอกสาร/สถานะอะไร |
| Process | งานที่ user หรือ Odoo ทำ | ทำใน Odoo app ไหน และทำ manual หรือ automate |
| Decision | จุดตัดสินใจ | ใครตัดสินใจ ใช้ข้อมูลอะไร มีทางออกกี่ทาง |
| Input / Output | ข้อมูลเข้า/ผลลัพธ์ | Source data มาจากไหน format อะไร |
| Document | เอกสาร Odoo | SO, PO, MO, Invoice, Receipt, Delivery คือเลขเอกสารหลัก |
| Database | Master/Transaction data | ต้อง setup master อะไร และ data นี้กระทบ module ไหน |
| Custom / Report Candidate | จุดที่ standard ยังไม่ตอบครบ | เป็น config, report, import, automation หรือ custom code |

### 4. อ่าน Standard vs Pain Point

ถ้าเป็น process/document/database มาตรฐาน ให้เริ่มตอบด้วย Odoo Standard ก่อน เช่น Sales, Purchase, Inventory, MRP, Quality, Accounting, Approval, Barcode

ถ้าเป็น custom/report candidate อย่ารีบสรุปว่า custom ทันที ให้แยกเป็น 4 ระดับ:

- Standard ทำได้เลย
- Standard ทำได้แต่ต้อง config/master data
- ต้องทำ report/import/automation เพิ่ม
- ต้อง custom จริง เพราะ standard ไม่มี business rule นั้น

### 5. อ่านผลกระทบ Accounting & Stock

ขั้นตอนที่เกี่ยวกับ stock.move, stock valuation, WIP, FG, COGS, Invoice, Vendor Bill, Payment ต้องตรวจเป็นพิเศษ เพราะถ้าออกแบบผิดจะกระทบต้นทุนและงบการเงิน

หลักที่ใช้ตอบคือ ห้ามแก้ stock/cost/accounting ด้วย manual SQL หรือ logic ที่ไม่ผ่าน Odoo model มาตรฐาน

## ลำดับการ Present ตั้งแต่ต้นจนจบ

### ช่วงที่ 1: เปิดการนำเสนอ

เวลาแนะนำ: 3-5 นาที

พูดให้ชัดว่า flow นี้สร้างจาก Excel Requirement และถูก mapping กับ Odoo AMS DB โดยเน้นการใช้ Standard Odoo ก่อน custom จุดประสงค์ไม่ใช่แค่ดูภาพสวย แต่ใช้เป็นเอกสารตัดสินใจว่า implementation จะทำอะไรบ้าง

Key message:

- AMS DB setup เป็นฐานสำหรับทดลอง standard flow
- Diagram แยกเป็นภาพรวมและ flow ราย module
- สีส้มคือจุดที่ยังต้องหารือ ไม่ใช่สรุปว่าต้อง custom แล้วเสมอ

### ช่วงที่ 2: อธิบายวิธีอ่านและ Symbol

เวลาแนะนำ: 5 นาที

เปิดหน้า `00 วิธีอ่าน Flow` และ `02 คำอธิบายสัญลักษณ์`

พูดตามลำดับ:

1. อ่านซ้ายไปขวา
2. อ่านตาม lane เพื่อดู owner
3. Decision คือจุดที่ต้องมี business rule
4. Document คือเอกสาร Odoo ที่ตรวจสอบได้
5. Database คือ master/transaction ที่ต้อง setup
6. Custom/Report Candidate คือ pain point ที่ต้องแยกระดับ

### ช่วงที่ 3: Present ภาพรวม End-to-End

เวลาแนะนำ: 8-10 นาที

เปิดหน้า `03 ภาพรวม AMS End-to-End`

ลำดับพูด:

1. เริ่มจาก Customer Forecast / PO / RFQ
2. Sales สร้าง Quotation/SO
3. ถ้า won แล้วส่ง demand เข้า MRP/Replenishment
4. ระบบตัดสินใจว่าต้องซื้อ, ผลิต หรือใช้ stock ที่มี
5. Procurement ออก RFQ/PO/Blanket และรับสินค้าเข้า warehouse
6. Manufacturing สร้าง MO/Work Orders และ QC
7. Warehouse จัด FG stock และ delivery
8. Accounting ทำ invoice/bill/payment และ valuation
9. Management ดู dashboard/report เพื่อใช้ตัดสินใจ

จุดเน้น:

- ภาพนี้คือ flow ใหญ่ ไม่ลง detail ทุก field
- จุดข้าม module คือจุดสำคัญของ data handoff
- Pain point ใหญ่จะไปแตกในแต่ละ module

### ช่วงที่ 4: Sales / CRM

เวลาแนะนำ: 6-8 นาที

เปิดหน้า `04 Sales / CRM`

สิ่งที่ต้องพูด:

- Trigger คือ Customer Inquiry/RFQ
- Standard Odoo รองรับ CRM, Quotation, Sales Order, Customer PO Ref, Pricelist, Margin และ Sales Analysis
- ถ้าต้องคิดราคาจาก BOM หรือ PPAP Costing Template จะเป็น custom/report candidate
- เมื่อ SO confirmed จะส่ง demand ไป Inventory/MRP

คำถามที่ควรถามทีม:

- ใช้ quotation revision อย่างไร
- Margin ต้องดูระดับ line, order, product หรือ customer
- Customer forecast เข้ามาเป็นไฟล์หรือ manual entry
- ต้องการ approval ก่อนส่ง quotation หรือไม่

### ช่วงที่ 5: Procurement

เวลาแนะนำ: 8-10 นาที

เปิดหน้า `05 Procurement`

สิ่งที่ต้องพูด:

- Trigger มาจาก MRP shortage, min/max, manual PR หรือ service request
- Standard Odoo รองรับ RFQ, PO, Blanket Agreement, Approval, Receipt และ Vendor Bill
- 3-way match ต้องโยง PO, Receipt และ Vendor Bill
- Supplier scorecard เป็น pain point ที่อาจต้อง report/custom ถ้าต้อง weighted score

คำถามที่ควรถามทีม:

- มี PR จริงก่อน PO หรือใช้ Approval แทนได้
- Approval rule อิงวงเงิน, budget, product category หรือ department
- Supplier evaluation ใช้คะแนนอะไร เช่น price, OTD, quality, credit
- Blanket Agreement ต้องคุมราคาและช่วงเวลาอย่างไร

### ช่วงที่ 6: Warehouse / Logistics

เวลาแนะนำ: 7-9 นาที

เปิดหน้า `06 Warehouse / Logistics`

สิ่งที่ต้องพูด:

- Standard Odoo รองรับ Receipt, Delivery, Internal Transfer, Barcode, Lot/Serial, Location, Reordering Rule
- Shelf/QC/WIP location ใน AMS ถูก setup เพื่อรองรับการ track stock
- Delivery Method และ Fleet เป็น standard ที่ใช้ต่อยอด logistics ได้
- Slow/dead stock dashboard เป็น report candidate

คำถามที่ควรถามทีม:

- ต้องบังคับ Lot/Serial กับ product ไหน
- ต้อง scan ทุก operation หรือเฉพาะ receipt/delivery
- Shelf location ลึกถึงระดับใด
- KPI stock aging/slow moving คำนวณจากวันไหน

### ช่วงที่ 7: Manufacturing / Quality

เวลาแนะนำ: 10-12 นาที

เปิดหน้า `07 Manufacturing / Quality`

สิ่งที่ต้องพูด:

- Standard Odoo รองรับ BOM, Routing, Work Centers, MO, Work Orders, Quality Points, Barcode MRP และ Stock Accounting
- AMS.400 REV 00 เป็นตัวอย่าง BOM พร้อม routing หลาย operation
- Decision สำคัญคือ Components available? และ QC pass?
- ถ้า QC fail ต้องระบุว่า rework, scrap หรือ quality alert
- OEE/OPE, DPPM และ variance allocation เป็น custom/report candidate

คำถามที่ควรถามทีม:

- ต้อง track WIP ตาม process หรือ location
- Waste/scrap เก็บที่ operation ไหน
- Quality point ต้องเกิดก่อน/ระหว่าง/หลัง operation
- Cost variance ต้องแยก material, labor, overhead หรือ machine

### ช่วงที่ 8: Accounting / Finance

เวลาแนะนำ: 8-10 นาที

เปิดหน้า `08 Accounting / Finance`

สิ่งที่ต้องพูด:

- Source document มาจาก SO, PO, MO, Receipt, Delivery
- Standard Odoo รองรับ AR/AP, multicurrency, bank statement import, reconciliation, analytic budget และ stock valuation
- Budget hard lock, cash forecast, consolidation อาจเป็น custom/report candidate
- ต้องรักษา Accounting & Stock Integrity โดยไม่แก้ valuation/accounting แบบ manual

คำถามที่ควรถามทีม:

- ใช้ FIFO, AVCO หรือ Standard Cost กับ product กลุ่มใด
- Budget control ต้อง warning หรือ hard block
- Cash forecast ต้องรวม PR/PO/AP/AR ระดับไหน
- Consolidation ต้องรวมบริษัทหรือ branch อย่างไร

### ช่วงที่ 9: Planning / MRP / Master Data

เวลาแนะนำ: 7-9 นาที

เปิดหน้า `09 Planning / MRP Master Data`

สิ่งที่ต้องพูด:

- Master data คือฐานของ flow ทั้งหมด เช่น Product, UoM, MOQ, Route, Lead Time, BOM, Routing
- Standard Odoo รองรับ MRP/Replenishment, Buy/Make, Min/Max, Vendor Lead Time
- Rolling Forecast import และ Forecast-to-Invoice KPI เป็น candidate ที่ต้องออกแบบเพิ่ม

คำถามที่ควรถามทีม:

- Forecast format มาจากลูกค้าแบบใด
- MOQ และ lead time อยู่ที่ product หรือ vendor
- BOM revision control ต้อง strict แค่ไหน
- MRP run ต้อง manual, scheduled หรือ auto ตามรอบ

### ช่วงที่ 10: สรุป Standard vs Pain Point

เวลาแนะนำ: 5-7 นาที

สรุปเป็น 4 กลุ่ม:

- Standard ได้เลย: Sales, Purchase, Inventory, MRP, Quality, Accounting, Barcode, Approval, Fleet บางส่วน
- ต้อง config/master: Analytic BU/Branch, product route, BOM/routing, quality point, location, valuation, budget
- Report/automation candidate: Supplier score, slow/dead stock, cash forecast, forecast accuracy, OEE/OPE, DPPM
- Custom candidate: Budget hard lock, automotive forecast import, variance allocation rule, PPAP/BOM costing template

### ช่วงที่ 11: ปิดการนำเสนอด้วย Next Step

เวลาแนะนำ: 5 นาที

เสนอ action ต่อ:

1. ยืนยัน owner ของแต่ละ swimlane
2. ตรวจ master data ที่ต้อง setup ใน AMS
3. แยก requirement เป็น Standard / Config / Report / Custom
4. ทำ UAT scenario จาก flow แต่ละหน้า
5. ตัดสินใจ custom เฉพาะจุดที่ standard ไม่ตอบโจทย์จริง

## Checklist ก่อนใช้ Present

- เปิดไฟล์ drawio แล้วดูหน้าครบ 10 หน้า
- เริ่ม present จากหน้า `00 วิธีอ่าน Flow`
- ใช้หน้า Overall ก่อนลง module
- ทุกครั้งที่เจอกล่องสีส้ม ให้จดเป็น discussion item
- ทุกขั้นที่กระทบ Stock/Accounting ให้ถามเรื่อง valuation, posting และ owner
- ปิดท้ายด้วย action list ไม่ใช่ปิดด้วย diagram อย่างเดียว
