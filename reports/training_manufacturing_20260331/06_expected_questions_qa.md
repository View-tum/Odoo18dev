# Manufacturing Training: Expected Questions and Trainer Answers

เอกสารนี้ใช้สำหรับผู้สอน เพื่อเตรียมตอบคำถามที่ผู้เข้าอบรมมักถามระหว่าง training manufacturing โดยอิง flow จริงในระบบและเอกสารตัวอย่างที่ใช้ใน deck

ใช้คู่กับไฟล์ต่อไปนี้

- [manufacturing_training_uat_detailed_plain_20260331.pptx](./manufacturing_training_uat_detailed_plain_20260331.pptx)
- [manufacturing_training_uat_detailed_plain_speaker_20260331.txt](./manufacturing_training_uat_detailed_plain_speaker_20260331.txt)
- [04_odoo_walkthrough.md](./04_odoo_walkthrough.md)
- [05_trainer_click_guide.md](./05_trainer_click_guide.md)

## 1. วิธีใช้เอกสารนี้

เวลาเจอคำถามจากห้อง ให้ตอบเป็น 3 ชั้น

1. `คำตอบสั้น`
2. `ขยายความ`
3. `พาเปิดหน้าจอจริง`

อย่าตอบเป็น technical ลึกเกินไปถ้าผู้ฟังเป็น user ให้พากลับมาที่ flow และเอกสารจริงก่อนเสมอ

## 2. คำถามภาพรวมของระบบ Manufacturing

### คำถาม: ทำไม training manu ต้องดูหลาย app ไม่ใช่แค่ Manufacturing
`คำตอบสั้น`
- เพราะ flow manufacturing วิ่งข้ามหลาย app

`ขยายความ`
- sale อาจเป็นต้นทางของ demand
- inventory เป็นจุดดู stock, transfer, scrap และ min/max
- purchase จะเกี่ยวเมื่อของขาดแล้ว route ไป Buy
- accounting เป็นปลายทางของ invoice และผลทางบัญชี

`หน้าจอที่ควรพาเปิด`
- Home Dashboard
- Manufacturing Overview

### คำถาม: เอกสารหลักใน flow นี้มีอะไรบ้าง
`คำตอบสั้น`
- Product, BoM, Reordering Rule, SO, MO, Work Order, Transfer, Scrap, Invoice

`ขยายความ`
- Product กับ BoM เป็น master data
- SO หรือ Min/Max เป็นตัว trigger demand
- MO กับ Work Order เป็น execution
- Transfer กับ Scrap เป็น inventory execution
- Invoice และ Journal เป็นปลายทางทางบัญชี

`หน้าจอที่ควรพาเปิด`
- Manufacturing Overview
- ตัวอย่าง `SOB-263070`
- ตัวอย่าง `GMP/MOPH/00011`

## 3. คำถามเรื่อง Product, Route และ Min/Max

### คำถาม: shortage แล้วจะไป MO หรือ PO ดูจากอะไร
`คำตอบสั้น`
- ดู route และ reordering rule

`ขยายความ`
- ถ้า route เป็น Manufacture ระบบจะไป MO
- ถ้า route เป็น Buy ระบบจะไป PO/RFQ
- ถ้าเป็น Min/Max จะมี trigger จาก reordering rule
- ถ้าเป็น MTO จาก sale ก็จะมี procurement chain จาก SO

`หน้าจอที่ควรพาเปิด`
- Product ของ `FG-PSS-TH-01005`
- Reordering Rule ของ `FG-PSS-TH-01005`

### คำถาม: Product route กับ Category route ต่างกันยังไง
`คำตอบสั้น`
- Product route คือสิ่งที่ผูกกับสินค้าตัวนั้นโดยตรง ส่วน category route คือสิ่งที่ inherited มา

`ขยายความ`
- ถ้าผู้ใช้ดูผิดจุดจะเข้าใจผิดว่าทำไมระบบสร้างเอกสารแบบนั้น
- เวลาตรวจปัญหาให้ดูทั้งสองชั้น

`หน้าจอที่ควรพาเปิด`
- Product inventory tab

### คำถาม: ทำไม FG-PSS-TH-01005 ไม่เตะจาก SO แบบ MTO
`คำตอบสั้น`
- เพราะตัวอย่างนี้ตั้งให้วิ่งจาก Min/Max ไม่ใช่ MTO ตรง

