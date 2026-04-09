# Manufacturing Training: Trainer Click Guide

เอกสารนี้ใช้สำหรับผู้สอนเท่านั้น ให้เปิดคู่กับ deck training และระบบ Odoo จริง เพื่อพาผู้เรียนเดินตาม flow แบบทีละหน้า ทีละเอกสาร

ใช้คู่กับไฟล์ต่อไปนี้

- [manufacturing_training_uat_detailed_plain_20260331.pptx](./manufacturing_training_uat_detailed_plain_20260331.pptx)
- [manufacturing_training_uat_detailed_plain_speaker_20260331.txt](./manufacturing_training_uat_detailed_plain_speaker_20260331.txt)
- [04_odoo_walkthrough.md](./04_odoo_walkthrough.md)

## 1. เตรียมก่อนเริ่มสอน

1. เปิดฐานที่ใช้สอนให้ถูกก่อน ว่าเป็น `UAT` หรือฐาน demo ที่ตกลงกันไว้
2. เปิด PowerPoint ไว้หนึ่งจอ และเปิด Odoo ไว้อีกจอ
3. เปิด Developer Mode ถ้าต้องการชี้ field เชิงตั้งค่า
4. เตรียม search bar ของแต่ละ app ให้พร้อมใช้
5. ให้จำเลขเอกสารตัวอย่างเหล่านี้ให้ได้ก่อนขึ้นสอน

- `FG-PSS-TH-01005` สินค้าตัวอย่างสำหรับสอน Product, Min/Max, BoM
- `S11563` promotion quotation
- `SOB-263069` FOC / SO 0 บาท
- `SOB-263070` SO -> MTO
- `GMP/MOPH/00011` MO จาก replenishment
- `GMP/MOPH/00001` trace งานผลิต 100000
- `GMP/MOPL/00014` plastic MO สำหรับ shopfloor / mold
- `SP/00011` scrap document
- `GMP/TRPL/00006` transfer plastic
- `GMP/TRPH/00001` transfer pharma
- `INV-D/26/04/00001` invoice / accounting endpoint

## 2. โครงเวลา 3 ชั่วโมง

### 09:00-09:20 Opening และภาพรวมระบบ
- Slide 1-4
- เป้าหมายคือให้ผู้เรียนเห็นภาพรวมว่า flow manufacturing ไม่ได้อยู่ในเมนูเดียว แต่โยงกันทั้ง Sales, Inventory, Manufacturing, Purchase และ Accounting

### 09:20-09:50 Settings และ Master Data
- Slide 5-8
- เป้าหมายคือให้ผู้เรียนรู้ว่า Product, Routes, Min/Max และ BoM คือจุดตั้งต้นของระบบ auto

### 09:50-10:20 Promotion / SO 0 บาท และ SO -> MTO
- Slide 9-12
- เป้าหมายคือให้ผู้เรียนเห็นความต่างของ demand ที่มาจาก sale และความต่างของ FOC กับ MTO

### 10:20-10:45 MTS / Replenishment
- Slide 13-14
- เป้าหมายคือให้ผู้เรียนเข้าใจว่า Min/Max ยิง MO อย่างไร และเมื่อไรไม่ต้องรอ SO

### 10:45-11:20 Shopfloor, Workorder และ Scrap
- Slide 15-18
- เป้าหมายคือให้ production และ supervisor เห็น execution page จริง

### 11:20-11:45 Mold, Transfer และ Inventory Linkage
- Slide 19-21
- เป้าหมายคือให้ผู้เรียนเห็นว่าฝั่ง plastic และ pharma เชื่อมกันตรงไหน และ mold ใช้ยังไง

### 11:45-12:00 Invoice, Costing และ Closing Checklist
- Slide 22-23
- เป้าหมายคือให้ผู้เรียน trace ปลายทางถึง accounting ได้ และรู้จุดตรวจหลักก่อนใช้งานจริง

## 3. Click-by-Click ต่อสไลด์

## Slide 1: Opening

### สิ่งที่พูด
- วันนี้จะสอน Manufacturing แบบ end-to-end ตั้งแต่ setting ไปจนถึงเอกสารปลายทาง
- ภาพทั้งหมดใช้จากระบบจริง ไม่ใช่ mockup
- เป้าหมายไม่ใช่แค่กดเมนูได้ แต่ต้องตอบได้ว่า demand 1 ตัววิ่งไปที่ไหนบ้าง

