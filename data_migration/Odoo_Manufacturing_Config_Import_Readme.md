# Odoo Manufacturing Config Import Templates

ไฟล์หลัก: `data_migration/Odoo_Manufacturing_Config_Import_Templates_PRO.xlsx`

## ใช้สำหรับ
1. Product Manufacturing Type
2. Workcenter Manufacturing Type
3. Operation Type
4. Route
5. Rule

## ลำดับ import ที่แนะนำ
1. `IMP_Product_MfgType`
2. `IMP_Workcenter_MfgType`
3. `IMP_OperationType`
4. `IMP_Route`
5. `IMP_Rule`

## หมายเหตุสำคัญ
- `Manufacturing Type` ใช้ค่า technical เท่านั้น: `plastic`, `pharma`, `packaging`
- `IMP_Rule` ควรอ้าง `Route/External ID` และ `Operation Type/External ID` เพื่อกัน matching ผิด
- Location ให้ใช้ค่า exact จาก `REF_Locations_Pro` โดยยึด `Complete Name`
- Warehouse ให้ใช้ชื่อ exact จาก `REF_Warehouses_Pro`
- Route / Rule เป็น config เชิงเทคนิค ควรทดสอบ import ใน `view` ก่อน `pro`