`ขยายความ`
- ตัวนี้ใช้สอนความต่างของ MTO กับ MTS
- ต้องแยกให้ได้ว่าบางตัวเริ่มจาก sale แต่บางตัวเติม stock จาก replenishment

`หน้าจอที่ควรพาเปิด`
- Product `FG-PSS-TH-01005`
- Reordering Rule ของ `FG-PSS-TH-01005`

### คำถาม: ถ้าสต็อกพอ ระบบจะสร้าง MO ไหม
`คำตอบสั้น`
- ไม่เสมอ ขึ้นกับ shortage จริง

`ขยายความ`
- ถ้าของยังพอ ระบบอาจแค่ reserve ของเดิม
- procurement จะเกิดเมื่อ forecast หรือ min/max บอกว่าต้องเติม

`หน้าจอที่ควรพาเปิด`
- Reordering Rule
- Product smart buttons เช่น On Hand / Forecasted

## 4. คำถามเรื่อง BoM และ Child Structure

### คำถาม: ทำไม MO ตัวแม่ไม่ผลิตทุกอย่างเอง
`คำตอบสั้น`
- เพราะ BoM แตก requirement ลง child ได้

`ขยายความ`
- FG บางตัวมีหลายชั้นของ semi และ solution
- ระบบจะแตก requirement ตาม BoM และ route ของแต่ละชั้น

`หน้าจอที่ควรพาเปิด`
- BoM ของ `FG-PSS-TH-01005`

### คำถาม: ถ้า component บางตัวเป็น Plastic บางตัวเป็น Pharma ระบบแยกยังไง
`คำตอบสั้น`
- แยกจาก route, operation type และ manufacturing type

`ขยายความ`
- ชิ้นส่วน plastic จะวิ่งไป Manufacturing Plastic
- งานยาและ FG ยา จะวิ่งไป Manufacturing Pharma
- transfer ก็จะแยกตาม operation type ด้วย

`หน้าจอที่ควรพาเปิด`
- BoM
- Transfer Plastic
- Transfer Pharma

### คำถาม: ถ้า BoM ผิด จะเกิดอะไรขึ้น
`คำตอบสั้น`
- ระบบแตก requirement ผิดทั้ง chain

`ขยายความ`
- อาจไปเรียกของผิด
- อาจไปผิดโรง
- อาจทำให้ MO ลูกไม่ถูกสร้างหรือสร้างผิด

`หน้าจอที่ควรพาเปิด`
- BoM form
- MO components tab

## 5. คำถามเรื่อง Promotion / FOC

### คำถาม: SO 0 บาท หรือ FOC ทำไมยังต้องดู stock movement
`คำตอบสั้น`
- เพราะของยังถูกส่งจริง

`ขยายความ`
- free item ไม่ได้แปลว่าไม่มี inventory effect
- ต้อง trace delivery และ invoice ให้ครบ

`หน้าจอที่ควรพาเปิด`
- `S11563`
- `SOB-263069`
- delivery ของ `SOB-263069`

### คำถาม: FOC มีผลบัญชีไหม
`คำตอบสั้น`
- มี ต้องดู invoice และ cost mapping ต่อ

`ขยายความ`
- ยอดขายอาจเป็นศูนย์หรือมีของฟรี
- แต่ stock movement และ costing ยังเกิดได้

`หน้าจอที่ควรพาเปิด`
- `INV-D/26/04/00001` หรือ invoice ตัวอย่างใน deck

## 6. คำถามเรื่อง SO -> MTO

### คำถาม: ถ้าเป็น MTO ผู้ใช้ต้องเปิด MO ลูกเองไหม
`คำตอบสั้น`
- ไม่ควร ถ้า setting ถูก

`ขยายความ`
- demand ควรถูกแตกจาก sale ลง production chain อัตโนมัติ
- ถ้าต้องเปิดเองทุกครั้ง มักแปลว่ามี setting ที่ยังไม่ถูก

`หน้าจอที่ควรพาเปิด`
- `SOB-263070`
- MO chain ที่เกี่ยวข้อง

