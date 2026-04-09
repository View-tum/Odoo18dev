# Manufacturing Handout

เอกสารนี้ใช้เป็น cheat sheet สำหรับผู้เข้าอบรมหลังจบคลาส

## 1. ดูก่อนว่า demand มาจากไหน
- `SO 0 บาท` = Promotion / FOC
- `SO -> MTO` = demand จาก sale โดยตรง
- `Min/Max` = demand จาก reordering rule

## 2. จะไป MO หรือ PO ดูจากอะไร
- ถ้า route เป็น `Manufacture` -> ไป `MO`
- ถ้า route เป็น `Buy` และมี vendor -> ไป `RFQ/PO`
- ถ้า route เป็น `Buy` แต่ไม่มี vendor -> ระบบไปต่อไม่สุด

## 3. Plastic กับ Pharma ดูตรงไหน
- ดู `Operation Type`
- `Manufacturing Plastic`
- `Manufacturing Pharma`
- `Transfer Plastic`
- `Transfer Pharma`

## 4. ถ้า SO เปิดแล้วระบบไม่สร้าง MO
- เช็ก product route
- เช็ก sale line route
- เช็ก stock ว่ายังพอหรือไม่
- เช็กว่าเป็น `MTO` จริงหรือเป็น `MTS`

## 5. ถ้าของหมดแล้วระบบไม่สร้าง PO
- เช็กว่า product มี `Buy`
- เช็ก vendor
- เช็ก orderpoint
- เช็ก location และ stock forecast

## 6. ถ้า MO เปิดแล้วไม่แตก child MO
- เช็ก BoM ของ component
- เช็ก route ของ component
- เช็ก BoM picking type
- เช็กว่า component นั้นมี stock พออยู่แล้วหรือไม่

## 7. ถ้า transfer ไม่มา
- เช็ก route ของสินค้า
- เช็ก operation type
- เช็ก location ต้นทางปลายทาง
- เช็ก stock reservation

## 8. Shopfloor ที่ต้องกรอก
- start
- good qty
- reject qty
- done
- scrap ถ้ามีของเสีย

## 9. Logic ใหม่ของ parallel shopfloor
- workcenter ที่ `done` หรือ `cancel` จะไม่ถูกเอาไปกระจาย qty
- cancelled workorder จะไม่แสดงใน shopfloor
- mold เดียวไม่ถูก assign ซ้ำข้าม parallel workorders

## 10. ถ้า mold ไม่ขึ้น
- เช็ก product mapping
- เช็ก workcenter mapping
- เช็กว่า mold ตัวนั้น active หรือไม่
- เช็กว่ามี sibling WO ที่ถือ mold อยู่แล้วหรือไม่

## 11. Mold life ขึ้นจากอะไร
- ขึ้นจาก output จริง
- ไม่ใช่จาก plan qty
- ถ้า output ไม่ถูก mold life ก็จะไม่ถูก

## 12. ถ้า cost ดูแปลก ให้เช็ก 4 อย่าง
- raw material
- machine cost
- labor cost
- mold cost

## 13. เอกสาร demo ที่ใช้ตรวจในระบบ
- Promotion quote: `S11563`
- FOC flow: `SOB-263069`
- MTO flow: `SOB-263070`
- MTS flow: `GMP/MOPH/00011`
- 100000 production: `GMP/MOPH/00001`
- Mold and shopfloor: `GMP/MOPL/00014`

## 14. คำถามที่ผู้ใช้ควรถามทุกครั้ง
- Demand นี้มาจาก SO หรือ Min/Max
- ตัวนี้ควรไป MO หรือ PO
- route อยู่ฝั่ง Plastic หรือ Pharma
- มี child MO ที่ควรเกิดหรือยัง
- transfer ที่ควรเกิดมาแล้วหรือยัง
- cost ที่ปลายทางสมเหตุผลหรือไม่

## 15. Checklist ก่อนใช้งานจริง
- route ถูก
- BoM ถูก
- orderpoint ถูก
- vendor ครบ
- mold map ครบ
- user เข้าใจจุดตรวจของตัวเอง
