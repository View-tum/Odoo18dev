# AMS Editable Workflow Package

ชุดนี้เป็นไฟล์ใหม่ แยกจากชุดเดิมที่ `output\ams_workflow`

## ไฟล์หลัก

- `AMS_Editable_Swimlane_Workflows.drawio` ไฟล์หลักที่จัด layout แล้ว เปิดด้วย diagrams.net/draw.io เพื่อแก้ไข flow, lane, symbol, ข้อความ และ connector
- `AMS_Editable_Swimlane_Workflows_polished.drawio` สำเนา layout เดียวกับไฟล์หลัก เผื่ออยากเปิดเทียบหรือส่งต่อ
- `AMS_Editable_Swimlane_Workflows_before_layout.drawio` backup ก่อนจัด layout รอบล่าสุด
- `AMS_Visual_Swimlane_Flow_Viewer.html` เปิดดูภาพรวมแบบเร็วใน browser
- `flow_svgs\*.svg` รูป preview ของแต่ละ flow
- `AMS_Editable_Workflow_Mapping.xlsx` ตาราง mapping Excel ที่แก้ไขต่อได้
- `layout_audit.json` ผลตรวจระยะ layout, overlap, จำนวน lane และจำนวน node ของแต่ละหน้า

## ผลจัด layout ล่าสุด

- ปรับ node ให้มีขนาดสม่ำเสมอและอ่านง่ายขึ้น
- ปรับ lane height ให้กล่องไม่ชิดขอบบน/ล่าง
- ปรับ column spacing เป็นระยะที่อ่านได้เมื่อเปิดแบบ fit page
- ปรับเส้น connector ให้มี label background และ stroke ชัดขึ้น
- ตรวจแล้วทุกหน้า overlap = 0 และไม่มี node หลุดออกนอก lane

## วิธีแก้ไข diagram

1. เปิด https://app.diagrams.net
2. เลือก File > Open From > Device
3. เลือกไฟล์ `AMS_Editable_Swimlane_Workflows.drawio`
4. แก้ไขแต่ละหน้า เช่น Overall Flow, Sales, Procurement, Warehouse, Manufacturing, Accounting, Planning
5. Save As เป็นไฟล์ใหม่หรือบันทึกทับเฉพาะไฟล์ใน folder นี้

## สัญลักษณ์ที่ใช้

- Start/End: จุดเริ่มต้นหรือจุดจบของ flow
- Process: ขั้นตอนการทำงานหรือ function ใน Odoo
- Decision: จุดตัดสินใจ เช่น Approve/Reject, Pass/Fail, Buy/Make
- Input/Output: ข้อมูลนำเข้า/ส่งออก
- Document: เอกสาร เช่น SO, PO, MO, Invoice
- Database: ข้อมูล master/transaction ใน Odoo
- Connector/Flowline: เส้นเชื่อมขั้นตอน

## หมายเหตุ Standard vs Custom

Diagram แยกจุดที่ Odoo Standard รองรับและจุด Pain Point ที่อาจต้อง custom เช่น budget hard lock, supplier scoring, OPE/DPPM dashboard, consolidation/cash forecast และ customer forecast import