### คำถาม: จะรู้ได้ยังไงว่าเอกสารนี้วิ่งมาจาก sale
`คำตอบสั้น`
- ดู origin, smart buttons และเอกสารเชื่อมกัน

`ขยายความ`
- sales order, delivery, MO, picking มักมี reference ผูกกัน
- ต้องฝึกผู้ใช้ให้ใช้ smart buttons และ origin field

`หน้าจอที่ควรพาเปิด`
- `SOB-263070`
- MO ที่เกี่ยวข้อง

## 7. คำถามเรื่อง MTS / Replenishment

### คำถาม: MTS ต่างจาก MTO ยังไง
`คำตอบสั้น`
- MTO เริ่มจาก sale ส่วน MTS เริ่มจาก stock policy / Min-Max

`ขยายความ`
- MTO มี sale เป็น demand ต้นทาง
- MTS ใช้เติม stock ตามระดับที่ต้องถือ
- ในระบบจริงสองแนวนี้อาจหน้าตาคล้ายกันตอนเป็น MO แต่จุดกำเนิดไม่เหมือนกัน

`หน้าจอที่ควรพาเปิด`
- `SOB-263070`
- `GMP/MOPH/00011`

### คำถาม: ของต่ำกว่า min แล้วระบบจะทำอะไร
`คำตอบสั้น`
- สร้าง procurement ตาม route

`ขยายความ`
- ถ้า route เป็น manufacture ก็ไป MO
- ถ้า route เป็น buy ก็ไป PO
- ผู้สอนควรย้ำว่าตัว trigger อยู่ที่ reordering rule

`หน้าจอที่ควรพาเปิด`
- Reordering Rule
- `GMP/MOPH/00011`

## 8. คำถามเรื่อง Shopfloor และ Work Order

### คำถาม: ทำไมต้องดู Work Order ไม่ดูแค่ MO
`คำตอบสั้น`
- เพราะงานจริงเกิดที่ Work Order

`ขยายความ`
- MO เป็นเอกสารแม่
- execution จริง เช่น machine, time, qty produced, mold อยู่ที่ Work Order

`หน้าจอที่ควรพาเปิด`
- Work Order ของ `GMP/MOPL/00014`

### คำถาม: GMP Shop Floor ต่างจาก Work Orders ยังไง
`คำตอบสั้น`
- GMP Shop Floor เป็น dashboard/card view ส่วน Work Orders เป็นเอกสารรายละเอียด

`ขยายความ`
- shop floor ใช้ดูงานเร็วและเข้า console
- work order ใช้ดู field ละเอียดและ trace execution จริง

`หน้าจอที่ควรพาเปิด`
- GMP Shop Floor Dashboard
- Work Order form

### คำถาม: ถ้า workcenter เป็น done หรือ cancel แล้วทำไมไม่ควรกระจาย qty ไปอีก
`คำตอบสั้น`
- เพราะมันไม่ใช่งาน active แล้ว

`ขยายความ`
- ถ้ากระจาย qty ไป done/cancel จะทำให้ execution เพี้ยน
- logic ล่าสุดของระบบถูกปรับให้ active workorder เท่านั้นที่รับ qty เพิ่ม

`หน้าจอที่ควรพาเปิด`
- Work Order example
- GMP Shop Floor

### คำถาม: งาน cancel ควรโชว์ใน shopfloor ไหม
`คำตอบสั้น`
- ไม่ควร

`ขยายความ`
- หน้างานไม่ควรเห็น card ที่ไม่ต้องทำต่อ
- ลดความเสี่ยงการกรอก qty ผิดเอกสาร

`หน้าจอที่ควรพาเปิด`
- GMP Shop Floor Dashboard

## 9. คำถามเรื่อง Scrap

### คำถาม: Scrap ใช้เมื่อไร
`คำตอบสั้น`
- ใช้เมื่อต้องตัดของออกจากระบบเพราะเสียหรือใช้ไม่ได้

`ขยายความ`
- scrap กระทบ stock และอาจมีผลต่อ cost
- ไม่ควรแก้ stock แบบตรง ๆ ถ้าเป็นของเสียจริง

`หน้าจอที่ควรพาเปิด`
- `SP/00011`

### คำถาม: Scrap ต่างจาก reject ยังไง
`คำตอบสั้น`
- reject เป็นแนวคิดในหน้างาน ส่วน scrap เป็นเอกสาร stock movement

