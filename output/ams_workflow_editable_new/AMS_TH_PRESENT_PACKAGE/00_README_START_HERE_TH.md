# AMS TH Present Package

ให้เปิดไฟล์ตามลำดับเลขด้านหน้า ตั้งแต่ 00 ถึง 05

## ลำดับไฟล์

1. `00_README_START_HERE_TH.md`
   - ไฟล์นี้ ใช้ดูว่าควรเปิดอะไรตามลำดับ

2. `01_AMS_SWINLANE_TH_PRESENT.drawio`
   - ไฟล์หลักสำหรับ present และแก้ไขใน diagrams.net
   - มีหน้าเรียงตั้งแต่ `00 วิธีอ่าน Flow`, `01 ลำดับ Present`, legend, overall flow และ flow ราย module

3. `02_AMS_Workflow_Mapping_with_Manday.xlsx`
   - Excel mapping ที่เพิ่ม Manday แล้ว
   - Sheet สำคัญ: `Manday Summary`, `Present Sequence`, `Requirement Mapping`, `Custom Backlog`

4. `03_AMS_SWINLANE_TH_Presentation_Guide.html`
   - คู่มือวิธีอ่าน flow และลำดับการ present แบบเปิดอ่านใน browser

5. `04_AMS_SWINLANE_TH_Presentation_Guide.md`
   - คู่มือแบบ Markdown สำหรับแก้ไขต่อ

6. `05_Manday_Summary_Preview.png`
   - ภาพ preview ของ Manday Summary

## วิธีเริ่ม Present

1. เปิด `01_AMS_SWINLANE_TH_PRESENT.drawio` ด้วย diagrams.net
2. เริ่มจากหน้า `00 วิธีอ่าน Flow`
3. ต่อด้วยหน้า `01 ลำดับ Present`
4. อธิบายหน้า `02 คำอธิบายสัญลักษณ์`
5. เข้า `03 ภาพรวม AMS End-to-End`
6. ลงรายละเอียดทีละ module ตามลำดับ:
   - Sales / CRM
   - Procurement
   - Warehouse / Logistics
   - Manufacturing / Quality
   - Accounting / Finance
   - Planning / MRP Master Data
7. เปิด `02_AMS_Workflow_Mapping_with_Manday.xlsx`
8. ใช้ sheet `Manday Summary` สรุป effort
9. ใช้ sheet `Present Sequence` เป็น script ในการพูด
10. ปิดท้ายด้วย action list: Standard / Config / Report / Custom และ owner ของแต่ละ flow

## วิธีอ่าน Manday

- `Manday Min` คือ effort ต่ำสุด ถ้า requirement ชัดและใช้ standard/config ได้มาก
- `Manday Max` คือ effort เผื่อกรณีต้อง design, revise, UAT fix หรือมี data gap
- `Manday Recommended` คือค่ากลางที่ใช้คุย planning เบื้องต้น
- ตัวเลขนี้เป็น initial estimate สำหรับ workshop ไม่ใช่ final quotation

## หลักการที่ใช้

- Standard First, Custom Later
- Custom เฉพาะจุดที่ standard/config/report ไม่ตอบโจทย์
- งานที่กระทบ Stock, Costing, WIP, FG, COGS, Invoice, Vendor Bill หรือ Payment ต้อง review แยกก่อนทำ custom
