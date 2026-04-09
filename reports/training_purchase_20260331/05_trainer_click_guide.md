# Purchase Training: Trainer Click Guide

เอกสารนี้ใช้สำหรับผู้สอนเท่านั้น ให้เปิดคู่กับ [purchase_training_uat_detailed_20260331.pptx](./purchase_training_uat_detailed_20260331.pptx) และระบบ `UAT`

## 1. เตรียมก่อนเริ่มสอน

1. เปิดฐาน `uat`
2. เปิด PowerPoint และเปิด speaker script ไว้ข้าง ๆ
3. เปิดหน้า Home ของ Odoo
4. ตรวจว่าเมนู `Purchase`, `Inventory`, `Accounting` มองเห็นครบ
5. ถ้าจะสลับหน้าเร็ว ให้เตรียม tab หรือ bookmark ของเอกสารตัวอย่างเหล่านี้

- `PR00004` PR draft สำหรับ RM
- `PR00006` PR approved สำหรับ RM
- `P00017` PO สำหรับ RM
- `GMP/IN/00034` Receipt สำหรับ RM
- `SP/00001` Scrap สำหรับ RM
- `PR00007` PR สำหรับ Asset
- `GMP/IN/00035` Receipt สำหรับ Asset
- `PR00008` PR สำหรับ Consumable
- `GMP/IN/00036` Receipt สำหรับ Consumable
- `P00019` PO สำหรับ Service
- `SA/2026/0001` Service Acceptance
- `Draft Bill` จาก `P00019`

## 2. โครงเวลา 3 ชั่วโมง

### 09:00-09:20 Opening + Master Data
- Slide 1-5
- เป้าหมายคือให้ผู้เรียนเข้าใจภาพรวมก่อนลง flow จริง

### 09:20-10:05 Flow 1: RM + Scrap
- Slide 6-10
- เป้าหมายคือเห็น PR -> PO -> Receipt -> Lot -> Scrap

### 10:05-10:35 Flow 2: Asset
- Slide 11-13
- เป้าหมายคือเห็น PR -> Receipt เข้า location พิเศษ -> Bill

### 10:35-11:00 Flow 3: Consumable
- Slide 14-15
- เป้าหมายคือเข้าใจว่า receipt ได้ แต่ valuation ไม่เก็บแบบ stockable

### 11:00-11:30 Flow 4: Service
- Slide 16-17
- เป้าหมายคือเข้าใจ service acceptance ก่อน bill

### 11:30-12:00 Accounting + Q&A
- Slide 18-19
- เป้าหมายคือให้ทุกคน trace ปลายทางบัญชีได้

## 3. Click-by-Click ต่อสไลด์

## Slide 1: Opening

### สิ่งที่พูด
- วันนี้จะสอนงานจัดซื้อแบบ End-to-End
- เราจะไม่สอนแค่เปิด PO แต่จะเห็นจนถึง Receipt และ Bill
- ตัวอย่างทั้งหมดอิงจากฐาน `UAT` จริง

### สิ่งที่ต้องทำ
- ยังไม่ต้องคลิกในระบบ

## Slide 2: Agenda

### สิ่งที่พูด
- วันนี้มี 4 flow หลัก
- แต่ละช่วงจะมีทั้งมุมใช้งานและมุมบัญชี
- ช่วงท้ายจะเก็บคำถามและสรุป checklist

### สิ่งที่ต้องทำ
- ยังไม่ต้องคลิกในระบบ

## Slide 3: Home Dashboard

### คลิก
1. อยู่หน้า Home
2. ใช้เมาส์ชี้ที่ `Purchase`
3. ใช้เมาส์ชี้ที่ `Inventory`
4. ใช้เมาส์ชี้ที่ `Accounting`

### สิ่งที่อธิบาย
- `Purchase` คือจุดเริ่มต้นของ PR, RFQ, PO
- `Inventory` คือจุดรับของ, lot, scrap
- `Accounting` คือปลายทางของ vendor bill และ journal

