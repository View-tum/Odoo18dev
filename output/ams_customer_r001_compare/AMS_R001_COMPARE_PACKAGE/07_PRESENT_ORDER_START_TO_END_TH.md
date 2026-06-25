# ลำดับการ Present ทั้งหมด: AMS R001 / Odoo Standard Mapping

เอกสารนี้ใช้เป็น script เปิดไฟล์ตั้งแต่ต้นจนจบสำหรับคุยกับลูกค้า R001 เป้าหมายคือทำให้ลูกค้าเข้าใจเร็วว่าเราเข้ามาช่วยอะไร ทำไม Odoo standard ช่วยได้หลายส่วน จุดไหนต้องเพิ่ม และ Manday ใช้ไปกับอะไร

## Message หลักที่ต้องพูดตั้งแต่ต้น

เราจะไม่เริ่มจากการ custom ทุกอย่างทันที แต่จะเริ่มจาก Odoo standard/config ก่อน แล้วค่อยแยกเฉพาะจุดที่ standard ไม่มีหรือไม่พอเป็น report, integration หรือ custom เพราะงานที่กระทบ Stock, MRP และ Accounting ต้องรักษาความถูกต้องของ flow, valuation และเอกสารบัญชี

## ลำดับเปิดไฟล์แบบเร็ว

1. `00_DASHBOARD_AMS_R001_CLIENT_SUMMARY.html`
2. `01_AMS_R001_Comparison_Manday_Sequence.xlsx` Sheet `05 Manday Summary`
3. `09_R001_Flow_Mapping_Table.xlsx` หรือ `10_R001_Flow_Mapping_Table.html`
4. `06_AMS_R001_Blueprint_Swimlane_TH.drawio`
5. `01_AMS_R001_Comparison_Manday_Sequence.xlsx` Sheet `01 R001 vs Our Mapping`
6. `01_AMS_R001_Comparison_Manday_Sequence.xlsx` Sheet `04 Odoo Function Detail`
7. `01_AMS_R001_Comparison_Manday_Sequence.xlsx` Sheet `07 Workshop Questions`

## 0. เปิด Package Folder

ไฟล์:
`C:\365_project\TheCool18e\Dev\output\ams_customer_r001_compare\AMS_R001_COMPARE_PACKAGE`

พูด:
วันนี้เราจะใช้ package R001 ชุดใหม่ที่ทำเพิ่มจาก requirement ใหม่ของลูกค้าและภาพ TFI blueprint โดยไม่ได้แก้ flow baseline เดิม ชุดนี้ใช้เพื่อ present, workshop และเตรียม scope สำหรับ UAT/quotation รอบถัดไป

ผลลัพธ์ที่ต้องการ:
ลูกค้าเข้าใจว่าเอกสารชุดนี้เป็น working package สำหรับ confirm scope ไม่ใช่แค่ diagram สวย ๆ

## 1. เปิด Dashboard เป็นหน้าแรก

ไฟล์:
`00_DASHBOARD_AMS_R001_CLIENT_SUMMARY.html`

ไฟล์สำรอง:
`00_DASHBOARD_AMS_R001_CLIENT_SUMMARY.png`
`00_DASHBOARD_AMS_R001_CLIENT_SUMMARY.xlsx`

ใช้เวลา:
3-5 นาที

พูด:
หน้าแรกนี้สรุปให้เห็นก่อนว่าเราเข้ามาทำอะไรให้ AMS ทำงานง่ายขึ้น เราเอา R001 และ blueprint มาจัดเป็น Odoo flow, แยกว่าส่วนไหนใช้ standard/config ได้, ส่วนไหนต้องทำรายงานหรือ KPI และส่วนไหน standard ไม่มี ต้องเป็น integration/custom

จุดที่ต้องชี้:
- Customer request จริงใน R001 มี 44 ข้อ ส่วนอีก 24 จุดคือ blueprint/add-on mapping points ที่ใช้ประกอบการอธิบาย ไม่ใช่ request เพิ่ม
- Standard/Config 196 MD คือส่วนที่ใช้ Odoo function และ setup process เป็นหลัก
- Report/KPI 67 MD คือส่วนที่ต้องทำแบบฟอร์ม, dashboard, COA, DPPM, OEE/OPE
- Custom/Integration 95 MD คือส่วนที่ต้องเชื่อม API/import, ทำ control guard หรือ design accounting เพิ่ม

