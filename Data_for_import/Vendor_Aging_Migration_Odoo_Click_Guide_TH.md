# คู่มือใช้งาน Vendor Aging Migration บน DB `pro`

ไฟล์หลัก: `c:\365_project\TheCool18e\Dev\Vendor_Aging_Migration_Pro_All_In_One.xlsx`

## หลักการ
1. ใช้ **Vendor Bill** ถ้าต้องการเอกสารเจ้าหนี้ระดับใบและต้องการให้ Aged Payable ออกตาม invoice/ref เดิม
2. ใช้ **AP Opening** ถ้าต้องการเปิดยอดเจ้าหนี้แบบเร็ว โดยไม่สร้างบิลย้อนหลัง
3. **ห้ามใช้ทั้งสองวิธีซ้ำกับรายการเดียวกัน**
4. ไฟล์นี้ map กับ DB `pro` แบบ strict โดยใช้ `partner.ref + exact vendor name`

## สรุป
- Source rows: 138
- Vendor Bill ready: 137
- Vendor Bill blocked: 1
- AP Opening ready rows: 274
- Missing vendors: 0
- Ambiguous vendors: 0
- Mismatch vendors: 1

## วิธีใช้ Vendor Bill
1. เปิด `Accounting > Vendors > Bills`
2. เปลี่ยนเป็นมุมมอง list
3. กด `Import`
4. อัปโหลดไฟล์ `Vendor_Aging_Migration_Pro_All_In_One.xlsx`
5. เลือก sheet `Vendor_Bill_Ready`
6. import แบบทดสอบก่อน 5-10 แถว
7. ตรวจ draft bills/refunds
8. เมื่อถูกต้องค่อย post ทั้งหมด
9. ตรวจรายงาน `Aged Payable`

## วิธีใช้ AP Opening
1. เปิด `Accounting > Accounting > Journal Entries`
2. กด `Import`
3. อัปโหลดไฟล์ `Vendor_Aging_Migration_Pro_All_In_One.xlsx`
4. เลือก sheet `AP_Opening_Ready`
5. import แบบทดสอบก่อน
6. ตรวจ journal `Opening Vendor Bill`
7. post ทั้งหมด
8. ตรวจ `Aged Payable` และ `Trial Balance`

## ข้อจำกัด
- ถ้า vendor ยังไม่ตรงกับ DB `pro` ระบบจะ block แถวไว้
- ตอนนี้แถวที่ blocked หลักคือ vendor code `00119` เพราะ ref ใน DB ชี้ไป partner คนละราย
