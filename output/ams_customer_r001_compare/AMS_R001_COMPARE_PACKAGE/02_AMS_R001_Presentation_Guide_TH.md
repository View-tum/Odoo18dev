# AMS R001 Comparison Presentation Guide

## เริ่มอ่านจากอะไร

- เริ่มจากไฟล์ Excel: 01_AMS_R001_Comparison_Manday_Sequence.xlsx
- เปิด sheet 00 Executive Summary เพื่อบอก scope และตัวเลขรวม
- ต่อด้วย sheet 03 Blueprint Flow Mapping เพื่ออธิบายภาพ TFI blueprint จากซ้ายไปขวา
- ใช้ sheet 01 R001 vs Our Mapping เพื่อเทียบ requirement ลูกค้ากับ mapping เดิมของเรา
- ใช้ sheet 02 Additions from R001 Blueprint เพื่อคุยรายการที่เพิ่มจาก Solution note และภาพ blueprint
- ปิดด้วย sheet 05 Manday Summary และ 06 Present Sequence

## ประเด็นที่เพิ่มจากไฟล์ลูกค้า R001

- ลูกค้าเพิ่ม Solution note เช่น Multi Company, Need Budget APP, Need Project APP, Use Landed Cost, Use Action WIP, MPS, API, RMA
- ต้องอธิบายเพิ่มว่า Solution เหล่านี้ใน Odoo คือ standard/config/custom ระดับไหน
- ภาพ blueprint เพิ่มเอกสาร legacy และ handoff เช่น SP, FA, IMR, PCC, COA, IS, WI, PI, IV, BI, PD, RR, PS, RE
- ต้อง map เอกสารเดิมเหล่านี้กับ Odoo model/document ก่อนทำ UAT

## ลำดับ Present แบบละเอียด

- 1. เปิดด้วย objective: เทียบ R001 กับ mapping เดิมและ identify สิ่งที่ต้องเพิ่ม
- 2. อธิบายวิธีอ่าน blueprint: lane คือแผนก, ลูกศรคือ handoff, รหัสเอกสารคือ legacy document ที่ต้อง map กับ Odoo
- 3. เริ่ม Sales: RFQ/Quotation/SO/Customer PO/Forecast/API
- 4. ต่อ Procurement: PR/RFQ/PO/Blanket/Supplier evaluation
- 5. ต่อ Warehouse RM: Receipt, Tag, Lot, Shelf, Customer supplied material
- 6. ต่อ Engineering/QC: PCC, BOM/Routing, Quality Check, COA
- 7. ต่อ Planning/Production: MPS/MRP, IS, WI, MO, WO, Rework/Scrap, OEE/OPE/DPPM
- 8. ต่อ FG/Delivery: PI, Delivery by SO, route/cost/fleet
- 9. ปิด Accounting: Invoice, Billing, Payment, Receipt, Thai Tax, QR, Netting, Multi Ledger
- 10. Review Manday: แยก base requirement กับ add-on จาก R001/blueprint
- 11. ปิดด้วย Workshop Questions และ action owner

## วิธีอธิบาย Standard vs Custom

- Standard: ใช้ Odoo module โดย config/master data ได้ เช่น Sales, Purchase, Inventory, MRP, Quality, Accounting, Thai localization
- Config + Report: standard มีข้อมูล แต่ต้องจัด report/form/dashboard เฉพาะบริษัท เช่น COA, BI, stock aging, sales dashboard
- Custom / Integration: standard ไม่มี business rule หรือมี external file/API เช่น customer forecast API, supplier scorecard weighted, budget hard lock, netting wizard
- Accounting/Stock Critical: WIP, valuation, cost variance, customer supplied material ต้อง review design ก่อน custom

## Manday หมายถึงอะไร

- Manday เป็น initial estimate สำหรับ workshop/planning
- MD Min คือกรณี requirement ชัดและใช้ standard/config ได้มาก
- MD Max คือกรณีต้อง revise, build report/custom, UAT fix หรือมี data gap
- MD Recommended คือค่ากลางใช้คุย priority และ phase
- ตัวเลขยังไม่ใช่ fixed quotation จนกว่าจะ scope lock
