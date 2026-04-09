# Trainer Script ภาษาไทย: Replenishment, Route, Rule, Operation Type และ Putaway ใน UAT

## วัตถุประสงค์
ใช้ script นี้เมื่อผู้สอนต้องการอธิบายว่า demand 1 ตัวในระบบ Odoo ของเราไหลจาก trigger ไปจนถึง document และ location ย่อยอย่างไร โดยอิงจาก config จริงในฐาน `uat`

---

## เปิดเรื่อง
วันนี้เราจะอธิบายคำ 5 คำที่คนใช้ระบบสับสนกันบ่อย คือ Replenishment, Route, Rule, Operation Type และ Putaway โดยจะใช้ข้อมูลจริงจากฐาน uat ไม่ใช่ตัวอย่างสมมติ เป้าหมายคือให้ทุกคนตอบได้ว่าถ้าของขาด ระบบจะไปผลิต ไปซื้อ หรือไปโอน เพราะอะไร

---

## สไลด์ 1
ให้บอกผู้เรียนว่าหัวข้อนี้เป็น appendix สำคัญของ training manufacturing เพราะเวลา flow ไม่ไปต่อ ปัญหามักอยู่ที่ 5 คำนี้ ไม่ใช่ที่หน้าจอปลายทาง

## สไลด์ 2
อธิบายความแตกต่างของ 5 คำให้ชัด
- Replenishment คือ trigger
- Route คือ policy
- Rule คือ logic ย่อยจริง
- Operation Type คือเอกสารจริง
- Putaway คือการจัดเก็บหลังงานเสร็จ

เน้นว่าคำทั้ง 5 ไม่ได้ซ้อนกันแบบคำพ้อง แต่ทำงานคนละชั้น

## สไลด์ 3
ใช้ FG-PNC-TH-01001 และ FG-PSS-TH-01005 เป็นตัวอย่าง
- FG-PNC-TH-01001 มี orderpoint 175 ที่ GMP/Stock
- FG-PSS-TH-01005 มี orderpoint 249 ที่ GMP/Stock และ 308 ที่ M-WH/Stock

จุดที่ต้องอธิบาย:
- trigger auto หมายถึงระบบยิง procurement ให้เอง
- min/max 0/0 ในฐานนี้หมายถึงเติม shortage กลับมาที่ 0
- orderpoint เป็นตัวเริ่ม แต่ยังไม่ใช่ตัวกำหนด document สุดท้ายทั้งหมด

## สไลด์ 4
อธิบาย Route ที่มีอยู่จริงใน UAT
- Buy
- Manufacture
- Manufacture (Pharma)
- Manufacture (Plastic)
- Auto Transfer Semi (Pharma)
- Auto Transfer Semi (Plastic)
- Replenish on Order (MTO)

ให้ย้ำว่า Route คือ policy ของสินค้า ไม่ใช่เอกสาร

## สไลด์ 5
อธิบาย Rule ด้วยตัวอย่างจริง
- Rule 7 ใช้กับ Buy
- Rule 146 ใช้กับ Manufacturing Pharma
- Rule 147 ใช้กับ Manufacturing Plastic
- Rule 144/145 ใช้กับ Transfer Semi

จุดสำคัญที่ต้องพูด:
- source location
- destination location
- action
- operation type

ให้พูดว่าเวลาระบบไปผิดทาง ต้องลงมาดูที่ Rule เป็นหลัก

## สไลด์ 6
ย้ำว่า Operation Type คือสิ่งที่คนใช้งานเห็นเป็น document จริง
เช่น
- Receipts
- Transfer Pharma
- Transfer Plastic
- Manufacturing Pharma
- Manufacturing Plastic

ให้สอนทีมดู operation type เพื่อแยกโรงงาน ไม่ใช่เดาจากชื่อสินค้าอย่างเดียว

