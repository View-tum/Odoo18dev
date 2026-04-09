# Manufacturing Training Speaker Notes

## Slide 1: Title
- วันนี้เราจะดู Manufacturing ของระบบเราแบบ end-to-end
- เราจะเริ่มจาก setting และจบที่การตรวจต้นทุน
- เป้าหมายคือให้ทุกทีมตอบได้ว่า demand 1 ตัว วิ่งไปไหนบ้าง

## Slide 2: Session Objective
- session นี้ไม่ได้สอนแค่กดเมนู
- เราจะเน้น logic ของระบบ ว่าอะไร auto และอะไรต้องตัดสินใจเอง
- หลังจบ key user ต้อง trace เอกสารได้ตั้งแต่ SO จนถึง accounting

## Slide 3: Business Picture
- โรงงานเรามี 2 ฝั่ง คือ Plastic กับ Pharma
- Semi บางตัวมาจาก plastic แล้วส่งต่อไป pharma
- เพราะฉะนั้น route ต้องถูก ไม่อย่างนั้นระบบจะสร้างเอกสารผิดฝั่ง

## Slide 4: Document Map
- ให้ผู้เข้าอบรมเห็นก่อนว่ามีเอกสารอะไรเกี่ยวข้องบ้าง
- อยากให้ทุกคนจำ sequence ใหญ่ไว้คือ demand, procurement, manufacturing, transfer, delivery, accounting
- เวลาระบบผิด เราจะตามผิดจาก chain นี้

## Slide 5: Core Logic ของระบบ
- แนวคิดของเราคือใช้ standard เท่าที่ทำได้
- custom ถูกทำไว้เพื่อให้ flow auto มากขึ้น ไม่ใช่เพื่อแทน standard ทั้งหมด
- ทุก flow ต้อง trace ได้และไม่ทำลาย stock หรือ accounting

## Slide 6: Settings ที่สำคัญ
- ถ้า setting ผิด ระบบ auto ผิดทันที
- ให้เน้น 6 ตัว คือ route, manufacturing type, BoM, BoM picking, orderpoint, vendor
- ปัญหาส่วนใหญ่ของ flow ที่ไม่วิ่งมาจาก 6 จุดนี้

## Slide 7: Factory Separation Logic
- แสดงให้เห็นว่าพลาสติกกับยาถูกแยกด้วย operation type ไม่ใช่แยกด้วยชื่อสินค้าอย่างเดียว
- เวลาผลิตหรือโอนของ ให้ดูที่ `Operation Type` เสมอ
- ถ้าระบบเปิดผิดฝั่ง ให้ย้อนกลับไปดู route และ BoM picking

## Slide 8: Product Master Data
- FG คือ finished goods
- Semi คือสินค้ากึ่งสำเร็จรูป
- RM คือ raw material
- Solution คือฝั่งน้ำยา
- Packaging คือกล่อง ลัง shrink film

## Slide 9: Replenishment Logic
- MTO คือ demand มาจาก sale โดยตรง
- MTS คือเติม stock ผ่าน orderpoint
- Buy กับ Manufacture ตัดสินว่าจะไป PO หรือ MO
- อยากให้ทุกทีมเข้าใจว่าของขาดไม่ได้แปลว่าต้องไป PO เสมอ

## Slide 10: Flow 1 Promotion / SO 0 บาท
- อธิบายว่า free item และ FOC line ทำงานยังไง
- แม้ขาย 0 บาท ก็ยังมี stock movement และ cost
- เปิดเอกสาร `S11563` และ `SOB-263069` ให้ดู

## Slide 11: Flow 2 SO -> MTO
- SO บางตัวต้องไป child MO โดยตรง
- ให้ผู้เข้าอบรมดู procurement group เดียวกัน
- ย้ำว่า `make_to_order` ของ delivery ไม่เท่ากับสินค้าเป็น MTO เสมอ

## Slide 12: Flow 3 MTS / Min-Max
- orderpoint ใช้เมื่อไม่มี SO หรือใช้เติม stock
- ถ้าของพอ ระบบจะไม่ทำอะไร
- ถ้าของไม่พอ route จะบอกว่าจะไป MO หรือ PO

## Slide 13: Example FG-PSS-TH-01005
- ใช้ตัวนี้เป็นตัวอย่างเพราะ BoM หลายชั้นและมีทั้ง plastic กับ pharma
- ปัจจุบันตัวนี้ไม่ใช่ MTO จาก SO
- ถ้าขาดจะวิ่งจาก Min/Max

## Slide 14: Multi-level Manufacturing
- ตัวบนสุดคือ FG carton
- ชั้นถัดไปคือกล่อง 5 โหล
- ชั้นถัดไปคือแผงและสินค้าสีต่าง ๆ
- ชั้นลึกลงไปคือ semi plastic และ solution

## Slide 15: Shopfloor Execution
- อธิบายการทำงานของ operator
- จุดสำคัญคือ start, good qty, reject qty, done
- ถ้ากรอก qty ผิด จะกระทบทั้ง stock และ cost

## Slide 16: Parallel Workcenter Rules
- ระบบ parallel ถูกใช้เพื่อรองรับหลายเครื่อง
- ตอนนี้ logic ใหม่คือ workcenter ที่ done หรือ cancel จะไม่เอามากระจาย planned qty แล้ว
- cancelled workorder ก็ไม่แสดงใน shopfloor

## Slide 17: Mold Management
- mold ไม่ใช่แค่ข้อมูลประกอบ แต่เป็นทรัพยากรจริง
- ตอนนี้ระบบ map mold กับ product และ workcenter แล้ว
- mold life ขึ้นจาก output จริง ไม่ใช่จาก plan qty

## Slide 18: Transfer Logic
- semi จาก plastic ต้องไป pharma ผ่าน internal transfer
- เวลาเปิดเอกสาร ให้ชี้ให้ผู้ใช้เห็น `Transfer Plastic` และ `Transfer Pharma`
- ถ้า transfer ไม่มา ให้เช็ก route กับ stock location

## Slide 19: Purchasing Logic
- ของที่จะไป PO ต้องมี Buy route และมี vendor
- ถ้าไม่มี vendor แม้มี Buy route ก็จะไม่จบเป็น RFQ
- ถ้า orderpoint route เป็น Manufacture ของก็จะไป MO ก่อน

## Slide 20: Costing Logic
- actual cost แยกเป็น raw, machine, labor, mold
- std cost เป็นคนละเรื่องกับ actual
- อยากให้ accounting และ production เห็นภาพเดียวกัน

## Slide 21: Common Failure Points
- route ผิดฝั่ง
- orderpoint ผิด
- vendor ไม่มี
- mold ไม่ map
- stock อยู่ location ผิด
- transfer ไม่เกิด

## Slide 22: Demo Checklist
- ตอน demo ให้เปิดเอกสารจริงใน DB 11
- อย่าเดโมด้วยการอธิบายอย่างเดียว
- ให้ผู้เข้าอบรมเห็น transaction chain จริง

## Slide 23: Role by Function
- Planner ดู demand และ replenishment
- Production ดู MO และ shopfloor
- Warehouse ดู transfer และ stock move
- Purchase ดู RFQ/PO
- Accounting ดู valuation และ journal

## Slide 24: Closing
- ก่อนจบให้ทุกทีมตอบว่า ถ้าของหมด ระบบจะไป MO หรือ PO เพราะอะไร
- ถ้าตอบได้ แปลว่าเข้าใจ flow แล้ว
- ปิดด้วย UAT checklist และ next step หลัง training