ประโยคปิดช่วงนี้:
ดังนั้นภาพรวมคือเราไม่ได้ custom ทั้งระบบ แต่เราแยกให้เห็นก่อนว่าส่วนไหนใช้ Odoo ได้ทันที และส่วนไหนต้องตัดสินใจเป็น scope เพิ่ม

## 2. ต่อด้วย Manday ว่าใช้ไปกับอะไร

ไฟล์:
`01_AMS_R001_Comparison_Manday_Sequence.xlsx`

Sheet:
`05 Manday Summary`

ใช้เวลา:
5-7 นาที

พูด:
Manday ในไฟล์นี้เป็น initial estimate สำหรับ planning/workshop ยังไม่ใช่ fixed quotation ตัวเลขนี้ใช้เพื่อดูว่า effort กระจุกอยู่ตรงไหน และช่วยตัด scope เป็น P1/P2/P3 ได้ง่ายขึ้น

ตัวเลขหลัก:
- R001 numbered requirements: 44 items, Recommended 220.5 MD
- R001 solution/blueprint additions: 24 items, Recommended 137.5 MD
- Total mapping scope if all included: 44 customer requests + 24 supporting mapping points, Recommended 358 MD
- Range โดยประมาณ: 226.5-493.5 MD

วิธีอธิบาย Manday:
- Standard/Config ใช้กับ setup module, master data, workflow, access, UAT standard flow
- Report/KPI ใช้กับเอกสารและ dashboard เช่น COA, DPPM, OEE/OPE, BI, slow/dead stock
- Custom/Integration ใช้กับ API/import, hard lock, netting, multi-ledger, consolidation, accounting/stock design

จุดที่ต้องย้ำ:
Manday ไม่ใช่การคิดราคาปิดทันที แต่เป็นตัวช่วยคุย priority ถ้าลูกค้าอยากลด scope ต้องเลือกว่าจะเลื่อน requirement ใดไป future phase

## 3. เปิดตาราง Mapping ราย Flow ก่อนเข้า Diagram

ไฟล์:
`09_R001_Flow_Mapping_Table.xlsx`

ไฟล์สำรอง:
`10_R001_Flow_Mapping_Table.html`

ใช้เวลา:
5-10 นาที

พูด:
ตารางนี้เป็นตัวตอบว่าเก็บครบทุกจุดตาม R001 และ blueprint ที่ได้รับหรือไม่ โดยแยกให้ชัดว่า customer request จริงมี 44 ข้อ และมี blueprint/add-on mapping points อีก 24 จุดสำหรับประกอบการอธิบาย flow รวมเป็น mapping scope 68 จุด ไม่ใช่ request ลูกค้า 68 ข้อ

วิธีอ่าน:
- Sheet `00 Flow Mapping Summary` ใช้ดูภาพรวมแต่ละ flow ว่ามีกี่ข้อ, Standard/Config กี่ข้อ, Report/KPI กี่ข้อ, Custom/Integration กี่ข้อ และ MD เท่าไร
- Sheet `01 Detail Mapping 44+24` ใช้ไล่ราย customer request/add-on point ว่าอยู่ flow ไหน, Odoo standard รองรับอะไร, ต้องเพิ่มอะไร, MD/Phase/Priority คืออะไร
- Sheet `02 วิธีอ่าน` ใช้เป็นคำอธิบายสั้นสำหรับทีม present

จุดที่ต้องย้ำ:
คำว่า “ครบ” หมายถึงครบตามเอกสาร R001 และรูป blueprint ที่ได้รับในระดับ workshop/presentation แล้ว แต่รายการที่เป็น API, report format, COA, DPPM/OEE/OPE, budget hard lock, netting, multi-ledger และ WIP/valuation ต้อง confirm rule/sample กับลูกค้าก่อน final quotation

## 4. เปิด Workflow / Business Flow

ไฟล์:
`06_AMS_R001_Blueprint_Swimlane_TH.drawio`

ใช้เวลา:
30-45 นาที

เริ่มหน้า:
`00 วิธีอ่าน R001 Blueprint Flow`

