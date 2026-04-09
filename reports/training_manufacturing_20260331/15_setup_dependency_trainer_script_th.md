# Trainer Script ภาษาไทย: Setup Dependency ของ Warehouse -> Location -> Operation Type -> Route -> Rule -> Product/Orderpoint -> Putaway

## วัตถุประสงค์
ใช้ script นี้อธิบาย 3 หน้าหลักคือ `Operation Type`, `Route`, `Rule` และเชื่อมให้คนเรียนเห็นทั้ง dependency chain ว่าควรสร้างอะไรก่อนหลัง และแต่ละ table มีหน้าที่อะไร

---

## เปิดเรื่อง
วันนี้หัวข้อนี้เราจะไม่ได้ดูแค่ว่าหน้าจอแต่ละหน้าใส่อะไรได้บ้าง แต่จะดูว่าระบบคิดเป็นทอด ๆ อย่างไร เพราะเวลาระบบไม่สร้างเอกสารหรือวิ่งผิดทาง ปัญหาจริงมักอยู่ที่ setup chain ไม่ครบ ไม่ได้อยู่ที่ปุ่มปลายทางอย่างเดียว

ให้ทุกคนจำคำง่าย ๆ ก่อน 3 คำ
- Operation Type คือ เอกสาร
- Route คือ นโยบาย
- Rule คือ วิธีทำจริง

แล้วทั้ง 3 ตัวนี้ต้องวางอยู่บนโครงสร้าง `Warehouse` กับ `Location` ก่อน และท้ายที่สุดต้องถูกนำไปใช้ที่ `Product` หรือ `Orderpoint`

---

## Part 1: Dependency Diagram
ตอนเปิดสไลด์ diagram ให้พูดตามนี้

ลำดับการตั้งค่าที่ถูกต้องคือ เริ่มจาก Warehouse ก่อน เพราะ warehouse เป็นกรอบใหญ่ของระบบคลัง จากนั้นต้องสร้าง Location ให้ครบก่อน เพราะทั้ง operation type และ rule ต้องอ้าง source กับ destination จริง ถ้ายังไม่มี location ก็ยังตั้ง flow ไม่ได้

พอมี location แล้ว ค่อยสร้าง Operation Type เพราะ operation type คือแม่แบบ document ที่ user จะเห็นจริง เช่น Receipt, Transfer หรือ MO และ rule จะต้องอ้าง operation type เสมอ

หลังจากนั้นค่อยสร้าง Route เพื่อบอก policy ว่าสินค้าจะซื้อ ผลิต หรือโอน แล้วจึงสร้าง Rule ที่เป็นคำสั่งจริงอยู่ใต้ route โดยระบุ action, source, destination และ operation type

เมื่อ route และ rule พร้อมแล้ว จึงค่อยนำ route ไปใช้จริงบน product, product category, SO line หรือ orderpoint และสุดท้ายเมื่อของถึง location ปลายทางแล้ว Putaway จะเข้ามาทำหน้าที่จัดเก็บลงตำแหน่งย่อย

สรุปแบบสั้นที่สุด:
- Warehouse / Location = โครงสร้างคลัง
- Operation Type = หน้าตาเอกสาร
- Route = นโยบาย
- Rule = logic ที่ทำงานจริง
- Product / Orderpoint = จุดเริ่มใช้งานจริง
- Putaway = การจัดเก็บปลายทาง

---

## Part 2: อธิบายหน้า Operation Type
เวลาเปิดหน้าจอนี้ ให้พูดว่า

หน้านี้คือ table `stock.picking.type` หรือ Operation Type หน้าที่ของมันคือกำหนดว่าเอกสารประเภทนี้หน้าตาเป็นอย่างไร ใช้ sequence อะไร ใช้ source location กับ destination location default ไหน และมี behavior ตอน validate อย่างไร

อธิบาย field ทีละส่วน

### General
- Operation Type คือชื่อ document family เช่น Receipts หรือ Manufacturing Pharma
- Type of Operation คือชนิดหลัก ว่าเป็น receipt, delivery, internal หรือ manufacturing
- Reference Sequence กับ Sequence Prefix ใช้กำหนดเลขเอกสาร
- Warehouse บอกว่า operation type นี้อยู่ภายใต้คลังไหน
- Barcode ใช้กับ app barcode
- Allow Edit Effective Date กับ Effective Date Offset เป็น field ที่คุมวันที่มีผลของเอกสาร

### Behavior / Control
- Returns Type ใช้กำหนด flow คืนของ
- Create Backorder ใช้กำหนดว่าถ้าทำไม่ครบจะถามหรือแตก backorder อย่างไร
- Require Invoice Reference/Date ใช้กับบาง receipt flow ที่อยากบังคับ invoice reference
- Show Delivery Address กับ Show Shipping Method เป็นเรื่อง field บน document

### Lots / Serials
- Create New คืออนุญาตให้สร้าง lot ใหม่
- Use Existing ones คืออนุญาตให้เลือก lot เดิม

### Locations
- Source Location และ Destination Location คือ default locations ของเอกสาร family นี้

ให้ย้ำกับคนเรียนว่า
Operation Type ไม่ได้ตัดสินใจว่าจะซื้อหรือผลิต แต่มันตัดสินใจว่า “ถ้ามีเอกสารเกิดขึ้น เอกสารนั้นเป็นประเภทอะไร”

---

## Part 3: อธิบายหน้า Route
เวลาเปิดหน้า Route ให้พูดว่า

