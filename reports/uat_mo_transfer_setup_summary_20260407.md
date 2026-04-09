# UAT MO Transfer Setup Summary

วันที่ตรวจ: `2026-04-07`
Server: `10.0.0.14`
Database: `goldmints_uat`

หมายเหตุ:
- ตรวจแบบ `read-only` ผ่าน Odoo shell บน server
- ไม่มีการแก้ไฟล์, เพิ่มไฟล์, upgrade module, หรือเขียนข้อมูลใด ๆ บน server

## สรุปผู้บริหาร
ปัญหา `MO แล้วใบ transfer มาไม่ครบ` ใน `goldmints_uat` ไม่ได้เกิดจาก route/rule หลักหาย แต่เกิดจาก `product route assignment ไม่ครบ` เป็นหลัก

สิ่งที่ตั้งไว้ถูกแล้ว:
- `Auto Transfer Semi (Pharma)` -> `Transfer Pharma`
- `Auto Transfer Semi (Plastic)` -> `Transfer Plastic`
- `Manufacture (Pharma)` -> `Manufacturing Pharma`
- `Manufacture (Plastic)` -> `Manufacturing Plastic`

สิ่งที่เป็นปัญหา:
- สินค้ากลุ่ม `SFG` บางตัวมี `Manufacture (...)` แต่ไม่มี `Auto Transfer Semi (...)`
- สินค้ากลุ่ม `RM` หลายตัวมี `Buy` แต่ไม่มี `Auto Transfer RM (...)`

ผลกระทบ:
- ระบบยังสร้าง `MO` ได้
- แต่ `Transfer` ที่คาดว่าจะเข้า `GMP/Stock/คลังลอย` หรือ staging จะไม่ถูกสร้างในบางกรณี

## สิ่งที่ตรวจแล้ว

### 1. Operation Types ใน GMP
มีครบและใช้งานได้:
- `Transfer Pharma` sequence `INT-PH` : `GMP/Stock -> GMP/Stock/คลังลอย`
- `Transfer Plastic` sequence `INT-PL` : `GMP/Stock -> GMP/Stock/คลังลอย`
- `Manufacturing Pharma` sequence `MO-PH` : `GMP/Stock/คลังลอย -> GMP/Stock`
- `Manufacturing Plastic` sequence `MO-PL` : `GMP/Stock/คลังลอย -> GMP/Stock`

สรุป:
- ฝั่ง `operation type` ไม่ใช่ root cause หลัก

### 2. Routes / Rules หลัก
ตั้งไว้ครบ:
- `Auto Transfer Semi (Pharma)` มี rule `Transfer SM (copy) (Pharma)`
  - action = `pull`
  - source = `GMP/Stock/Semi`
  - destination = `GMP/Stock/คลังลอย`
  - operation type = `Transfer Pharma`
- `Auto Transfer Semi (Plastic)` มี rule `Transfer SM (copy) (Plastic)`
  - action = `pull`
  - source = `GMP/Stock/Semi`
  - destination = `GMP/Stock/คลังลอย`
  - operation type = `Transfer Plastic`
- `Manufacture (Pharma)` มี rule สร้าง `Manufacturing Pharma`
- `Manufacture (Plastic)` มี rule สร้าง `Manufacturing Plastic`

สรุป:
- ตัว engine กลางยังอยู่ครบ
- ปัญหาอยู่ที่ `สินค้าไม่ได้ผูก route ให้ครบ`

## Root Cause หลัก

### A. SFG ที่มี `Manufacture (Pharma)` แต่ไม่มี `Auto Transfer Semi (Pharma)`
สินค้ากลุ่มนี้จะสร้าง `MO` ได้ แต่จะไม่สร้าง `Transfer Pharma` เข้าคลังลอย

รายการที่พบ:
- `FG-PNF-TH-03001`
- `FG-PNR-TH-04001`
- `FG-PPR-TH-02001`
- `FG-PPR-TH-02002`
- `SO-MTS-XX-01001`
- `SO-PAS-XX-01001`
- `SO-PAS-XX-01002`
- `SO-PNS-XX-01001`
- `SO-PPR-UP-01001`
- `SO-PPS-LO-01001`
- `SO-PSS-LO-01001`
- `SO-PSS-UP-01001`

ตัวอย่างที่กระทบจริง:
- `SO-PSS-LO-01001`
  - route ปัจจุบัน: `Manufacture (Pharma)` อย่างเดียว
  - ถูกใช้ใน BOM ของ:
    - `FG-PSS-TH-04001`
    - `FG-PSS-TH-04002`
    - `FG-PSS-TH-04003`
    - `FG-PSS-TH-04004`
    - `FG-PSS-TH-04005`
    - `FG-PSS-TH-04006`
  - ผลคือระบบสร้าง MO ของน้ำยาได้ แต่ไม่สร้าง `Transfer Pharma` สำหรับน้ำยาเข้าคลังลอย