### สิ่งที่ต้องย้ำ
- งานจัดซื้อของบริษัทไม่ได้จบที่ PO
- ถ้าไม่เชื่อม 3 แอปนี้ ผู้ใช้จะมอง flow ขาด

## Slide 4: Product Category: Raw Materials

### คลิก
1. เข้า `Inventory`
2. ไป `Configuration > Product Categories`
3. เปิด category `All / RM / สารเคมี`

### สิ่งที่อธิบาย
- ดู `Costing Method`
- ดู `Inventory Valuation`
- อธิบายว่าทำไม category นี้มีผลกับ accounting ตอนรับของ

### สิ่งที่ต้องย้ำ
- ถ้า category ผิด การรับของจะลงบัญชีผิด
- RM ที่ใช้ lot และมีผลต้นทุน ต้องดู category ก่อน product

## Slide 5: Vendor Master Setup

### คลิก
1. เข้า `Purchase`
2. ไป `Orders > Vendors`
3. เปิด `Home Product Center Plc.`
4. ชี้แท็บ `Purchase`
5. ชี้แท็บ `Accounting`

### สิ่งที่อธิบาย
- Vendor profile
- Payment terms
- ข้อมูลบัญชีธนาคาร
- ข้อมูลเหล่านี้ไปมีผลตอน PO และ Bill

### สิ่งที่ต้องย้ำ
- Vendor master ไม่ครบ ทำให้ปลายทางจ่ายเงินสะดุด
- เวลาฝ่ายจัดซื้อบอกว่าเปิด PO ได้ แต่บัญชีบอกจ่ายไม่ได้ สาเหตุมักอยู่หน้านี้

## Slide 6: Create PR

### คลิก
1. เข้า `Purchase`
2. ไป `My Requisitions`
3. เปิด `PR00004`
4. ชี้ปุ่ม `New`
5. ชี้ line สินค้า

### สิ่งที่อธิบาย
- PR นี้เป็น draft
- มีสินค้า, จำนวน, UoM, Analytic Distribution, Unit Cost
- อธิบายว่าผู้ใช้หน้างานเริ่มตรงนี้ ไม่ใช่เริ่มที่ PO

### สิ่งที่ต้องย้ำ
- `Analytic Distribution` ต้องครบ 100%
- ถ้า line ไม่มี analytic ระบบจะไม่ยอมให้ใช้ flow ต่อ

## Slide 7: Approve PR & Create RFQ

### คลิก
1. ยังอยู่ใน `Purchase > My Requisitions`
2. เปิด `PR00006`
3. ชี้ status `Approved`
4. ชี้ปุ่ม `Create RFQ`

### สิ่งที่อธิบาย
- เมื่อ PR ผ่าน approval แล้ว ฝั่งจัดซื้อจึงสร้าง RFQ ได้
- ปุ่ม `Create RFQ` คือจุดเปลี่ยนจากคำขอภายในไปเป็นเอกสารจัดซื้อ

### สิ่งที่ต้องย้ำ
- ถ้า PR ยังไม่ approve จะไม่ควรไปขั้น RFQ
- ผู้เรียนต้องแยกบทบาท requester กับ purchaser ให้ออก

## Slide 8: Confirm PO & Receipt

### คลิก
1. เข้า `Purchase > Orders`
2. เปิด `P00017`
3. ชี้สถานะ PO
4. ชี้ Smart Button `Receipt`
5. ชี้บรรทัดสินค้าและจำนวน `Received`

### สิ่งที่อธิบาย
- นี่คือเอกสาร PO หลัง confirm/approve แล้ว
- จากหน้า PO จะเห็นว่า receipt ถูกสร้างตามมา
- เชื่อมกับ PR/RFQ ได้ทาง origin และ smart button

### สิ่งที่ต้องย้ำ
- ถ้ายังไม่มี receipt ให้เช็กว่า PO ถูก confirm จริงหรือยัง
- PO คือสัญญาสั่งซื้อ ส่วน receipt คือการรับของจริง

## Slide 9: Detailed Operations & Lot

