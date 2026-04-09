# Manufacturing Training Agenda

หัวข้อหลักของ session นี้คือ `Setting -> Flow -> Shopfloor -> Mold -> Transfer -> Costing`

## ระยะเวลา
- รวม `3 ชั่วโมง`

## วัตถุประสงค์
- ให้ทีมเข้าใจภาพรวม Manufacturing ของบริษัท
- ให้ทีมเห็น logic `Plastic` กับ `Pharma`
- ให้ทีมเข้าใจ `Promotion`, `MTO`, `MTS / Min-Max`
- ให้ทีมใช้งาน `Shopfloor`, `Scrap`, `Mold`, `Transfer` ได้
- ให้ทีมรู้จุดตรวจของ `PO`, `Inventory`, `Accounting`

## ตารางเวลาแบบละเอียด

### 00:00-00:15 Opening และภาพรวมระบบ
- เนื้อหาที่สอน
  - เป้าหมายของระบบ Manufacturing
  - ภาพรวมโรงงาน `Plastic` และ `Pharma`
  - Demand 1 ตัว จะไหลไปเอกสารอะไรบ้าง
  - ภาพรวมเอกสาร `SO -> MO -> Transfer -> Delivery -> Accounting`
- สิ่งที่จะ demo
  - หน้า `Home`
  - หน้า `Manufacturing`
- ผลลัพธ์ที่ต้องได้
  - ผู้เข้าอบรมเห็นภาพรวมระบบก่อนลงรายละเอียด
  - ผู้เข้าอบรมเข้าใจว่า flow ของบริษัทไม่ได้อยู่ในแอปเดียว

### 00:15-00:35 Settings และ Master Data
- เนื้อหาที่สอน
  - Product routes
  - `manufacturing_type`
  - BoM และ BoM picking type
  - Workcenter และ Operation Type
  - Reordering Rule (`Min/Max`)
  - Vendor สำหรับสินค้าที่ `Buy`
  - Mold mapping
- สิ่งที่จะ demo
  - Product `FG-PSS-TH-01005`
  - BoM ของ `FG-PSS-TH-01005`
  - Reordering Rule ของ `FG-PSS-TH-01005`
- ผลลัพธ์ที่ต้องได้
  - ผู้เข้าอบรมรู้ว่า setting ไหนผิดแล้วระบบจะไม่ auto
  - ผู้เข้าอบรมรู้ว่าต้องเช็กอะไรเมื่อ flow ไม่ไปต่อ

### 00:35-01:00 Flow 1: Promotion / SO 0 บาท
- เนื้อหาที่สอน
  - เปิด quotation / SO แบบส่งเสริมการขาย
  - free item และ FOC logic
  - เอกสาร downstream ที่ต้องเกิด
  - วิธีเช็กใน UI ว่า free line และ accounting ถูกหรือไม่
- สิ่งที่จะ demo
  - `S11563`
  - `SOB-263069`
  - `GMP/OUT/02504`
  - `INV-D/26/03/00960`
- ผลลัพธ์ที่ต้องได้
  - ผู้เข้าอบรมเข้าใจว่า SO 0 บาท ยังมี stock movement และ cost
  - ผู้เข้าอบรม trace เอกสาร FOC ได้

### 01:00-01:25 Flow 2: SO -> MTO
- เนื้อหาที่สอน
  - เปิด SO แบบขายปกติ
  - procurement จาก SO
  - child MO และ smart button chain
  - จุดที่แยก `make_to_order` กับ `make_to_stock`
- สิ่งที่จะ demo
  - `SOB-263070`
  - เอกสาร MO ที่เกี่ยวข้อง
  - `GMP/PICK/03572`
  - `INV-D/26/03/00961`
- ผลลัพธ์ที่ต้องได้
  - ผู้เข้าอบรมเข้าใจ logic ของ demand จาก sale
  - ผู้เข้าอบรมดูได้ว่า case ไหนควรสร้าง MO จาก SO

### 01:25-01:45 Flow 3: MTS / Min-Max
- เนื้อหาที่สอน
  - orderpoint และ reordering rule
  - กรณีของพอ
  - กรณี stock ต่ำกว่า min หรือ forecast ติดลบ
  - route `Manufacture` กับ `Buy`
  - PO จะเกิดเมื่อไร
- สิ่งที่จะ demo
  - `FG-PNC-TH-01001`
  - `GMP/MOPH/00011`
  - `FG-PSS-TH-01005` เป็นตัวอย่างของ `ORDERPOINT_ONLY`
- ผลลัพธ์ที่ต้องได้
  - ผู้เข้าอบรมแยก MTS กับ MTO ได้
  - ผู้เข้าอบรมตอบได้ว่าของขาดแล้วควรไป MO หรือ PO เพราะอะไร

### 01:45-02:10 Shopfloor, Workorder, Scrap
- เนื้อหาที่สอน
  - start, pause, done
  - good qty และ reject qty
  - scrap
  - จุดที่ operator ต้องกรอก
  - parallel logic ที่เกี่ยวกับ `done/cancel`
- สิ่งที่จะ demo
  - workorder ของ `GMP/MOPL/00014`
  - scrap `SP/00011`
- ผลลัพธ์ที่ต้องได้
  - ผู้เข้าอบรมเข้าใจว่าหน้างานต้องกรอกอะไร
  - ผู้เข้าอบรมเห็นผลของ scrap ต่อ stock และ cost

### 02:10-02:30 Mold Management
- เนื้อหาที่สอน
  - mold map กับ product และ workcenter
  - auto assign mold
  - mold life
  - guard ของ parallel workorder
- สิ่งที่จะ demo
  - `GMP/MOPL/00014`
  - mold ที่ map กับ `SM-PLS-UP-01001`
  - machine mapping ตาม matrix ที่ตั้งไว้
- ผลลัพธ์ที่ต้องได้
  - ผู้เข้าอบรมรู้ว่าต้องเช็กอะไรเมื่อ mold ไม่ขึ้น
  - ผู้เข้าอบรมเข้าใจว่า mold life เพิ่มจาก output จริง

### 02:30-02:50 Transfer, Inventory, Costing
- เนื้อหาที่สอน
  - `Transfer Plastic` กับ `Transfer Pharma`
  - semi ข้ามโรง
  - raw, machine, labor, mold cost
  - std cost กับ actual cost
- สิ่งที่จะ demo
  - transfer ที่เกี่ยวข้องกับ flow จริง
  - MO ที่มี labor และ mold posting
- ผลลัพธ์ที่ต้องได้
  - ผู้เข้าอบรม trace การโอนของข้ามโรงได้
  - ผู้เข้าอบรมเข้าใจว่าต้องดู cost จากเอกสารไหน

### 02:50-03:00 Q&A และ Checklist
- เนื้อหาที่สอน
  - recap จุดสำคัญ
  - checklist ก่อนใช้งานจริง
  - คำถามที่พบบ่อย
  - next step หลัง training
- สิ่งที่จะ demo
  - handout และ checklist สรุป
- ผลลัพธ์ที่ต้องได้
  - ผู้เข้าอบรมรู้จุดเช็กหลักก่อนแจ้งปัญหา
  - key user พร้อมไป UAT ต่อได้

## สิ่งที่ต้องเตรียมก่อนสอน
- `DB 11` เปิดพร้อม login
- เปิด Developer Mode
- เตรียมเมนู Manufacturing, Inventory, Purchase, Accounting
- เตรียมตัวอย่างเอกสารตาม `README.md`
- โปรเจคเตอร์และ user test account