พูด:
ก่อนเข้า flow จริง เราจะอธิบายวิธีอ่านสัญลักษณ์ก่อน เช่น Start/End, Process, Decision, Input/Output, Document, Database และ Connector เพื่อให้ทุกฝ่ายอ่าน diagram ด้วยภาษาเดียวกัน

ลำดับหน้าใน draw.io:
1. `00 วิธีอ่าน R001 Blueprint Flow`
2. `01 Overall R001 Blueprint End-to-End`
3. `02 Sales + Customer Forecast API`
4. `03 Procurement + PR PO Approval`
5. `04 RM Warehouse + Customer Supplied Material`
6. `05 Engineering + PCC BOM Routing`
7. `06 Quality + COA`
8. `07 Planning + IS WI MRP`
9. `08 Production + MO WO Rework`
10. `09 FG Warehouse + Delivery`
11. `10 Accounting + Thai Tax Legacy Docs`

วิธีเล่า flow ใหญ่:
เริ่มจากลูกค้าส่ง RFQ/Forecast หรือ PO เข้าระบบ จากนั้น Sales สร้าง quotation/SO, Planning ใช้ MPS/MRP แตกความต้องการ, Procurement ซื้อ RM, Warehouse รับและจ่ายวัตถุดิบ, Engineering ดู BOM/Routing/PCC, Production ผลิตผ่าน MO/WO, Quality ตรวจและออก COA, FG Warehouse รับสำเร็จรูปและส่งสินค้า, Accounting ออก IV/BI/PD/RR/PS/RE และปิดบัญชี

จุดตัดสินใจสำคัญ:
- Customer Forecast จะรับเป็น manual, Excel, EDI หรือ API
- Budget control ต้อง warning หรือ hard block
- Customer supplied material ต้องถือ stock owner และ valuation แบบใด
- COA format ต้องอิง spec จาก customer, product หรือ lot
- WIP จะ track ด้วย stock location หรือ process/accounting report
- Netting payment และ multi-ledger ต้องการระดับ statutory หรือ management report

## 5. กลับมา Excel เพื่อเทียบ R001 vs Our Mapping

ไฟล์:
`01_AMS_R001_Comparison_Manday_Sequence.xlsx`

Sheet:
`01 R001 vs Our Mapping`

ใช้เวลา:
15-20 นาที

พูด:
Sheet นี้เป็นตารางหลักสำหรับไล่ทีละ requirement ว่าขอเดิมของลูกค้าตรงกับ mapping เดิมของเราตรงไหน ถ้ามีอยู่แล้วจะบอกว่าเราอธิบายเพิ่มอะไร ถ้าเป็นเรื่องใหม่จะถูกจัดเป็น New / Need Mapping

คอลัมน์ที่ต้องอธิบาย:
- `Customer Requirement`: สิ่งที่ลูกค้าเขียนใน R001
- `Customer Solution`: note ของลูกค้า เช่น Multi Company, API, MPS, RMA
- `Our Existing Mapping`: requirement เดิมของเราที่ match
- `Odoo Standard Explanation`: Odoo standard รองรับด้วย module/function ใด
- `Standard vs Custom`: สรุปว่าเป็น Standard, Config, Report, Integration หรือ Custom
- `What to Add / Explain`: สิ่งที่เราต้องอธิบายเพิ่มตอน present
- `MD Rec`: Manday recommended

ตัวอย่างที่ควรหยิบพูด:
- Consolidation: Odoo multi-company มี แต่ consolidation/elimination ต้อง design เพิ่ม
- Budget Limit: Odoo budget มี แต่ hard block PR/PO ต้อง custom guard
- Customer Forecast API: Odoo MPS/MRP รองรับ demand แต่ automotive API/import ต้อง integration
- COA/DPPM/OEE: Quality/MRP มีข้อมูลต้นทาง แต่ report/formula ต้องทำเพิ่ม
- Thai Tax/QR: standard localization มีฐาน แต่ legacy format และ sequence ต้อง map เพิ่ม

## 6. เปิด Odoo Function Detail

ไฟล์:
`01_AMS_R001_Comparison_Manday_Sequence.xlsx`

Sheet:
`04 Odoo Function Detail`

ใช้เวลา:
10-15 นาที

