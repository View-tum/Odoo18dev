# Odoo Walk-through ทีละหน้าจอ

เอกสารนี้ใช้สำหรับคนสอนเปิดตามใน Odoo ทีละหน้า โดยเรียงตามลำดับการสอน 3 ชั่วโมง

## ช่วง 1: Opening และภาพรวมระบบ

### หน้า 1: Dashboard
- เมนู: `Home`
- สิ่งที่ต้องชี้: แอปหลักที่เกี่ยวข้องกับ flow นี้
- แอปที่ควรเห็น: `Sales`, `Inventory`, `Manufacturing`, `Purchase`, `Accounting`, `Quality`
- ประโยคที่ใช้สอน: “flow วันนี้ไม่ได้อยู่ในแอปเดียว แต่โยงกันหลายแอป”

### หน้า 2: Manufacturing Overview
- เมนู: `Manufacturing`
- สิ่งที่ต้องชี้: menu สำหรับ `Operations`, `Products`, `Reporting`, `Configuration`
- ประโยคที่ใช้สอน: “ทีมผลิตต้องรู้ว่าจะเข้าเมนูจากตรงไหนเวลาไล่ปัญหา”

## ช่วง 2: Settings และ Master Data

### หน้า 3: Product ของ FG ตัวอย่าง
- เมนู: `Manufacturing > Products > Products`
- สินค้าที่เปิด: `FG-PSS-TH-01005`
- สิ่งที่ต้องชี้: `Routes`, `Manufacturing Type`
- ประโยคที่ใช้สอน: “ตัวนี้ไม่ได้วิ่งจาก SO แบบ MTO แต่ใช้ Min/Max”

### หน้า 4: Reordering Rule ของ FG
- เมนู: `Inventory > Configuration > Reordering Rules`
- ค้นหา: `FG-PSS-TH-01005`
- สิ่งที่ต้องชี้: `Location`, `Min`, `Max`, `Route`, `Trigger`
- ประโยคที่ใช้สอน: “จุดนี้เป็นตัวบอกว่า shortage จะไป MO หรือ PO”

### หน้า 5: BoM ของ FG
- เมนู: `Manufacturing > Products > Bills of Materials`
- เปิด: `FG-PSS-TH-01005`
- สิ่งที่ต้องชี้: `BoM Type`, `Operation Type`, component หลัก
- ประโยคที่ใช้สอน: “MO ตัวแม่ไม่ได้ทำทุกอย่างเอง แต่มันแตก demand ลง child layer”

### หน้า 6: Child structure ของ FG
- เมนู: BoM เดิม
- สิ่งที่ต้องชี้: `FG-PSS-TH-02001`, `FG-PSS-TH-03001`, 6 สี, `SM-*`, `SO-*`
- ประโยคที่ใช้สอน: “นี่คือจุดที่ Pharma กับ Plastic มาเจอกัน”

## ช่วง 3: Promotion / SO 0 บาท

### หน้า 7: Promotion Quote
- เมนู: `Sales > Quotations`
- เปิด: `S11563`
- สิ่งที่ต้องชี้: free line, price `0`, product line ที่ระบบเติมให้
- ประโยคที่ใช้สอน: “SO 0 บาท ไม่ได้แปลว่าไม่มี stock movement”

### หน้า 8: FOC Full Flow
- เมนู: `Sales > Orders`
- เปิด: `SOB-263069`
- สิ่งที่ต้องชี้: status ของ order, delivery, invoice smart buttons
- ประโยคที่ใช้สอน: “flow นี้ต้องไปจบที่เอกสารปลายทางครบ”

### หน้า 9: FOC Delivery
- เมนู: จาก smart button ของ `SOB-263069`
- เปิด: `GMP/OUT/02504`
- สิ่งที่ต้องชี้: source, destination, qty done
- ประโยคที่ใช้สอน: “ถึงจะ FOC ก็ยังต้องส่งของจริง”

### หน้า 10: FOC Invoice
- เมนู: จาก smart button ของ `SOB-263069`
- เปิด: `INV-D/26/03/00960`
- สิ่งที่ต้องชี้: invoice posted, line amount, accounting effect
- ประโยคที่ใช้สอน: “FOC ไม่ใช่ไม่เกิด accounting”

## ช่วง 4: SO -> MTO