## สไลด์ 7
อธิบาย Putaway ว่าเป็น layer หลังสุด
ใช้ตัวอย่างจริง:
- RM/พลาสติก ไป PL01
- SFG/พลาสติก ไป Semi/พลาสติก
- SFG/น้ำยา ไป Semi/โรงงานยา

ประโยคสำคัญ:
Putaway ไม่ได้สร้าง PO ไม่ได้สร้าง MO แต่เป็นตัวจัดเก็บเมื่อของไปถึง location ใหญ่แล้ว

## สไลด์ 8
อธิบาย FG-PNC-TH-01001
ลำดับที่ต้องพูด:
1. orderpoint 175 ยิง demand
2. product route เป็น Manufacture (Pharma)
3. ระบบจึงไป chain ฝั่งผลิตยา

จุดที่ต้องย้ำ:
orderpoint เป็นตัวเริ่ม แต่ route บนสินค้าเป็นคนกำหนดฝั่งผลิต

## สไลด์ 9
อธิบาย FG-PSS-TH-01005
- orderpoint 249 route = Manufacture
- product route = Manufacture (Pharma)
- top BOM มี FG-PSS-TH-02001 x16, PK-CAR-PS-01003 x1 และเทปกาว x1

ให้ผู้เรียนเห็นว่า chain นี้มีทั้ง:
- ผลิต
- ซื้อ
- และลึกลงไปยังแยก Plastic กับ Pharma

## สไลด์ 10
ใช้ชั้นลึกของ FG-PSS-TH-01005 เพื่ออธิบายของจริง
- FG-PSS-TH-02001 แตกเป็น FG-PSS-TH-03001 และ packaging buy
- FG-PSS-TH-03001 แตกเป็น 6 สี
- ตัวอย่างสี FG-PSS-TH-04001 ใช้ทั้ง semi plastic, joiner plastic, filter, และ solution pharma

ตรงนี้ต้องชี้ให้ชัดว่า:
- Plastic branch ใช้ route 61/63
- Pharma branch ใช้ route 60/62
- Buy branch ใช้ route 5

## สไลด์ 11
ปิดด้วยสรุป 5 คำอีกครั้ง
- Replenishment = ตัวเริ่มเรื่อง
- Route = บอกทาง
- Rule = บอกวิธีทำจริง
- Operation Type = หน้าตาเอกสาร
- Putaway = บอกว่าพอไปถึงแล้วเก็บตรงไหน

ประโยคปิด:
ถ้าระบบไม่สร้างเอกสารที่เราคาด อย่าเริ่มจากโทษหน้าจอปลายทาง ให้ไล่จาก trigger ไป route ไป rule แล้วค่อยดู operation type และ putaway

---

## คำถามที่คนเรียนมักถาม
### ถาม: Replenishment กับ Orderpoint เหมือนกันไหม
ตอบ: ไม่เหมือนกัน Orderpoint เป็นหนึ่งใน trigger ของ replenishment แต่ replenishment กว้างกว่า เพราะ MTO demand ก็เป็น replenishment ได้

### ถาม: ทำไมสินค้าบางตัวมีหลาย route
ตอบ: เพราะ route คนละตัวรับผิดชอบคนละ behavior เช่น สินค้าหนึ่งตัวอาจต้องมีทั้ง transfer semi และ manufacture

### ถาม: ทำไม route Manufacture ที่ orderpoint กับ route Manufacture (Pharma) บนสินค้าไม่เหมือนกัน
ตอบ: เพราะ orderpoint บอกเชิง procurement ว่าต้องผลิต แต่ route เฉพาะบน product/child chain ใช้แยก logic โรงงานและ operation type

### ถาม: Putaway มีผลกับ procurement ไหม
ตอบ: ไม่มี Putaway มีผลตอนของมาถึงปลายทางแล้วเท่านั้น

### ถาม: ถ้าของขาด ระบบจะ Buy หรือ Manufacture ดูตรงไหน
ตอบ: ดูที่ route และ rule ที่วิ่งจริงของสินค้านั้น รวมทั้ง route บน orderpoint ถ้ามี
