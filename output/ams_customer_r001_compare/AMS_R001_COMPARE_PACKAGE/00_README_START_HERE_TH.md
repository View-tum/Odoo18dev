# AMS R001 Compare Package

ชุดนี้เป็น version ใหม่สำหรับนำเสนอ R001 โดยไม่แก้ flow baseline เดิม

## ถ้าจะ present ลูกค้า ให้เปิดตามลำดับนี้

1. `00_DASHBOARD_AMS_R001_CLIENT_SUMMARY.html` หรือ `00_DASHBOARD_AMS_R001_CLIENT_SUMMARY.png`
   - หน้าแรกสำหรับสรุปสั้นว่าเราเข้ามาช่วยอะไร ทำให้ AMS ทำงานง่ายขึ้นอย่างไร และอะไรที่ Odoo standard ไม่มี
2. `01_AMS_R001_Comparison_Manday_Sequence.xlsx`
   - เปิด Sheet `05 Manday Summary` เพื่ออธิบายว่า Manday ใช้ไปกับอะไร
   - ต่อด้วย Sheet `01 R001 vs Our Mapping`, `02 Additions from R001 Blueprint`, `04 Odoo Function Detail`
3. `09_R001_Flow_Mapping_Table.xlsx` หรือ `10_R001_Flow_Mapping_Table.html`
   - ตาราง mapping อ่านง่าย แยกตาม flow โดยแยก `44 customer requests` ออกจาก `24 supporting blueprint/add-on mapping points`
   - ใช้ตอบคำถามว่า request/add-on point อยู่ flow ไหน, standard Odoo รองรับอะไร, จุดไหนต้องเพิ่ม/custom
4. `06_AMS_R001_Blueprint_Swimlane_TH.drawio`
   - เปิดหน้า `00 วิธีอ่าน R001 Blueprint Flow` ก่อน แล้วค่อยไปหน้า overall และราย module
5. `07_PRESENT_ORDER_START_TO_END_TH.md` หรือ `08_PRESENT_ORDER_START_TO_END_TH.html`
   - script การพูดตั้งแต่ต้นจนจบ
6. `02_AMS_R001_Presentation_Guide_TH.md` หรือ `03_AMS_R001_Presentation_Guide_TH.html`
   - guide รายละเอียดเสริมสำหรับอ่านทำความเข้าใจก่อน present
7. `04_Manday_Summary_Preview.png`
   - รูปสรุป Manday สำหรับส่งเร็วหรือแปะใน slide
8. `05_TFI_Blueprint_Reference.jpg`
   - ภาพ blueprint ลูกค้าต้นฉบับ ใช้เทียบเมื่อจำเป็น

## ไฟล์หลัก

- `00_DASHBOARD_AMS_R001_CLIENT_SUMMARY.xlsx` คือ dashboard แบบแก้ไขได้ใน Excel
- `00_DASHBOARD_AMS_R001_CLIENT_SUMMARY.html` คือ dashboard แบบเปิดใน browser สำหรับ present
- `00_DASHBOARD_AMS_R001_CLIENT_SUMMARY.png` คือ dashboard แบบรูปภาพ
- `01_AMS_R001_Comparison_Manday_Sequence.xlsx` คือไฟล์หลักสำหรับเทียบ R001 vs mapping เดิม พร้อม standard/custom, Manday และ sequence
- `09_R001_Flow_Mapping_Table.xlsx` คือไฟล์ mapping แบบอ่านง่าย แยกตาม flow โดย customer request จริงมี 44 ข้อ และมี supporting mapping point จาก blueprint/add-on 24 จุด
- `10_R001_Flow_Mapping_Table.html` คือ mapping table แบบเปิดอ่านใน browser
- `06_AMS_R001_Blueprint_Swimlane_TH.drawio` คือ flow ใหม่สำหรับ present blueprint R001 โดยเฉพาะ

## Sheet สำคัญใน Excel

- `00 Executive Summary`
- `01 R001 vs Our Mapping`
- `02 Additions from R001 Blueprint`
- `03 Blueprint Flow Mapping`
- `04 Odoo Function Detail`
- `05 Manday Summary`
- `06 Present Sequence`
- `07 Workshop Questions`
- `08 Raw Customer R001`

## วิธีเล่าให้ลูกค้าเข้าใจเร็ว

1. Dashboard: เราเข้ามา map requirement ให้เป็น Odoo flow, แยก standard/config/report/custom และทำให้เห็นจุดตัดสินใจ
2. Manday: ตัวเลขนี้เป็น initial estimate สำหรับ planning/workshop ยังไม่ใช่ fixed quotation
3. Workflow: ใช้ draw.io ไล่ end-to-end และราย module เพื่อยืนยัน owner, document, decision และ UAT scenario
4. Decision: ปิดด้วยการ lock scope P1/P2/P3 และเก็บคำถามที่ต้อง confirm ก่อน final quotation