พูด:
Sheet นี้ใช้ตอบคำถามเชิง function ว่า Odoo standard รองรับอะไร และ pain point ที่ต้องเพิ่มคืออะไร ตามหลัก Standard First, Custom Later

จุดที่ต้องเน้น:
- Sales, Purchase, Inventory, MRP, Quality, Accounting เป็น standard flow ที่ควรเริ่มก่อน
- งานเอกสาร legacy เช่น SP, FA, IMR, PCC, IS, WI, PI, IV, BI, PD, RR, PS, RE ต้อง map กับ Odoo document/model
- งาน KPI/report สามารถเริ่มจากข้อมูลมาตรฐาน แต่รูปแบบลูกค้าอาจต้องทำ report เพิ่ม
- งานที่กระทบ stock/accounting เช่น WIP, valuation, netting, multi-ledger ต้อง design review ก่อน custom

## 7. เปิด Workshop Questions เพื่อปิด scope

ไฟล์:
`01_AMS_R001_Comparison_Manday_Sequence.xlsx`

Sheet:
`07 Workshop Questions`

ใช้เวลา:
10 นาที

พูด:
คำถามเหล่านี้คือสิ่งที่ต้องตอบก่อน final quotation หรือก่อนทำ UAT scenario เพราะบาง requirement ยังมีหลายวิธีทำใน Odoo

คำถามสำคัญ:
- Consolidation ต้องเป็น statutory consolidation หรือ management report
- Budget ต้อง warning หรือ hard block
- Multi Ledger หมายถึงหลายสมุดบัญชี, หลาย reporting basis หรือหลาย company
- Forecast เข้ามาทาง Excel, EDI, API หรือ manual
- Customer supplied material ต้อง valuate หรือ off-balance
- COA format และ spec source คืออะไร
- OEE/OPE/DPPM ใช้สูตร approved แบบใด
- WIP ต้อง track ตาม location หรือ process
- ระบบเดิม Access/BP Soft/Express/Excel ต้อง migrate หรือ retire ตัวไหน

## 8. ปิดการ Present

ไฟล์:
`01_AMS_R001_Comparison_Manday_Sequence.xlsx`

Sheet:
`06 Present Sequence`

ใช้เวลา:
5 นาที

พูดสรุป:
สิ่งที่เราทำคือแปลง R001 ให้เป็น Odoo-ready flow, แยก standard/config/report/custom, ทำ Manday เพื่อใช้จัด priority และสร้าง swimlane flow เพื่อใช้ยืนยัน owner, document, decision และ UAT scenario

Output ที่ต้องได้จาก meeting:
- ยืนยัน scope P1/P2/P3
- ยืนยัน owner ของแต่ละ flow
- ยืนยัน requirement ที่ยังไม่ชัด
- ขอ sample document, report, file import/API
- ตกลง UAT scenario ตาม business flow

## สรุปลำดับไฟล์ที่ใช้ present จริง

1. `00_DASHBOARD_AMS_R001_CLIENT_SUMMARY.html`
2. `01_AMS_R001_Comparison_Manday_Sequence.xlsx`
3. `09_R001_Flow_Mapping_Table.xlsx` หรือ `10_R001_Flow_Mapping_Table.html`
4. `06_AMS_R001_Blueprint_Swimlane_TH.drawio`
5. `07_PRESENT_ORDER_START_TO_END_TH.md` หรือ `08_PRESENT_ORDER_START_TO_END_TH.html`
6. `02_AMS_R001_Presentation_Guide_TH.md` หรือ `03_AMS_R001_Presentation_Guide_TH.html`
7. `04_Manday_Summary_Preview.png`
8. `05_TFI_Blueprint_Reference.jpg`

## หมายเหตุเรื่อง flow baseline เดิม

Flow baseline เดิมยังใช้เป็น reference ภาพรวมได้ แต่ไม่ต้องแก้หรือทับไฟล์เดิม สำหรับ R001 ให้ใช้ `06_AMS_R001_Blueprint_Swimlane_TH.drawio` เป็น version ใหม่ เพราะมี detail เพิ่มจาก R001 เช่น legacy document code, customer supplied material, COA, IS/WI, Thai Tax, Netting, Multi Ledger และ Forecast API
