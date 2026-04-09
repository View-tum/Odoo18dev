# Work Center Import Mapping

ไฟล์ต้นทาง:
- `Work Center (mrp.workcenter) - ready import.xlsx`
- แนะนำให้ใช้ sheet: `ready import`

## แนะนำวิธี import

เพื่อให้ปลอดภัย แนะนำ import `2 รอบ`

### รอบ 1: โครงหลักของ Work Center / Mold
map เฉพาะ field หลักก่อน

| Excel column | Odoo import field | ใช้ไหม | หมายเหตุ |
|---|---|---:|---|
| `id` | `External ID` | Yes | ใช้เป็น external id ของ record |
| `name` | `Work Center` หรือ `Name` | Yes | ชื่อเครื่องหรือชื่อ mold |
| `code` | `Code` | Yes | รหัสเครื่อง / รหัส mold |
| `manufacturing_type` | `Manufacturing Type` | Yes | ค่าในไฟล์เป็น `Plastic` / `Pharma` |
| `tag_ids` | `Tags / Name` | Yes | ใช้ชื่อ tag ตรงจากไฟล์ |
| `default_capacity` | `Capacity` | Yes | ค่าเริ่มต้นของเครื่อง |
| `costs_hour` | `Cost per hour` | Yes | ต้นทุนเครื่องต่อชั่วโมง |
| `oee_target` | `OEE Target` | Yes | เป้าหมาย OEE |
| `sequence` | `Sequence` | Yes | ลำดับแสดงผล |
| `time_efficiency` | `Time Efficiency` | Yes | efficiency ของ work center |
| `is_mold` | `Is Mold?` | Yes | แยกว่า record นี้เป็น mold หรือ machine |
| `mold_cost_hour` | `Mold Cost / Hour` | Yes | ใช้กับ mold เป็นหลัก |
| `mold_life_limit` | `Mold Life Limit (Shots)` | Yes | กำหนด shot limit |
| `mold_cavities` | `Cavities` | Yes | จำนวนชิ้นต่อ 1 shot |

### รอบ 2: ความสัมพันธ์ Machine <-> Mold และ Mold <-> Product
import หลังจากรอบ 1 สำเร็จ

| Excel column | Odoo import field | ใช้ไหม | หมายเหตุ |
|---|---|---:|---|
| `allowed_mold_ids/name` | `Compatible Molds / Name` | Yes | ใช้กับแถวที่เป็นเครื่อง |
| `mold_product_line_ids/product_id` | `Produced Products Efficiency / Product` | Yes | ใช้กับแถวที่เป็น mold |

## คอลัมน์ที่แนะนำให้ข้าม

| Excel column | เหตุผล |
|---|---|
| `alternative_workcenter_ids` | ในไฟล์นี้ว่าง |
| `produced_product_ids/name` | เป็น field compatibility เก่า ใช้ซ้ำกับ `mold_product_line_ids/product_id` |
| `produced_product_ids` | ในไฟล์นี้ว่าง |
| `mold_product_line_ids` | เป็น technical/export column ไม่ต้อง map |
| `capacity_ids/product_id` | ในไฟล์นี้ว่าง |
| `capacity_ids` | ในไฟล์นี้ว่าง |
| `capacity_ids/time_start` | ในไฟล์นี้ว่าง |
| `allowed_mold_ids` | เป็น technical/export column ไม่ต้อง map |

## คำเตือนสำคัญ

### 1. `mold_product_line_ids/product_id` ตอนนี้มีแค่ Product
- model จริงรองรับ `Cycle Time (s)` และคำนวณ `Units / Hour`
- แต่ไฟล์นี้ยังไม่มี column ของ cycle time
- ถ้า import ตามนี้อย่างเดียว line จะถูกสร้าง แต่ `Cycle Time = 0`
- ถ้าต้องการ matrix สมบูรณ์ ควรเพิ่ม column แล้ว map ไปที่ `Produced Products Efficiency / Cycle Time (s)`

### 2. relation column ตอนนี้เป็นชื่อ ไม่ใช่ external id
- `allowed_mold_ids/name` ใช้ชื่อ mold
- `mold_product_line_ids/product_id` ใช้ชื่อสินค้าแบบ `[CODE] Name`
- ถ้าจะใช้ relation แบบ external id ต้องแปลงค่าข้อมูลในคอลัมน์ก่อน แล้วค่อย map ไป field แบบ `/External ID`

### 3. มีทั้ง machine และ mold อยู่ใน sheet เดียว
- machine จะมี `is_mold = False`
- mold จะมี `is_mold = True`
- import ได้ใน sheet เดียว แต่ต้องระวัง relation fields ให้ถูกฝั่ง

## Mapping แบบสั้นสำหรับ import wizard

### รอบ 1
- `id` -> `External ID`
- `name` -> `Name`
- `code` -> `Code`
- `manufacturing_type` -> `Manufacturing Type`
- `tag_ids` -> `Tags / Name`
- `default_capacity` -> `Capacity`
- `costs_hour` -> `Cost per hour`
- `oee_target` -> `OEE Target`
- `sequence` -> `Sequence`
- `time_efficiency` -> `Time Efficiency`
- `is_mold` -> `Is Mold?`
- `mold_cost_hour` -> `Mold Cost / Hour`
- `mold_life_limit` -> `Mold Life Limit (Shots)`
- `mold_cavities` -> `Cavities`

### รอบ 2
- `allowed_mold_ids/name` -> `Compatible Molds / Name`
- `mold_product_line_ids/product_id` -> `Produced Products Efficiency / Product`

## หมายเหตุจาก data file
- sheet `ready import` มีทั้งหมด `154` records
- ในนี้มี `mold` จริง `23` records
- field `allowed_mold_ids/name` ถูกใช้จริง `9` records
- field `mold_product_line_ids/product_id` ถูกใช้จริง `34` records