`ขยายความ`
- หน้างานอาจพูดว่า reject
- แต่ในระบบ inventory ต้องมี scrap document ถ้าตัดของออกจริง

`หน้าจอที่ควรพาเปิด`
- Scrap form
- Work Order / Shopfloor screen

## 10. คำถามเรื่อง Mold

### คำถาม: Mold master มีไว้ทำอะไร
`คำตอบสั้น`
- ใช้คุมการเลือก mold, machine compatibility, mold life และ mold cost

`ขยายความ`
- mold ไม่ใช่แค่ข้อมูลประกอบ
- มีผลต่อ execution และ actual cost

`หน้าจอที่ควรพาเปิด`
- Mold master ตัวอย่าง

### คำถาม: ระบบรู้ได้ยังไงว่า mold ไหนใช้กับเครื่องไหน
`คำตอบสั้น`
- ดูจาก mold/workcenter matrix

`ขยายความ`
- compatibility matrix ระบุคู่ที่ใช้ได้
- ถ้า matrix ผิด ระบบอาจเลือกเครื่องหรือ mold ผิด

`หน้าจอที่ควรพาเปิด`
- Workcenter `Injection 5`
- Mold matrix ของ `แม่พิมพ์พลาสติกตัวบน W01`

### คำถาม: Mold life ดูจากอะไร
`คำตอบสั้น`
- ดู `Current Shots` เทียบกับ `Mold Life Limit`

`ขยายความ`
- ใช้ติดตามอายุการใช้งานและแผนบำรุงรักษา
- ผู้เรียนควรเข้าใจว่าค่านี้ขยับตาม output จริงของงาน

`หน้าจอที่ควรพาเปิด`
- Mold master

### คำถาม: ถ้ามี parallel workorder ระบบจะใช้ mold ซ้ำกันไหม
`คำตอบสั้น`
- ตอนนี้ logic ถูกกันไว้แล้วไม่ให้ซ้ำผิด business rule

`ขยายความ`
- active workorder เท่านั้นที่ควรถือ mold
- cancel/done ไม่ควรดึง qty หรือใช้งาน mold ต่อ

`หน้าจอที่ควรพาเปิด`
- MO / Work Order ของ `GMP/MOPL/00014`

## 11. คำถามเรื่อง Transfer Plastic / Pharma

### คำถาม: Plastic กับ Pharma แยก transfer ยังไง
`คำตอบสั้น`
- แยกด้วย operation type และ route

`ขยายความ`
- ถ้า master data ถูก ระบบจะสร้าง transfer คนละฝั่งให้เอง
- จุดนี้สำคัญมากเวลา semi วิ่งข้ามโรง

`หน้าจอที่ควรพาเปิด`
- `GMP/TRPL/00006`
- `GMP/TRPH/00001`

### คำถาม: ถ้า transfer ไปผิดฝั่งควรเช็กอะไร
`คำตอบสั้น`
- เช็ก product route, manufacturing type, BoM operation type และ operation type ของเอกสาร

`ขยายความ`
- อย่าเริ่มแก้ที่ transfer ทันที
- ต้องย้อนกลับไปดูต้นทางของ logic ก่อน

`หน้าจอที่ควรพาเปิด`
- Product
- BoM
- Transfer

## 12. คำถามเรื่อง Costing และ Accounting

### คำถาม: Production flow จบที่ไหน
`คำตอบสั้น`
- จบเชิงปฏิบัติการที่ stock/document และจบเชิงบัญชีที่ invoice / journal / valuation

`ขยายความ`
- ผู้ใช้หลายคนมักคิดว่าจบที่ MO done
- แต่ในมุมธุรกิจจริงยังต้องดู transfer, delivery และผลทางบัญชีต่อ

`หน้าจอที่ควรพาเปิด`
- MO
- Transfer
- Invoice

### คำถาม: Costing ต้องดูอะไรบ้าง
`คำตอบสั้น`
- raw, machine, labor, mold และปลายทางใน valuation/journal

`ขยายความ`
- training นี้ไม่ได้สอนบัญชีเชิงลึก แต่ต้องให้ผู้เรียนรู้ว่าต้นทุนไม่ได้มาจาก raw อย่างเดียว
- machine, labor และ mold มีบทบาทด้วย โดยเฉพาะฝั่ง plastic