### คลิก
1. เข้า `Inventory > Operations > Receipts`
2. เปิด `GMP/IN/00034`
3. ชี้ `Traceability Report`
4. ชี้ column `Lot/Serial #`

### สิ่งที่อธิบาย
- RM ตัวอย่างนี้ใช้ lot `TRN-RM-LOT-01`
- lot ทำให้ trace ย้อนกลับได้ว่า receipt นี้มาจาก PO ไหน
- ใช้ lot เพื่อคุม traceability ระหว่างจัดซื้อและการใช้งานในโรงงาน

### สิ่งที่ต้องย้ำ
- ถ้าไม่มี lot สินค้ากลุ่มนี้จะ trace ย้อนยาก
- ผู้เรียนมักจะถามว่าใส่ lot ตอนไหน ให้ตอบว่าใส่ตอนรับของ

## Slide 10: Scrap Warehouse Operation

### คลิก
1. เข้า `Inventory > Operations > Scrap`
2. เปิด `SP/00001`
3. ชี้สินค้า
4. ชี้ lot
5. ชี้ source location และ scrap location

### สิ่งที่อธิบาย
- ของเสียต้องออกจาก stock ให้ตรงกับสภาพจริง
- scrap นี้อ้าง lot เดิมจาก receipt ของ RM

### สิ่งที่ต้องย้ำ
- scrap ไม่ใช่แค่เอกสารโกดัง แต่มีผลกับยอดคงเหลือ
- ถ้าสอนคนคลัง ให้เน้นว่า scrap ต้องอิง lot ให้ถูก

## Slide 11: Asset PR & Analytic Account

### คลิก
1. เข้า `Purchase > My Requisitions`
2. เปิด `PR00007`
3. ชี้ line สินค้า asset
4. ชี้ `Analytic Distribution`

### สิ่งที่อธิบาย
- asset PR ต้องรู้ว่าใครเป็นผู้ใช้หรือเจ้าของต้นทุน
- analytic account ใช้ช่วย trace ต้นทุนตามแผนก

### สิ่งที่ต้องย้ำ
- asset ไม่ใช่ของใช้สิ้นเปลือง ต้องดู category และการบันทึกปลายทาง

## Slide 12: Asset Destination Location

### คลิก
1. เข้า `Inventory > Operations > Receipts`
2. เปิด `GMP/IN/00035`
3. ชี้ `Destination Location`
4. ชี้ค่า `GMP/Stock/Training Asset`

### สิ่งที่อธิบาย
- asset receipt ถูกส่งไป location แยกจาก stock ปกติ
- ช่วยให้แยกของใช้ระยะยาวออกจากวัสดุทั่วไป

### สิ่งที่ต้องย้ำ
- ถ้ารับของ asset เข้า location ผิด จะตรวจนับและ trace ยาก
- หน้านี้เป็นตัวอย่าง location training ที่ใช้สอนใน UAT

## Slide 13: Vendor Bill & Asset Automation

### คลิก
1. เข้า `Purchase > Orders > Purchase Orders`
2. เปิด bill จาก `P00018`
3. ชี้ invoice line
4. ชี้ข้อมูลคู่ค้าและ bill date

### สิ่งที่อธิบาย
- นี่คือ vendor bill ฝั่ง asset
- อธิบายความต่างระหว่างการรับของกับการตั้งเจ้าหนี้
- ถ้า category และ account ถูก ปลายทางบัญชีจะรับต่อได้ถูก

### สิ่งที่ต้องย้ำ
- ผู้เรียนมักคิดว่ารับของแล้วจบ ต้องย้ำว่า bill ยังเป็นอีก step

## Slide 14: Consumables PR

### คลิก
1. เข้า `Purchase > My Requisitions`
2. เปิด `PR00008`
3. ชี้สินค้า consumable
4. ชี้ analytic distribution

### สิ่งที่อธิบาย
- consumable ยังต้องมี PR และ analytic เหมือนกัน
- ต่างจาก asset ที่ปลายทางบัญชีและ valuation logic

## Slide 15: Consumable Receipt ($0 Value)

