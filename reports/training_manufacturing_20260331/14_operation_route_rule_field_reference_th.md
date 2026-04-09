# Field Reference: Operation Type, Route และ Rule

## วัตถุประสงค์
ใช้อธิบายหน้าจอ 3 หน้านี้ให้ผู้เรียนเข้าใจว่าตารางหรือ section ไหนใช้ทำอะไร และ field สำคัญแต่ละตัวมีผลกับ flow อย่างไร

---

## 1. Operation Type (`stock.picking.type`)

### หน้าที่ของ table
- เป็นแม่แบบเอกสาร
- กำหนดว่า document family นี้คือ Receipt, Delivery, Internal Transfer หรือ Manufacturing
- กำหนด sequence, default source/destination และ behavior ตอน validate

### ส่วน General
- `Operation Type`
  ชื่อเอกสาร เช่น Receipts, Transfer Plastic, Manufacturing Pharma
- `Type of Operation`
  ประเภทหลักของเอกสาร เช่น Receipt, Delivery, Internal Transfer, Manufacturing
- `Reference Sequence`
  sequence ที่ใช้สร้างเลขเอกสาร
- `Sequence Prefix`
  prefix ของเลขเอกสาร
- `Warehouse`
  operation type นี้อยู่ภายใต้ warehouse ไหน
- `Barcode`
  ใช้กับงาน barcode app
- `Allow Edit Effective Date`
  อนุญาตให้แก้ effective date ได้หรือไม่
- `Effective Date Offset (Days)`
  offset ของ effective date

### ส่วน Behavior / Control
- `Returns Type`
  ถ้าต้องคืนของ จะให้ใช้ operation type ไหน
- `Create Backorder?`
  เวลาทำไม่ครบ จะถามหรือสร้าง backorder อย่างไร
- `Analytic Costs`
  ใช้กับ analytic costing บาง flow
- `Require Invoice Reference/Date`
  บังคับให้กรอกข้อมูล invoice ก่อน validate บางประเภทเอกสาร
- `Show Delivery Address`
  แสดงช่องที่อยู่ปลายทางหรือไม่
- `Show Shipping Method`
  แสดงช่อง shipping method หรือไม่

### ส่วน Lots / Serial Numbers
- `Create New`
  อนุญาตให้สร้าง lot/serial ใหม่ได้
- `Use Existing ones`
  อนุญาตให้ใช้ lot/serial ที่มีอยู่แล้ว

### ส่วน Batch & Wave Transfers
- `Automatic Batches`
  ใช้สำหรับรวมหลาย picking เป็น batch

### ส่วน Locations
- `Source Location`
  location ต้นทาง default ของ operation type นี้
- `Destination Location`
  location ปลายทาง default ของ operation type นี้

### ใช้เมื่อไร
- ใช้ก่อนสร้าง rule
- ใช้เวลาจะออกแบบ document family ของ flow
- เช่นก่อนสร้าง route `Manufacture (Pharma)` ต้องมี operation type `Manufacturing Pharma` ก่อน

---

## 2. Route (`stock.route`)

### หน้าที่ของ table
- เป็น policy container
- เป็นตัวรวม rule หลายตัวให้อยู่ภายใต้ชื่อเดียว
- ใช้บอกว่าสินค้านี้จะ Buy, Manufacture, MTO, Transfer หรือใช้หลาย behavior ร่วมกัน

### ส่วน Header
- `Route`
  ชื่อ route
- `Sequence`
  ลำดับการแสดงผล / ความสำคัญ
- `Supplied Warehouse`
  route นี้ใช้จัดหาของให้ warehouse ไหน

### ส่วน Applicable On
- `Product Categories`
  route นี้เลือกใช้ได้ที่ product category
- `Products`
  route นี้เลือกใช้ได้ที่ product
- `Shipping Methods`
  route นี้ใช้กับ shipping method ได้
- `Warehouses`
  route นี้ใช้ระดับ warehouse ได้