### หน้า 11: SO แบบ MTO
- เมนู: `Sales > Orders`
- เปิด: `SOB-263070`
- สิ่งที่ต้องชี้: smart buttons, delivery, invoice, linked manufacturing docs
- ประโยคที่ใช้สอน: “ตัวนี้เป็น demand จาก sale ที่วิ่งต่อไป production”

### หน้า 12: MTO MO Chain
- เมนู: smart button ที่เกี่ยวกับ production จาก `SOB-263070`
- สิ่งที่ต้องชี้: child MO ที่ถูกสร้างตาม chain
- ประโยคที่ใช้สอน: “ผู้ใช้ไม่ควรไปเปิด MO ลูกเองถ้า setting ถูก”

## ช่วง 5: MTS / Min-Max

### หน้า 13: Replenishment Example
- เมนู: `Inventory > Configuration > Reordering Rules`
- เปิดหรือค้นหา product: `FG-PNC-TH-01001`
- สิ่งที่ต้องชี้: rule ที่ใช้เติม stock
- ประโยคที่ใช้สอน: “นี่คือตัวอย่างของ MTS ที่ไม่ต้องรอ SO”

### หน้า 14: MO จาก Replenishment
- เมนู: `Manufacturing > Operations > Manufacturing Orders`
- เปิด: `GMP/MOPH/00011`
- สิ่งที่ต้องชี้: origin, product, operation type, status
- ประโยคที่ใช้สอน: “เอกสารนี้มาจาก replenishment ไม่ใช่จาก sale”

## ช่วง 6: Shopfloor และ Scrap

### หน้า 15: Shopfloor Workorder
- เมนู: `Manufacturing > Operations > Work Orders`
- เปิด workorder ของ `GMP/MOPL/00014`
- สิ่งที่ต้องชี้: start, qty produced, workcenter, state
- ประโยคที่ใช้สอน: “จุดนี้คือหน้างานจริงของ operator”

### หน้า 16: Scrap
- เมนู: `Inventory > Operations > Scrap`
- เปิด: `SP/00011`
- สิ่งที่ต้องชี้: product, source location, scrap qty, status
- ประโยคที่ใช้สอน: “scrap มีผลต่อ stock และ cost ทันที”

## ช่วง 7: Mold Management

### หน้า 17: MO Plastic ตัวอย่าง
- เมนู: `Manufacturing > Operations > Manufacturing Orders`
- เปิด: `GMP/MOPL/00014`
- สิ่งที่ต้องชี้: linked workorders และ machine ที่ใช้จริง
- ประโยคที่ใช้สอน: “parallel workorder ตอนนี้ไม่กระจาย qty ไปตัว done/cancel แล้ว”

### หน้า 18: Mold Mapping
- เมนู: `Manufacturing` หรือเมนู custom ของ mold
- เปิด mold ที่ใช้กับ `SM-PLS-UP-01001`
- สิ่งที่ต้องชี้: product mapping, workcenter mapping, mold life
- ประโยคที่ใช้สอน: “mold ต้อง map ทั้ง product และ machine ถึงจะ auto ได้”

## ช่วง 8: Transfer, Inventory, Costing

### หน้า 19: Transfer Plastic / Pharma
- เมนู: `Inventory > Operations > Transfers`
- ค้นหาเอกสาร `Transfer Plastic` และ `Transfer Pharma`
- สิ่งที่ต้องชี้: operation type และ location ต้นทางปลายทาง
- ประโยคที่ใช้สอน: “แยกโรงงานดูจาก operation type ไม่ใช่ดูจากชื่อสินค้าอย่างเดียว”

### หน้า 20: Costing Review
- เมนู: เปิด MO ล่าสุดที่มี labor และ mold
- เอกสารที่ใช้: `GMP/MOPL/00014`
- สิ่งที่ต้องชี้: stock valuation, labor JE, mold JE
- ประโยคที่ใช้สอน: “actual cost ของเราดู raw, machine, labor, mold แยกกัน”

## ช่วง 9: Closing

### หน้า 21: Checklist Screen
- เมนู: กลับไป `Dashboard` หรือ `Manufacturing`
- สิ่งที่ต้องชี้: recap ว่าถ้า flow ไม่ไปต่อ ให้เช็ก `route`, `BoM`, `orderpoint`, `vendor`, `mold mapping`
- ประโยคที่ใช้สอน: “ก่อนแจ้งปัญหา ให้เช็ก 5 จุดนี้ก่อนเสมอ”