หน้านี้คือ table `stock.route` Route เป็น policy container หรือกล่องนโยบาย มันไม่ได้สั่งงานเองทันที แต่เป็นตัวรวม rule หลายตัวเข้าด้วยกันแล้วให้ product หรือ orderpoint มาเลือกใช้

อธิบาย field หลัก

### Header
- Route คือชื่อ route
- Sequence คือลำดับ
- Supplied Warehouse คือ warehouse ที่ route นี้ใช้จัดหาของให้

### Applicable On
- Product Categories หมายถึง route นี้เลือกใช้ได้จาก category
- Products หมายถึง route นี้เลือกใช้ได้ตรงบนสินค้า
- Warehouses หมายถึง route นี้ผูกระดับ warehouse ได้
- Sales Order Lines หมายถึง route นี้เลือกที่ SO line ได้

### Rules Table
ตารางด้านล่างคือ rule ย่อยที่อยู่ใน route นี้
ถ้ายังไม่มี rule, route จะเป็นแค่นโยบายเปล่า ๆ ที่ยังทำงานไม่ได้

ให้ย้ำว่า
Route ตอบคำถามว่า สินค้านี้ควรไปทางไหน แต่ Rule จะเป็นตัวตอบว่า “ไปยังไง”

---

## Part 4: อธิบายหน้า Rule
เวลาเปิดหน้า Rule ให้พูดว่า

หน้านี้คือหัวใจของ procurement flow จริง ๆ เพราะ Rule คือ execution logic ตัวจริง ถ้าระบบวิ่งผิด document หรือผิด location ส่วนใหญ่ต้องย้อนลงมาดูที่ Rule

อธิบาย field สำคัญ

### Core
- Name คือชื่อ rule
- Action คือวิธีทำงาน เช่น Pull, Buy, Manufacture
- Operation Type คือ document family ที่จะถูกสร้าง
- Source Location คือของจะถูกดึงจากที่ไหน
- Destination Location คือของจะถูกส่งไปที่ไหน
- Supply Method คือจะใช้ stock เดิมหรือจะ propagate procurement ต่อ

### Applicability
- Route บอกว่า rule นี้อยู่ใต้ route ไหน
- Warehouse บอกบริบทของคลัง
- Sequence ใช้เรียงลำดับ rule

### Propagation
- Propagation of Procurement Group ใช้กับการเชื่อม demand chain
- Cancel Next Move ใช้กำหนดผลกระทบเวลายกเลิก
- Propagation of carrier และ Warehouse to Propagate ใช้ส่ง context ต่อ

### Options
- Partner Address ใช้กับบาง flow ที่มี partner
- Lead Time คือเวลานำของ rule นี้

ให้ย้ำกับคนเรียนว่า
Rule คือจุดที่เอา Route กับ Operation Type มาเชื่อมเข้าด้วยกัน และเติม Source/Destination ลงไปให้กลายเป็น flow ที่ทำงานจริงได้

---

## Part 5: ลำดับการสร้างที่ถูกต้อง
ตอนนี้ให้กลับไปที่ diagram แล้วพูดสรุป

1. สร้าง Warehouse ก่อน
2. สร้าง Locations ให้ครบ
3. สร้าง Operation Types
4. สร้าง Routes
5. สร้าง Rules
6. Assign Route ให้ Product / Category / SO Line / Orderpoint
7. ค่อยสร้าง Putaway Rules
8. ทดสอบ E2E

ให้ย้ำว่าถ้าทำสลับลำดับ เช่นรีบสร้าง orderpoint ก่อน route/rule พร้อม ระบบจะมี trigger แต่ไม่รู้จะไปทางไหน

---

## Part 6: ตัวอย่างจริงจาก UAT
ให้ยก 3 ตัวอย่างนี้

### ตัวอย่างที่ 1: Buy
- Route = Buy
- Rule 7
- Action = buy
- Operation Type = Receipts
- Destination = GMP/Stock

### ตัวอย่างที่ 2: Manufacture (Pharma)
- Route = Manufacture (Pharma)
- Rule 146
- Action = manufacture
- Operation Type = Manufacturing Pharma
- Source = GMP/Stock/คลังลอย
- Destination = GMP/Stock

### ตัวอย่างที่ 3: Auto Transfer Semi (Plastic)
- Route = Auto Transfer Semi (Plastic)
- Rule 145
- Action = pull
- Operation Type = Transfer Plastic
- Source = GMP/Stock/Semi
- Destination = GMP/Stock/คลังลอย

ให้ชี้ให้เห็นว่าในทั้ง 3 ตัวอย่างนี้ pattern เดิมเสมอคือ
Route เป็น policy
Rule เป็น execution
Operation Type เป็นเอกสาร

---

## Part 7: ปิดท้าย
ให้ปิดด้วยประโยคนี้

ถ้าจำได้แค่ประโยคเดียวจากหัวข้อนี้ ให้จำว่า
Warehouse กับ Location ทำให้ระบบรู้ว่าของอยู่ที่ไหน
Operation Type ทำให้ระบบรู้ว่าจะสร้างเอกสารอะไร
Route ทำให้ระบบรู้ว่าควรไปทางไหน
Rule ทำให้ระบบรู้ว่าจะทำอย่างไรจริง
Product กับ Orderpoint คือจุดที่ flow ถูกเอาไปใช้
และ Putaway เป็นตัวจัดเก็บปลายทางหลังของถึงคลังแล้ว

ถ้าคนเรียนเข้าใจ 6 ชั้นนี้ เวลาดูปัญหาเรื่อง replenishment, transfer, MO หรือ receipt จะ trace ได้ถูกจุดมากขึ้น