### B. RM ที่มี `Buy` แต่ไม่มี `Auto Transfer RM (...)`
สินค้ากลุ่มนี้รับของเข้า stock ได้ แต่จะไม่สร้าง transfer จาก RM ไป staging/คลังลอยให้อัตโนมัติ

ตัวอย่างที่พบ:
- กลุ่มสารเคมี:
  - `00529`
  - `00530`
  - `00532`
  - `00533`
  - `00534`
- กลุ่มบรรจุภัณฑ์:
  - หลายตัวในตระกูล `PK-BAG-*`
  - หลายตัวในตระกูล `PK-BLS-*`
  - หลายตัวในตระกูล `PK-CAR-*`
  - หลายตัวในตระกูล `PK-SHF-*`
- กลุ่มพลาสติก:
  - `RM-PLA-HD-00001`
  - `RM-PVC-RO-01001`
  - `RM-PVC-RO-01002`
  - `RM-PVC-RO-01003`
  - `RM-PVC-RO-01004`
  - `RM-PVC-RO-01006`

## ตัวอย่างสินค้าเปรียบเทียบ

### ตัวอย่างที่ตั้งถูก
`SM-PSS-TH-02001`
- route:
  - `Auto Transfer Semi (Plastic)`
  - `Manufacture (Plastic)`

ผล:
- ระบบมีทั้ง transfer และ MO ตามที่คาด

`RM-FIL-PS-01004`
- route:
  - `Auto Transfer Semi (Pharma)`
  - `Manufacture (Pharma)`
  - `Buy`

ผล:
- chain ทำได้ครบกว่าตัวที่มีแค่ `Manufacture (Pharma)`

### ตัวอย่างที่ตั้งไม่ครบ
`SO-PSS-LO-01001`
- route:
  - `Manufacture (Pharma)`

ผล:
- ระบบรู้ว่าต้องผลิต
- แต่ไม่รู้ว่าต้องสร้าง `Transfer Pharma` ก่อนหรือระหว่าง flow

## ข้อสังเกตเพิ่ม

### 1. Default source ของ Operation Type
`Transfer Pharma` และ `Transfer Plastic` ตั้ง default source เป็น `GMP/Stock`

ผลกระทบ:
- ไม่กระทบ auto-generated transfer ที่มาจาก rule มากนัก เพราะ rule มี source/destination ของตัวเอง
- แต่มีผลต่อ `manual transfer` เพราะ user จะเห็นต้นทาง default ไม่ตรงกับ `GMP/Stock/Semi`

### 2. BOM ของตัวอย่างที่ตรวจ
`FG-PSS-TH-01005` และลูกหลายชั้นของมันใช้ routing pattern ที่ค่อนข้างชัด:
- กลุ่ม plastic components มักมี `Auto Transfer Semi (Plastic)` + `Manufacture (Plastic)` ครบ
- บางกลุ่ม pharma semi โดยเฉพาะน้ำยา มีแค่ `Manufacture (Pharma)`

## สรุปเชิงธุรกิจ
ถ้าธุรกิจคาดว่า:
- ของกึ่งสำเร็จ (`Semi`) ต้องมีใบโอนเข้า `คลังลอย`
- วัตถุดิบ (`RM`) ต้องมีใบโอนเข้า staging ก่อนผลิต

ตอนนี้ setup บน product ยังไม่ครบพอให้ระบบสร้าง transfer ทุกจุดโดยอัตโนมัติ

## แนวทางแก้

### ระยะสั้น
1. ตรวจสินค้ากลุ่ม `SFG / น้ำยา` ที่ถูกใช้เป็น component ใน BOM
2. เติม `Auto Transfer Semi (Pharma)` ให้ตัวที่ต้องมีใบโอนเข้าคลังลอย
3. ตรวจสินค้ากลุ่ม `RM` ที่ต้องโอนเข้า staging
4. เติม `Auto Transfer RM (Pharma/Plastic/Packaging)` ให้ตรง category และหน้างานจริง

### ระยะกลาง
1. ทำ audit ทุก BOM เพื่อหาว่า component ไหนใช้ใน production แต่ route ไม่ครบ
2. แยก policy ให้ชัด:
   - ตัวไหนต้อง `Buy` อย่างเดียว
   - ตัวไหนต้อง `Buy + Auto Transfer RM`
   - ตัวไหนต้อง `Manufacture` อย่างเดียว
   - ตัวไหนต้อง `Manufacture + Auto Transfer Semi`

## ข้อสรุปสุดท้าย
ปัญหานี้เป็น `setup gap` ที่ระดับ `product routes`

ไม่ใช่:
- rule พัง
- operation type หาย
- route engine เสีย

ถ้าต้องการให้ `MO -> Transfer` มาครบตามที่ทีมหน้างานคาด ต้องเติม route บนสินค้าให้ครบตามบทบาทของสินค้าใน flow จริง
