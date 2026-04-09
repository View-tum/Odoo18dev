# Flow Diagram: FG-PSS-TH-01005 ใน UAT

## จุดตั้งต้น
- Product: `FG-PSS-TH-01005`
- Product Route: `Manufacture (Pharma)` id `62`
- Orderpoint: `249`
- Orderpoint Location: `GMP/Stock`
- Orderpoint Route: `Manufacture` id `6`
- Trigger: `auto`

## Top-level chain
1. Orderpoint 249 ตรวจ forecast ที่ `GMP/Stock`
2. ถ้าของไม่พอ ระบบเริ่ม procurement
3. Product route บอกว่าปลายทางหลักต้องวิ่งฝั่ง `Manufacture (Pharma)`
4. Rule `146` ทำให้ document หลักออกเป็น `Manufacturing Pharma`

## Top BOM
- `FG-PSS-TH-02001` x `16`
- `PK-CAR-PS-01003` x `1` -> `Buy`
- `เทปกาว` x `1` -> `Buy`

## Mid BOM
`FG-PSS-TH-02001` แตกเป็น
- `FG-PSS-TH-03001` x `160`
- `PK-BOX-PS-01002` x `16` -> `Buy`
- `PK-SHF-PS-01003` x `0.01424` -> `Buy`

## Color layer
`FG-PSS-TH-03001` แตกเป็น
- `FG-PSS-TH-04001` x `160`
- `FG-PSS-TH-04002` x `160`
- `FG-PSS-TH-04003` x `160`
- `FG-PSS-TH-04004` x `160`
- `FG-PSS-TH-04005` x `160`
- `FG-PSS-TH-04006` x `160`
- `RM-PET-RO-00001` x `1.952` -> `Buy`
- `PK-BLS-PS-01014` x `160` -> `Buy`

## ตัวอย่างชั้นลึก: FG-PSS-TH-04001
- `SM-PSS-TH-02001` x `160` -> Plastic branch
- `SM-PSS-TH-02002` x `160` -> Plastic branch
- `SM-JOI-PK-02002` x `160` -> Plastic branch
- `RM-FIL-PS-01004` x `160` -> Mixed branch (Buy + Pharma + Plastic child)
- `SO-PSS-LO-01001` x `0.176` -> Pharma branch

## Plastic branch
- `SM-PSS-TH-02001` -> route `61 + 63`
- `SM-PSS-TH-02002` -> route `61 + 63`
- `SM-JOI-PK-02002` -> route `61 + 63`
- Rule `145` -> `Transfer Plastic`
- Rule `147` -> `Manufacturing Plastic`

## Pharma branch
- `SO-PSS-LO-01001` -> route `62`
- `RM-FIL-PS-01004` -> route `60 + 62 + Buy`
- Rule `144` -> `Transfer Pharma`
- Rule `146` -> `Manufacturing Pharma`

## Buy branch
- `PK-CAR-PS-01003`
- `PK-BOX-PS-01002`
- `PK-SHF-PS-01003`
- `RM-PET-RO-00001`
- `PK-BLS-PS-01014`
- Rule `7` -> `Buy` -> `Receipts`

## Mermaid
```mermaid
flowchart TD
    A[Orderpoint 249\nGMP/Stock\nroute = Manufacture] --> B[FG-PSS-TH-01005\nroute = Manufacture (Pharma)]
    B --> C[Rule 146\nManufacturing Pharma]
    C --> D[FG-PSS-TH-02001 x16]
    C --> E[PK-CAR-PS-01003 x1\nBuy]
    C --> F[เทปกาว x1\nBuy]
    D --> G[FG-PSS-TH-03001 x160]
    D --> H[PK-BOX-PS-01002\nBuy]
    D --> I[PK-SHF-PS-01003\nBuy]
    G --> J[FG-PSS-TH-04001..04006]
    G --> K[RM-PET-RO-00001\nBuy]
    G --> L[PK-BLS-PS-01014\nBuy]
    J --> M[Plastic branch\nSM-PSS / SM-JOI]
    J --> N[Pharma branch\nSO-PSS / RM-FIL]
    M --> O[Rule 145 + 147\nINT-PL + MO-PL]
    N --> P[Rule 144 + 146\nINT-PH + MO-PH]
    E --> Q[Rule 7\nReceipts]
    F --> Q
    H --> Q
    I --> Q
    K --> Q
    L --> Q
```