### คลิก
1. เข้า `Inventory > Operations > Receipts`
2. เปิด `GMP/IN/00036`
3. ชี้สถานะ done
4. ชี้ line สินค้า

### สิ่งที่อธิบาย
- receipt เกิดจริง
- แต่ logic ทางบัญชีถือว่า consumable ไม่เก็บมูลค่า stock แบบสินค้าคงเหลือ

### สิ่งที่ต้องย้ำ
- ของยังรับเข้าเพื่อ control ปริมาณได้
- แต่ valuation ไม่เหมือน RM ที่ลง stock value

## Slide 16: Service Project/Labor PO

### คลิก
1. เข้า `Purchase > Orders > Purchase Orders`
2. เปิด `P00019`
3. ชี้สินค้า service
4. ชี้สถานะและ line จำนวน

### สิ่งที่อธิบาย
- service ไม่มีของรับเข้าคลังแบบ stock item
- แต่ยังต้องผ่าน process รับงานให้ครบก่อนวาง bill

### สิ่งที่ต้องย้ำ
- ผู้เรียนชอบถามว่าทำไม service ยังมี step เพิ่ม ให้โยงไป slide ถัดไป

## Slide 17: Service Entry / Service Acceptance

### คลิก
1. เปิด `SA/2026/0001`
2. ชี้ purchase order อ้างอิง
3. ชี้ accepted quantity
4. ชี้สถานะ done

### สิ่งที่อธิบาย
- service acceptance คือการยืนยันว่าได้รับงานแล้ว
- ก่อน acceptance ระบบไม่ควรเปิด bill สำหรับ service

### สิ่งที่ต้องย้ำ
- receipt ของ service ไม่ได้อยู่ใน inventory receipt ปกติ
- เอกสารนี้คือจุดควบคุมงานบริการ

## Slide 18: Vendor Bill Journal Items

### คลิก
1. เข้า `Accounting > Vendors > Bills`
2. เปิด draft bill จาก `P00019`
3. กดแท็บ `Journal Items`
4. ไล่ดู debit / credit และ tax

### สิ่งที่อธิบาย
- ตรงนี้คือปลายทางบัญชีที่ต้องตรวจ
- ผู้เรียนต้องดูให้เป็นว่า line ไหนเป็นค่าใช้จ่าย line ไหนเป็นภาษี line ไหนเป็นเจ้าหนี้

### สิ่งที่ต้องย้ำ
- ถ้าถามเรื่องบัญชี ให้พากลับมาดู journal items เสมอ

## Slide 19: Closing Checklist

### คลิก
1. กลับมาที่ slide
2. สรุปโดยไม่ต้องสลับหน้า Odoo ถ้าห้องถามน้อย
3. ถ้ามีเวลา ให้ย้อนเปิด `P00017` และ `P00019` อีกครั้งเพื่อเชื่อม flow

### สิ่งที่อธิบาย
- RM ต้องดู lot และ scrap
- asset ต้องดู location และ bill
- consumable ต้องดู receipt และ logic $0 value
- service ต้องดู acceptance ก่อน bill

## 4. จุดที่ควรถามกลับผู้เรียนระหว่างสอน

- ถ้า PR ยังไม่ approve จะสร้าง RFQ ได้ไหม
- ถ้ารับ RM แล้วไม่ใส่ lot จะเกิดผลอะไร
- asset ต่างจาก consumable ตรงไหน
- ทำไม service ต้องมี acceptance
- ถ้าจะตรวจบัญชี ต้องเปิดหน้าไหน

## 5. ถ้าห้องเริ่มหลุด focus ให้ใช้ประโยคนี้

- “จำง่าย ๆ ว่า Purchase เริ่มจากความต้องการ, Inventory ยืนยันการรับจริง, Accounting คือผลสุดท้าย”
- “ถ้าเอกสารต้นน้ำผิด ปลายน้ำจะผิดตาม”
- “ทุก flow ต้องตอบได้ว่า ตอนนี้ของอยู่ไหน และค่าใช้จ่ายไปลงที่ไหน”