### สิ่งที่ต้องทำ
- ยังไม่ต้องคลิกในระบบ

## Slide 2: Agenda

### สิ่งที่พูด
- วันนี้เราจะเรียน 3 flow หลักคือ Promotion, MTO และ MTS/Min-Max
- หลังจากนั้นจะต่อด้วย Shopfloor, Scrap, Mold, Transfer และ Costing
- ช่วงท้ายจะปิดด้วย checklist สำหรับใช้งานจริง

### สิ่งที่ต้องทำ
- ยังไม่ต้องคลิกในระบบ

## Slide 3: Home Dashboard

### คลิก
1. เปิดหน้า `Home`
2. ใช้เมาส์ชี้ `Sales`
3. ใช้เมาส์ชี้ `Inventory`
4. ใช้เมาส์ชี้ `Manufacturing`
5. ใช้เมาส์ชี้ `Purchase`
6. ใช้เมาส์ชี้ `Accounting`
7. ใช้เมาส์ชี้ `GMP Shop Floor`

### สิ่งที่อธิบาย
- flow manu ของเราไม่ได้จบใน Manufacturing app อย่างเดียว
- ถ้าจะ trace ปัญหาให้จบ ต้องสลับดูหลาย app
- Sales เป็นจุดเริ่มของ MTO และ FOC
- Inventory เป็นจุดดู stock, transfer, min/max และ scrap
- Manufacturing เป็นศูนย์กลางของ MO, WO, BoM
- Purchase จะถูกใช้เมื่อ shortage วิ่งไป Buy route
- Accounting เป็นปลายทางของ invoice และผลกระทบด้านบัญชี

## Slide 4: Manufacturing Overview

### คลิก
1. เข้า `Manufacturing`
2. เปิด `Overview`
3. ชี้เมนูด้านบน `Operations`
4. ชี้เมนู `Products`
5. ชี้เมนู `Reporting`
6. ชี้เมนู `Configuration`

### สิ่งที่อธิบาย
- Overview เป็นหน้าที่หัวหน้างานหรือ planner ใช้ดูภาพรวม
- Operations ใช้เจาะ MO, WO และ execution docs
- Products ใช้ดู master data เช่น Product, BoM
- Configuration ใช้ดู workcenter, operation type และ setting หลัก
- ให้ผู้เรียนจำว่าเวลางานไม่วิ่ง ต้องรู้ก่อนว่าจะเริ่ม trace จากเมนูไหน

## Slide 5: Product Master ของ FG-PSS-TH-01005

### คลิก
1. ไป `Manufacturing > Products > Products`
2. ค้นหา `FG-PSS-TH-01005`
3. เปิดสินค้านี้
4. ชี้ `Product Type`
5. ชี้ `Manufacturing Type`
6. ชี้ smart button เช่น `On Hand`, `Forecasted`, `Bill of Materials`

### สิ่งที่อธิบาย
- product master เป็นจุดเริ่มของ logic หลายอย่าง
- `Product Type` บอกว่าสินค้าถูกคุมเชิง stock แบบไหน
- `Manufacturing Type` บอกว่าของนี้อยู่ฝั่ง Plastic หรือ Pharma
- smart buttons ช่วยให้ trace ของจริงได้ทันทีจากหน้าเดียว
- ตัวอย่างนี้สำคัญเพราะเป็น FG ที่ใช้สอน Min/Max และ child chain

## Slide 6: Product Inventory และ Routes

### คลิก
1. อยู่หน้าเดิมของ `FG-PSS-TH-01005`
2. เข้าแท็บ `Inventory`
3. ชี้ `Routes`
4. ชี้ `Category Routes` ถ้ามีให้เห็น
5. ถ้าเปิดได้ ให้กด `View Diagram`

### สิ่งที่อธิบาย
- route คือคำตอบของคำถามว่า shortage แล้วจะไปทางไหน
- ต้องแยกให้ได้ระหว่าง route บน product กับ route ที่ inherited มาจาก category
- ตัวนี้ใช้ Min/Max ไม่ใช่ MTO ตรงจาก SO
- ถ้าผู้เรียนจำได้ว่าดู route ที่ไหน เวลาระบบไม่สร้าง MO/PO จะวิเคราะห์ง่ายขึ้น

## Slide 7: Reordering Rule / Min-Max

