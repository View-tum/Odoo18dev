# Slide ภาษาไทย: Replenishment, Route, Rule, Operation Type และ Putaway ใน UAT

## สไลด์ 1: หัวข้อ
- Replenishment, Route, Rule, Operation Type และ Putaway ใน UAT
- อธิบายจาก config และ master data จริงของฐาน uat
- ใช้เป็น appendix เพิ่มในชุด training manufacturing หลัก

## สไลด์ 2: ภาพรวมคำ 5 คำในระบบ
- Replenishment = ตัวเริ่ม demand
- Route = policy ว่าจะ Buy, Manufacture, Transfer หรือ MTO
- Rule = คำสั่งย่อยจริงที่ระบุ source, destination, action และ operation type
- Operation Type = เอกสารจริงที่ผู้ใช้เห็น
- Putaway = กฎจัดเก็บหลัง stock ถึงปลายทาง

## สไลด์ 3: Replenishment ใน uat ทำงานอย่างไร
- FG-PNC-TH-01001 มี orderpoint id 175 ที่ GMP/Stock, trigger auto, min 0, max 0
- FG-PSS-TH-01005 มี orderpoint id 249 ที่ GMP/Stock และ id 308 ที่ M-WH/Stock
- min/max แบบ 0/0 ในฐานนี้ใช้เติม shortage กลับขึ้นมาที่ 0
- Replenishment จึงเป็น trigger ของ procurement ไม่ใช่เอกสารปลายทาง

## สไลด์ 4: Route จริงที่ใช้ใน uat
- Buy (id 5)
- Manufacture (id 6)
- Manufacture (Pharma) (id 62)
- Manufacture (Plastic) (id 63)
- Auto Transfer Semi (Pharma) (id 60)
- Auto Transfer Semi (Plastic) (id 61)
- Replenish on Order (MTO) (id 1)

## สไลด์ 5: Rule คือจุดที่ logic ลงรายละเอียดจริง
- Rule 7: GMP: Stock (Buy)
- Rule 146: GMP: Stock (Production) (copy) (Pharma)
- Rule 147: GMP: Stock (Production) (copy) (Plastic)
- Rule 144 และ 145: pull rules สำหรับ Transfer Pharma / Transfer Plastic

## สไลด์ 6: Operation Type คือเอกสารจริง
- Receipts
- Transfer Pharma
- Transfer Plastic
- Manufacturing Pharma
- Manufacturing Plastic
- ต้องให้ทีมดู Operation Type เพื่อแยกฝั่งงานให้ถูก

## สไลด์ 7: Putaway ใน uat
- RM/พลาสติก -> GMP/Stock/RM/PL01
- RM/สารเคมี -> GMP/Stock/RM/สารเคมี
- SFG/พลาสติก -> GMP/Stock/Semi/พลาสติก
- SFG/น้ำยา -> GMP/Stock/Semi/โรงงานยา
- Putaway ทำงานหลัง document เสร็จแล้ว

## สไลด์ 8: ตัวอย่าง FG-PNC-TH-01001
- orderpoint 175 เป็น trigger
- product route เป็น Manufacture (Pharma)
- demand ถูกจุดโดย orderpoint แต่ chain ฝั่งผลิตอิง product route

## สไลด์ 9: ตัวอย่าง FG-PSS-TH-01005
- orderpoint 249 route = Manufacture
- product route = Manufacture (Pharma)
- top BOM มี FG-PSS-TH-02001 x16, PK-CAR-PS-01003 x1, เทปกาว x1
- chain นี้มีทั้ง Pharma, Plastic และ Buy

## สไลด์ 10: ชั้นลึกของ FG-PSS-TH-01005
- FG-PSS-TH-02001 -> FG-PSS-TH-03001 x160 + packaging buy
- FG-PSS-TH-03001 -> FG-PSS-TH-04001..04006 + buy items
- สีแต่ละตัวแตกลง semi plastic และ solution pharma ต่อ

## สไลด์ 11: สรุป logic ที่ควรใช้สอนทีม
- Replenishment เป็นตัวเริ่มเรื่อง
- Route เป็น policy
- Rule เป็น logic ย่อยจริง
- Operation Type เป็นเอกสารจริง
- Putaway เป็น storage logic ตอนท้าย
