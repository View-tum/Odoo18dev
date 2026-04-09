# Flow Diagram 2 คอลัมน์: MTS vs MTO ใน UAT

## ตัวอย่างที่ใช้
- MTS: `FG-PNC-TH-01001`
- MTO: `FG-MTK-IL-01001`

## สรุปสั้น
- `MTS` = ของในคลังขาดก่อน แล้ว orderpoint ยิง procurement ไปเติม stock
- `MTO` = ลูกค้าสั่งก่อน แล้ว demand ดึง supply chain ย้อนกลับไปสร้างของ

## MTS Column
1. `Replenishment`
   - Trigger จาก orderpoint `175`
   - Location = `GMP/Stock`
   - min = `0`, max = `0`, trigger = `auto`
2. `Route`
   - Product route = `Manufacture (Pharma)`
3. `Rule`
   - Rule `146`
   - action = `manufacture`
   - source = `GMP/Stock/คลังลอย`
   - destination = `GMP/Stock`
4. `Operation Type`
   - `Manufacturing Pharma`
5. `Putaway`
   - ทำงานตอน stock/compoent เข้าปลายทางใหญ่แล้ว
   - ไม่ได้เป็นตัว trigger procurement

## MTO Column
1. `Replenishment`
   - Trigger จาก `SO demand`
   - ไม่มี orderpoint
2. `Route`
   - `Replenish on Order (MTO)`
   - `Manufacture (Pharma)`
   - `Auto Transfer Semi (Pharma)`
3. `Rule`
   - Rule `5` = pull จาก `GMP/Stock` ไป `Customers`
   - Rule `146` = manufacture ฝั่ง pharma
   - Rule `144` = transfer semi pharma
4. `Operation Type`
   - `Pick`
   - `Transfer Pharma`
   - `Manufacturing Pharma`
5. `Putaway`
   - ไปมีผลกับ material/semi ที่เข้าคลังระหว่างทาง
   - ไม่ได้อยู่บนขา customer โดยตรง

## สิ่งที่ต้องเน้นเวลาเทียบ
- MTS เริ่มจาก `stock shortage`
- MTO เริ่มจาก `sales demand`
- MTS เป้าหมายคือ `เติม stock`
- MTO เป้าหมายคือ `ตอบออเดอร์`

## Mermaid
```mermaid
flowchart LR
    subgraph MTS["MTS : FG-PNC-TH-01001"]
        A1[Replenishment\nOrderpoint 175\nGMP/Stock] --> A2[Route\nManufacture (Pharma)]
        A2 --> A3[Rule 146\naction = manufacture]
        A3 --> A4[Operation Type\nManufacturing Pharma]
        A4 --> A5[Putaway / Storage\nทำงานตอนของเข้าคลัง]
    end

    subgraph MTO["MTO : FG-MTK-IL-01001"]
        B1[Replenishment\nSO Demand\nไม่มี orderpoint] --> B2[Route\nMTO + Manufacture (Pharma) + Auto Transfer Semi (Pharma)]
        B2 --> B3[Rule 5 / 146 / 144\npull + manufacture + transfer]
        B3 --> B4[Operation Type\nPick + Transfer Pharma + Manufacturing Pharma]
        B4 --> B5[Putaway / Storage\nใช้กับ material ระหว่างทาง]
    end
```