### คลิก
1. ไป `Inventory > Configuration > Reordering Rules`
2. ค้นหา `FG-PSS-TH-01005`
3. เปิด rule ของสินค้า
4. ชี้ `Location`
5. ชี้ `Min Quantity`
6. ชี้ `Max Quantity`
7. ชี้ `Route`
8. ชี้ `Trigger`

### สิ่งที่อธิบาย
- จุดนี้คือหัวใจของ MTS / Min-Max
- ถ้าของพอ ระบบไม่ทำอะไร
- ถ้าของต่ำกว่า min หรือ forecast ติดลบ ระบบจะสร้าง procurement จากจุดนี้
- procurement จะไป MO หรือ PO ขึ้นกับ route
- ใช้หน้าจอนี้ตอบคำถามเรื่อง “ทำไมตัวนี้ไม่วิ่งจาก SO”

## Slide 8: BoM ของ FG-PSS-TH-01005

### คลิก
1. ไป `Manufacturing > Products > Bills of Materials`
2. ค้นหา `FG-PSS-TH-01005`
3. เปิด BoM
4. ชี้ `BoM Type`
5. ชี้ `Operation Type`
6. ชี้ component หลัก
7. ถ้ามี structure button ให้กดดู child structure

### สิ่งที่อธิบาย
- BoM บอกว่าสินค้าตัวแม่ต้องการอะไรบ้าง
- `Operation Type` ช่วยบอกว่าฝั่งไหนเป็น Plastic และฝั่งไหนเป็น Pharma
- ผู้ใช้ไม่ควรดูแค่ตัวแม่ แต่ต้องเข้าใจว่ามันแตก requirement ลง child ได้
- ตัวอย่างนี้ใช้ดีเพราะมีทั้ง FG, SM และ SO อยู่ใน chain เดียว

## Slide 9: Promotion Quote

### คลิก
1. ไป `Sales > Quotations`
2. เปิด `S11563`
3. ชี้ order lines
4. ชี้ free line ที่ราคา `0`
5. ชี้ยอดรวมด้านล่าง

### สิ่งที่อธิบาย
- Promotion flow เริ่มจาก quotation / sales document เหมือน sale ปกติ
- free item ถูกเติมเข้า order line ใน order เดียวกัน
- ราคา 0 ไม่ได้แปลว่าไม่ต้องวิ่ง stock
- ผู้เรียนต้องจำว่าการเป็น FOC ไม่ได้ตัด requirement ฝั่ง inventory และ production

## Slide 10: FOC Full Flow

### คลิก
1. ไป `Sales > Orders`
2. เปิด `SOB-263069`
3. ชี้ statusbar
4. ชี้ smart buttons ของ delivery และ invoice
5. ชี้ order lines อีกครั้ง

### สิ่งที่อธิบาย
- นี่คือ FOC flow ที่จบจริง
- ถึงแม้จะมีของแถมหรือยอดขายบางส่วนเป็นศูนย์ ระบบยังต้องส่งของจริง
- ผู้ใช้ต้อง trace ไป delivery และ invoice ให้ครบ

## Slide 11: SO -> MTO Example

### คลิก
1. ไป `Sales > Orders`
2. เปิด `SOB-263070`
3. ชี้ delivery smart button
4. ชี้ invoice smart button
5. ชี้ order line quantity และสถานะ delivered / invoiced

### สิ่งที่อธิบาย
- demand ตัวนี้มาจาก sale แล้วต่อไป production
- ถ้า setup ถูก ผู้ใช้ไม่ควรเปิด MO ลูกเอง
- ให้เปรียบเทียบกับ FOC ว่า UI คล้ายกัน แต่ intent และ downstream ต่างกัน

## Slide 12: Child MO / MTO Chain

### คลิก
1. จาก `SOB-263070` กด smart button ที่เกี่ยวกับ production หรือ delivery trace
2. เปิด MO ที่เกี่ยวข้อง
3. ชี้ child chain ถ้ามีหลายใบ
4. ชี้ origin และ document linkage

### สิ่งที่อธิบาย
- จุดนี้ใช้ย้ำว่า sale line สามารถแตก child MO ได้เอง
- ผู้เรียนต้องเข้าใจว่าถ้าไม่เกิด MO ลูก มักเป็นปัญหา setting ไม่ใช่ปัญหาผู้ใช้กดไม่ครบ

## Slide 13: Replenishment Example