- `Sales Order Lines`
  route นี้เลือกบน SO line ได้

### ส่วน Rules
ตารางนี้คือ one2many ไป `Rule`

คอลัมน์สำคัญ:
- `Action`
  action หลักของ rule ย่อย
- `Source Location`
  ต้นทางของแต่ละ rule
- `Destination Location`
  ปลายทางของแต่ละ rule

### ใช้เมื่อไร
- สร้างหลัง operation type
- สร้างก่อน rule
- เป็นตัวกลางให้ product หรือ orderpoint มาเลือกใช้

---

## 3. Rule (`stock.rule`)

### หน้าที่ของ table
- เป็น execution logic ตัวจริง
- ระบุว่าเมื่อเกิด demand แล้วระบบจะ “ทำอะไร”
- เชื่อม route เข้ากับ operation type และ location

### ส่วน Core Fields
- `Name`
  ชื่อ rule
- `Action`
  วิธีทำงาน เช่น Pull From, Push To, Pull & Push, Buy, Manufacture
- `Operation Type`
  อ้างเอกสารที่จะสร้าง
- `Source Location`
  ของจะถูกดึงจากที่ไหน
- `Destination Location`
  ของจะถูกส่งไปที่ไหน
- `Destination location origin from rule`
  ใช้กับ logic ปลายทางบางแบบ
- `Supply Method`
  วิธีจัดหาของ เช่น Take From Stock หรือ procurement method อื่น

### ส่วน Applicability
- `Route`
  rule นี้อยู่ใต้ route ไหน
- `Warehouse`
  ใช้กับ warehouse ไหน
- `Sequence`
  ลำดับของ rule

### ส่วน Propagation
- `Propagation of Procurement Group`
  จะ propagate procurement group ต่อไปหรือไม่
- `Cancel Next Move`
  ถ้ายกเลิก move นี้ จะยกเลิก move ถัดไปหรือไม่
- `Propagation of carrier`
  propagate carrier ต่อหรือไม่
- `Warehouse to Propagate`
  ส่ง warehouse context ต่อหรือไม่

### ส่วน Options
- `Partner Address`
  ใช้ใน flow ที่มี partner involvement
- `Lead Time`
  ระยะเวลานำของ rule นี้

### ใช้เมื่อไร
- สร้างหลัง route
- สร้างเมื่อรู้ source/destination จริงแล้ว
- สร้างเมื่อรู้แล้วว่าจะใช้ operation type ไหน

---

## 4. ความสัมพันธ์ระหว่าง 3 table
- `Route` 1 ตัว มี `Rule` ได้หลายตัว
- `Rule` 1 ตัว อยู่ใต้ `Route` 1 ตัว
- `Rule` 1 ตัว อ้าง `Operation Type` 1 ตัว
- `Operation Type` 1 ตัว ถูกใช้โดย `Rule` หลายตัวได้

---

## 5. ลำดับ setup ที่ควรใช้
1. `Warehouse`
2. `Locations`
3. `Operation Type`
4. `Route`
5. `Rule`
6. `Product / Product Category / Orderpoint`
7. `Putaway`

---

## 6. ตัวอย่างจาก UAT

### Manufacture (Pharma)
- `Route = Manufacture (Pharma)`
- `Rule 146`
- `Action = manufacture`
- `Operation Type = Manufacturing Pharma`
- `Source = GMP/Stock/คลังลอย`
- `Destination = GMP/Stock`

### Auto Transfer Semi (Plastic)
- `Route = Auto Transfer Semi (Plastic)`
- `Rule 145`
- `Action = pull`
- `Operation Type = Transfer Plastic`
- `Source = GMP/Stock/Semi`
- `Destination = GMP/Stock/คลังลอย`

### Buy
- `Route = Buy`
- `Rule 7`
- `Action = buy`
- `Operation Type = Receipts`
- `Destination = GMP/Stock`