`หน้าจอที่ควรพาเปิด`
- Work Order
- Mold
- Invoice / Journal Items

### คำถาม: FOC ไม่มีรายได้ แล้วทำไมยังต้องสนใจ cost
`คำตอบสั้น`
- เพราะของยังถูกผลิตและส่งจริง

`ขยายความ`
- ถึงยอดขายเป็นศูนย์หรือเป็นของแถม ระบบยังมี inventory movement และ cost impact

`หน้าจอที่ควรพาเปิด`
- `SOB-263069`
- invoice ตัวอย่าง

## 13. คำถามเชิง policy ที่ห้องอาจถาม

### คำถาม: Manual MO กับ auto MO ต่างกันยังไง
`คำตอบสั้น`
- manual MO คือผู้ใช้เปิดเอง ส่วน auto MO เกิดจาก sale หรือ replenishment ตาม setting

`ขยายความ`
- จุดสำคัญของ training คือให้ผู้เรียนรู้ว่าเมื่อไรควรให้ระบบยิงเอง
- และเมื่อไรต้องเปิดงานเองจริง ๆ

`หน้าจอที่ควรพาเปิด`
- MO จาก replenishment
- MO ที่ trace จาก sale

### คำถาม: ทุกของที่ขาดควรไปผลิตหมดไหม
`คำตอบสั้น`
- ไม่เสมอ ขึ้นกับ route ว่า Buy หรือ Manufacture

`ขยายความ`
- บาง item เป็น RM หรือ packaging ที่ควรซื้อ
- บาง item เป็น semi หรือ FG ที่ควรผลิต

`หน้าจอที่ควรพาเปิด`
- Product route
- Reordering Rule

## 14. คำถามที่ควรถามกลับเพื่อเช็กความเข้าใจ

- ถ้าผมให้ชื่อสินค้า 1 ตัว คุณจะเริ่มดูจากหน้าไหนก่อน
- จะรู้ได้ยังไงว่าสินค้าตัวนี้ควรไป MTO หรือ MTS
- จะรู้ได้ยังไงว่าขาดแล้วควรไป MO หรือ PO
- จะ trace จาก SO ไปหา MO และ delivery ยังไง
- ถ้า workorder ไม่ควรทำต่อแล้ว มันควรไปแสดงใน shopfloor ไหม
- ถ้าฝั่ง plastic กับ pharma ปนกัน คุณจะตรวจจุดไหนก่อน

## 15. คำตอบสรุปแบบเร็วสำหรับผู้สอน

- Product + Route + BoM คือฐานของระบบ auto
- MTO เริ่มจาก sale, MTS เริ่มจาก min/max
- MO เป็นเอกสารแม่ แต่งานจริงอยู่ที่ Work Order
- Scrap ต้องใช้เอกสาร ไม่ควรแก้ stock ตรง ๆ
- Mold มีผลทั้ง execution และ cost
- Plastic กับ Pharma ต้องแยก transfer
- ถ้าระบบวิ่งผิด ให้ย้อนกลับไปดู master data ก่อน

## 16. เอกสารที่ผู้สอนควรจำให้ได้ก่อนขึ้นสอน

- `FG-PSS-TH-01005`
- `S11563`
- `SOB-263069`
- `SOB-263070`
- `GMP/MOPH/00011`
- `GMP/MOPH/00001`
- `GMP/MOPL/00014`
- `SP/00011`
- `GMP/TRPL/00006`
- `GMP/TRPH/00001`
- `INV-D/26/04/00001`

## 17. ข้อควรระวังเวลาตอบคำถาม

- ถ้าผู้เรียนถามลึกเรื่องบัญชี ให้ตอบในระดับ flow ก่อน แล้วค่อยให้ accounting key user ต่อรายละเอียด
- ถ้าถามเชิง technical เกินไป ให้พากลับมาที่ business meaning ของเอกสาร
- ถ้าห้องเริ่มงง ให้ย้อนกลับไปอธิบาย Product, Route, BoM ใหม่
- อย่าปล่อยให้ห้องติดกับเลขเอกสารมากเกินไป ให้ย้ำว่าต้องเข้าใจ flow ก่อน
