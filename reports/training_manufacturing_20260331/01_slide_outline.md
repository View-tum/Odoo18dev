# Manufacturing Training Slide Outline

## Slide 1: Title
- Manufacturing Training
- Odoo 18 Enterprise
- Plastic + Pharma Integrated Flow

## Slide 2: Session Objective
- เข้าใจภาพรวมระบบ
- เข้าใจ 3 flow หลัก
- เข้าใจ shopfloor และ mold
- รู้จุดตรวจปลายทาง

## Slide 3: Business Picture
- โรงงานพลาสติก
- โรงงานยา
- ผลิตรายวัน
- ระบบต้อง auto ให้มากที่สุด

## Slide 4: Document Map
- SO
- Replenishment
- MO
- Work Order
- Transfer
- PO
- Delivery
- Invoice
- Journal Entry

## Slide 5: Core Logic ของระบบ
- `Standard First, Custom Later`
- แยก Plastic และ Pharma
- ทุก flow ต้อง trace ได้
- ทุก flow ต้องไม่ทำลาย accounting

## Slide 6: Settings ที่สำคัญ
- Product Routes
- Manufacturing Type
- BoM
- BoM Picking Type
- Orderpoint
- Vendor

## Slide 7: Factory Separation Logic
- `Manufacturing Plastic`
- `Manufacturing Pharma`
- `Transfer Plastic`
- `Transfer Pharma`
- ทำไมต้องแยก

## Slide 8: Product Master Data
- FG
- Semi
- RM
- Solution
- Packaging
- จุดที่ตั้งผิดแล้ว flow พัง

## Slide 9: Replenishment Logic
- MTO
- MTS
- Min/Max
- Buy
- Manufacture

## Slide 10: Flow 1 Promotion / SO 0 บาท
- free item
- FOC
- SO -> MO -> Transfer -> Delivery -> Invoice
- จุดตรวจสำคัญ

## Slide 11: Flow 2 SO -> MTO
- demand จาก sale
- procurement group
- child MO
- delivery และ invoice

## Slide 12: Flow 3 MTS / Min-Max
- orderpoint trigger
- ของพอ
- ของไม่พอ
- route ไป MO หรือ PO

## Slide 13: Example FG-PSS-TH-01005
- ไม่ใช่ MTO จาก SO
- วิ่งจาก orderpoint / Min-Max
- chain ยาวทั้ง Pharma และ Plastic
- ใช้เป็น case study ของ multi-level BoM

## Slide 14: Multi-level Manufacturing
- FG ระดับบน
- FG packing layer
- FG color layer
- Semi plastic layer
- Solution layer

## Slide 15: Shopfloor Execution
- start
- qty log
- done
- reject
- scrap

## Slide 16: Parallel Workcenter Rules
- distribute qty อย่างไร
- workcenter `done/cancel` ไม่กระจาย qty
- cancelled WO ไม่โชว์ใน shopfloor
- ผลที่เกิดกับ supervisor

## Slide 17: Mold Management
- mold to product
- mold to workcenter
- auto assign
- mold life
- guard ป้องกัน mold ซ้ำ

## Slide 18: Transfer Logic
- semi plastic ไป pharma
- internal transfer
- output / delivery
- จุดตรวจใน UI

## Slide 19: Purchasing Logic
- Buy route
- vendor requirement
- shortage -> RFQ/PO
- กรณี route เป็น Manufacture แม้มี Buy

## Slide 20: Costing Logic
- raw actual
- machine actual
- labor actual
- mold actual
- std cost vs actual cost

## Slide 21: Common Failure Points
- route ผิด
- vendor ไม่มี
- orderpoint ไม่ครบ
- mold ไม่ map
- stock อยู่ผิด location
- transfer ไม่เกิด

## Slide 22: Demo Checklist
- Promotion
- MTO
- MTS
- Shopfloor
- Mold
- Scrap
- Costing

## Slide 23: Role by Function
- Planner
- Production
- Warehouse
- Purchase
- Accounting
- IT / Key User

## Slide 24: Closing
- สิ่งที่ต้องเช็กทุกวัน
- สิ่งที่ต้อง escalate
- next step หลัง training
