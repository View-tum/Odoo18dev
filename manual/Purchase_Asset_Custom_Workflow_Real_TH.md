# Purchase Asset Custom Workflow (Real Odoo Flow)

Figma:
- https://www.figma.com/online-whiteboard/create-diagram/ac2b448e-13a0-42c8-8f6a-3880113b607c?utm_source=other&utm_content=edit_in_figjam&oai_id=&request_id=bee0b0ae-cde6-4207-85f6-e13b62db33d2

## Scope

Flow นี้อิงจาก custom จริงในฐาน `view` และเริ่มจากช่วง `PR approval` ไปจนถึง `asset depreciation`.

## Main Flow

1. `PR Approval Lv1`
   - custom state ที่พบจริง: `pr_approval_lvl1`
2. `PR Approval Lv2`
   - custom state ที่พบใน report/status code: `pr_approval_lvl2`
3. `PR Approved`
   - state มาตรฐานที่ custom ใช้ต่อ: `approved`
   - มี analytic + budget check ก่อนผ่าน
4. `Create RFQ from PR`
   - wizard ทำงานได้เมื่อ PR อยู่ใน `approved` หรือ `in_progress`
5. `Draft RFQ / Draft PO created`
   - มี allocation link กลับไปที่ PR
   - PR ถูกขยับเป็น `in_progress`
6. `Wizard validation`
   - ต้องมี supplier
   - PR lines ต้องมาจาก company เดียวกัน
   - picking type ต้องตรงกัน
   - custom บล็อกการสร้างเกิน qty ที่ขอซื้อ
   - custom ตั้ง `currency_id` จาก PR vendor currency ได้
7. `Send RFQ to Vendor` (optional)
8. `PO Approval Workflow`
   - custom `approval.record` ครอบ purchase order
9. `PO Approved`
   - state = `purchase`
   - มี analytic + budget check
10. `Receipt?`
   - ถ้าเป็น stockable flow ให้รับของและ validate receipt
   - ถ้าเป็น consumable/service flow สามารถข้ามไป Vendor Bill ได้
11. `Create Vendor Bill from PO`
12. `Post Vendor Bill`
13. `Treat as Asset?`
   - bill line ต้องมาจาก product category ที่ติ๊ก `Treat as Asset`
14. `Create Assets button`
   - custom alert + ปุ่ม `Create Assets` แสดงบน Vendor Bill
15. `Create Assets Wizard`
   - กำหนด `Asset Model`
   - `Split Individual`
   - `Target Asset`
   - `Parent Asset`
16. `Create Asset Draft`
17. `Validate Asset`
18. `Compute Depreciation Board`
19. `Post Depreciation Journal`

## Source Modules

- `custom/goldmints_addon-main/oi_workflow_purchase_request`
- `custom/goldmints_addon-main/purchase_request`
- `custom/goldmints_addon-main/purchase_request_custom`
- `custom/goldmints_addon-main/purchase_request_vendor`
- `custom/goldmints_addon-main/budget_control_purchase_request`
- `custom/goldmints_addon-main/oi_workflow_purchase_order`
- `custom/goldmints_addon-main/budget_control_purchase`
- `custom/goldmints_addon-main/purchase_request_analytic_required`
- `custom/goldmints_addon-main/auto_asset_from_vendor_bill`
- `custom/goldmints_addon-main/account_asset_customization`
- `custom/goldmints_addon-main/account_asset_number`
- `custom/goldmints_addon-main/account_asset_history`

## Key Evidence

- PR sample in DB `view`: `PR00004` is in `pr_approval_lv1`
- PR report/status code exposes `pr_approval_lvl1` and `pr_approval_lvl2`
- PR base wizard only allows RFQ creation when PR is `approved` or `in_progress`
- PR custom wizard blocks over-quantity and inherits RFQ creation
- PO custom approval overrides default button flow through `approval.record`
- Vendor Bill custom shows `Create Assets` when bill contains asset-category lines
- Asset wizard creates draft `account.asset` records from vendor bill lines