### คลิก
1. ไป `Inventory > Configuration > Reordering Rules`
2. ค้นหา `FG-PNC-TH-01001`
3. เปิด rule หรือชี้รายการใน list

### สิ่งที่อธิบาย
- ตัวนี้ใช้แทน flow MTS ที่ไม่ต้องมี SO
- เป็นตัวอย่างว่าระบบเติม stock ตาม Min/Max ได้อย่างไร
- ใช้แยก concept จาก MTO ให้ผู้เรียนชัดเจน

## Slide 14: MO จาก Replenishment

### คลิก
1. ไป `Manufacturing > Operations > Manufacturing Orders`
2. เปิด `GMP/MOPH/00011`
3. ชี้ `Origin`
4. ชี้ `Product`
5. ชี้ `BoM`
6. ชี้ `Component Status`
7. ชี้ smart buttons เช่น `Work Orders`, `Transfers`, `MO Cost`

### สิ่งที่อธิบาย
- ตัวนี้ไม่ได้มาจาก SO แต่มาจาก replenishment
- ใช้สอนว่าก่อนเริ่มงาน production ต้องดู component readiness
- smart buttons เป็นทางลัดในการ trace execution กับ cost

## Slide 15: Work Order

### คลิก
1. ไป `Manufacturing > Operations > Work Orders`
2. เปิด work order ที่ใช้ใน training เช่น operation ของ `GMP/MOPL/00014`
3. ชี้ `Work Center`
4. ชี้ `Product`
5. ชี้ `Qty Produced`
6. ชี้ `Expected Duration`
7. ชี้ `Time Tracking`

### สิ่งที่อธิบาย
- หน้านี้คือ operational truth ของ shopfloor
- ใช้ดูว่า operator กำลังทำอะไร ที่เครื่องไหน
- เวลาและ quantity ตรงนี้มีผลต่อ actual cost
- ถ้า workorder ผิด machine หรือ qty เพี้ยน downstream จะเพี้ยนตาม

## Slide 16: GMP Shop Floor Dashboard

### คลิก
1. ไป `GMP Shop Floor`
2. เปิด `Dashboard`
3. สลับดู `Plastic Shop Floor`
4. สลับดู `Pharma Shop Floor`
5. ใช้ search หรือ filter หา MO ตัวอย่าง
6. ชี้ปุ่ม `Open Console`

### สิ่งที่อธิบาย
- นี่คือหน้าที่หัวหน้างานใช้จริงทุกวัน
- card view ทำให้เห็นงาน Ready, In Progress, Done
- ปัจจุบันงานที่ cancel ไม่ควรโชว์ให้ operator ใช้งานต่อ
- ผู้เรียนควรจำว่าหน้านี้ไว้ดูงานปัจจุบัน ไม่ใช่ไว้แก้ master data

## Slide 17: Scrap Transaction

### คลิก
1. ไป `Inventory > Operations > Scrap`
2. เปิด `SP/00011`
3. ชี้ `Product`
4. ชี้ `Quantity`
5. ชี้ `Source Location`
6. ชี้ `Scrap Location`
7. ชี้ status

### สิ่งที่อธิบาย
- scrap มีผลกับ stock และอาจมีผลกับ cost
- ไม่ควรลด stock แบบ manual ถ้าของเสียจริง
- scrap เป็นเอกสาร traceable ที่ใช้ย้อนกลับได้

## Slide 18: Workcenter

### คลิก
1. ไป `Manufacturing > Configuration > Work Centers`
2. เปิด `Injection 5`
3. ชี้ `Manufacturing Type`
4. ชี้ `Capacity`
5. ชี้ `Cost per Hour`
6. ชี้ `Time Efficiency`
7. ชี้แท็บ `Compatibility Matrix`

### สิ่งที่อธิบาย
- workcenter เป็นตัวบอกกำลังการผลิตและต้นทุนเครื่อง
- ฝั่ง plastic และ pharma แยกกันได้จาก master ตรงนี้ด้วย
- compatibility matrix ใช้บอกว่าเครื่องนี้รับ mold อะไรได้

## Slide 19: Mold Master

### คลิก
1. เปิด mold ตัวอย่าง เช่น `แม่พิมพ์พลาสติกตัวบน W01`
2. ชี้ `Is Mold?`
3. ชี้ `Mold Cost / Hour`
4. ชี้ `Mold Life Limit`
5. ชี้ `Current Shots`
6. ชี้ `Cavities`
7. เข้าแท็บ `Mold Matrix`

