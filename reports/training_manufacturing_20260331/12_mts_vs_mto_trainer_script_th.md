# Trainer Script ภาษาไทย: MTS vs MTO ใน UAT

## เปิดเรื่อง
วันนี้เราจะเทียบ MTS กับ MTO แบบเห็นเป็นรูปธรรม โดยใช้สินค้าจริงจาก UAT คนละตัว เพื่อให้ทีมเห็นว่าความต่างไม่ได้อยู่แค่ชื่อ route แต่ต่างกันตั้งแต่ตัวจุดชนวนของ demand จนถึงเอกสารที่ระบบสร้าง

ตัวอย่างที่ใช้:
- MTS = FG-PNC-TH-01001
- MTO = FG-MTK-IL-01001

---

## Slide 1: หัวข้อ
ให้บอกผู้เรียนก่อนว่าเราจะใช้กรอบเดียวกันทั้งสองฝั่ง:
Replenishment -> Route -> Rule -> Operation Type -> Putaway

จุดประสงค์คือให้ตอบได้ว่า:
- ทำไมสินค้าตัวหนึ่งเติม stock
- ทำไมอีกตัวหนึ่งรอ demand จาก sales

## Slide 2: ทำไมเลือกสองตัวนี้
อธิบายว่า:
- FG-PNC-TH-01001 มี orderpoint 175 จริง และไม่มี MTO route
- FG-MTK-IL-01001 มี MTO route จริง และไม่มี orderpoint

เพราะฉะนั้นมันเป็นตัวอย่างสะอาดสำหรับอธิบายความต่าง

## Slide 3: MTS
พูดตามลำดับนี้
1. ตัวเริ่มคือ orderpoint 175 ที่ GMP/Stock
2. เมื่อ forecast ขาด ระบบเริ่ม procurement อัตโนมัติ
3. Product route ของมันคือ Manufacture (Pharma)
4. ดังนั้น rule ที่ทำงานจริงคือ rule 146
5. เอกสารที่คนเห็นคือ Manufacturing Pharma

ประโยคที่ควรย้ำ:
MTS คิดจาก stock ก่อน ถ้าของในคลังไม่พอ ระบบจึงค่อยสร้างงานมาเติม

## Slide 4: MTO
พูดตามลำดับนี้
1. ตัวเริ่มไม่ใช่ orderpoint แต่เป็น demand จาก SO
2. Product มี MTO route อยู่จริง
3. MTO route ดึง demand ย้อนกลับผ่าน rule 5
4. ถ้าต้องผลิต ระบบจะต่อไป rule 146
5. ถ้าต้องดึง semi ก็จะต่อไป rule 144

ประโยคที่ควรย้ำ:
MTO ไม่ได้เติม stock ล่วงหน้า แต่ค่อยสร้าง supply เมื่อมี order เข้ามา

## Slide 5: ความต่างที่ต้องให้ทีมจำ
ให้สรุปด้วยคำง่าย ๆ
- MTS = stock-first
- MTO = order-first
- MTS เป้าหมายคือเติม stock
- MTO เป้าหมายคือส่งมอบตามออเดอร์

## Slide 6: Rule และ Operation Type
ใช้สไลด์นี้ย้ำว่า route อย่างเดียวไม่พอ
ต้องดู rule และ operation type ด้วย

ให้พูดว่า:
- ถ้าเป็น MTS ตัวอย่างนี้ คนหน้างานจะเห็น Manufacturing Pharma เป็นหลัก
- ถ้าเป็น MTO คนหน้างานจะเห็น Pick, Transfer Pharma, Manufacturing Pharma ตามชั้นของ chain

## Slide 7: สรุปปิด
ปิดด้วยประโยคนี้:
ถ้าถามว่าของขาดแล้วระบบจะทำอะไร อย่าตอบจากความเคยชิน ให้ไล่ถาม 5 เรื่องนี้เสมอ คือ trigger มาจากไหน, route อะไร, rule ไหนทำงาน, operation type อะไรจะถูกสร้าง, และ putaway จะพาไปเก็บที่ไหน

---

## Q&A ที่คนเรียนมักถาม
### ถาม: สินค้ามีทั้ง orderpoint และ MTO route ได้ไหม
ตอบ: ได้ แต่จะทำให้ logic ซ้อนกัน ต้องดูว่า demand จริงเริ่มจาก orderpoint หรือ sales flow และต้องดู route ที่ level product กับ orderpoint พร้อมกัน

### ถาม: min/max = 0 แปลว่าไม่เติมของใช่ไหม
ตอบ: ไม่ใช่ ในฐานนี้ 0/0 ถูกใช้แบบเติม shortage กลับมาที่ 0

### ถาม: MTO แล้วถ้ามีของใน stock อยู่จะใช้ stock ได้ไหม
ตอบ: ขึ้นกับ rule และ procure_method ที่วิ่งจริง บาง rule ใน UAT เป็น `mts_else_mto` จึงยังมีพฤติกรรมใช้ stock ก่อนในบาง leg

### ถาม: Putaway มีผลกับ MTO ไหม
ตอบ: มีในส่วนของ material หรือ semi ที่เข้าคลังระหว่างทาง แต่ไม่ได้เป็นตัวเริ่ม MTO demand