### สิ่งที่อธิบาย
- mold เป็น master data ที่มีผลทั้ง execution และ costing
- `Current Shots` ใช้ติดตามอายุการใช้งาน
- `Mold Matrix` ใช้ map ว่า mold นี้ผลิตสินค้าอะไร และใช้กับเครื่องไหน
- ให้ย้ำว่าตอนนี้ระบบกันไม่ให้ mold เดียวถูกใช้ซ้ำผิด logic ใน parallel case แล้ว

## Slide 20: Transfer Plastic

### คลิก
1. ไป `Inventory > Operations > Transfers`
2. เปิด `GMP/TRPL/00006`
3. ชี้ `Operation Type`
4. ชี้ `Source Location`
5. ชี้ `Destination Location`
6. ชี้ lines และ qty

### สิ่งที่อธิบาย
- transfer plastic คือการเคลื่อนของกึ่งสำเร็จรูปหรือชิ้นส่วนฝั่งพลาสติก
- ต้องทำให้ผู้เรียนเห็นว่าพลาสติกกับ pharma ไม่ใช่ transfer เดียวกัน
- ใช้ย้ำเรื่อง location segregation ของโรงงาน

## Slide 21: Transfer Pharma

### คลิก
1. อยู่หน้า transfers หรือค้นหาใหม่
2. เปิด `GMP/TRPH/00001`
3. ชี้ `Operation Type`
4. ชี้ `Source Location`
5. ชี้ `Destination Location`
6. เปรียบเทียบกับ transfer plastic

### สิ่งที่อธิบาย
- transfer pharma ใช้คนละ operation type กับ plastic
- ถ้า route ถูก ระบบจะแยกเอกสารและ location ให้อัตโนมัติ
- จุดนี้สำคัญมากสำหรับ warehouse และ planner

## Slide 22: Invoice / Accounting Endpoint

### คลิก
1. ไป `Accounting > Customers > Invoices`
2. เปิด `INV-D/26/04/00001`
3. ชี้สถานะ `Posted`
4. ชี้ invoice lines
5. ชี้ `Journal Items`

### สิ่งที่อธิบาย
- manufacturing flow ที่โยงกับ sale ต้องจบถึง accounting ได้
- invoice เป็นปลายทางด้านขาย แต่ไม่ใช่ตัวเดียวที่ใช้ตรวจต้นทุน
- ให้ผู้เรียนเห็นว่าปลายทางของ flow ไม่ได้จบที่ delivery อย่างเดียว

## Slide 23: Closing Checklist

### สิ่งที่พูด
- ก่อนใช้งานจริงให้เช็ก 5 เรื่อง
- product / route ถูกไหม
- min/max หรือ sale trigger ถูกไหม
- BoM และ operation type ถูกไหม
- transfer แยก plastic / pharma ถูกไหม
- shopfloor, scrap, mold และ accounting trace ได้ไหม

### สิ่งที่ต้องทำ
- ถามห้องว่าแต่ละทีมจะกลับไปเช็กหน้าไหนก่อนเมื่อเริ่มใช้งานจริง

## 4. คำถามสะท้อนกลับที่ควรถามผู้เรียน

- ถ้าสินค้าขาด ระบบควรไป MO หรือ PO ดูจากอะไร
- ถ้าเป็น SO 0 บาท ทำไมยังต้องดู delivery
- ถ้าเป็น MTS แล้วไม่มี SO ระบบยิงเอกสารจากจุดไหน
- ถ้า mold life ใกล้เต็ม เราดูจาก field ไหน
- ถ้า transfer ไปผิดฝั่ง plastic/pharma ควรเริ่มเช็กที่ไหนก่อน
- ถ้า workorder ถูก cancel มันควรไปโผล่ใน shopfloor ไหม

## 5. ประโยคช่วยดึงห้องกลับมาเวลาหลุด focus

- “ตอนนี้ยังไม่ต้องจำทุก field ให้จำก่อนว่าหน้านี้มีหน้าที่อะไรใน flow”
- “ให้ยึดหลักว่าของขาดแล้วจะไป MO หรือ PO เพราะ route อะไร”
- “ถ้า trace ไม่ถูก ให้ย้อนกลับไป product, route, BoM ก่อน”
- “หน้างานดู Shopfloor, คนวางแผนดู MO, คนคลังดู Transfer, คนบัญชีดู Invoice และ Journal”
