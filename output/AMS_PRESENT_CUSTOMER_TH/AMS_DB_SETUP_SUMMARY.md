# AMS Demo Database Setup Summary

- Database: `AMS`
- URL: `http://localhost:8813`
- Login: `admin` / `admin`
- Standard only installed custom modules: `0`

## Configured
- Company set to AMS Co., Ltd. with THB currency
- Demo customer and supplier configured
- Products, product codes, categories, stockability, lot tracking, sale/purchase flags configured
- BOM AMS.400 REV 00 configured with 18 components and 21 routing operations
- Raw material and trading stock lots loaded to WH/Stock for demo production
- Reordering rules configured for raw materials
- Quality control points configured on selected manufacturing operations

## Test Flow
- PASSED: Purchase Order confirmed - P00005
- PASSED: Vendor receipt validated - WH/IN/00003
- PASSED: Sales Order confirmed - S00004
- PASSED: Manufacturing Order produced - WH/MO/00006
- PASSED: Customer delivery validated - WH/OUT/00004
- PASSED: Customer invoice posted - INV/2026/00003 (AMS-DEMO-20260619-1531)

## Current Records
- required_modules: {'sale_management': 'installed', 'purchase': 'installed', 'stock': 'installed', 'mrp': 'installed', 'mrp_workorder': 'installed', 'quality_control': 'installed', 'quality_mrp': 'installed', 'stock_account': 'installed', 'account': 'installed', 'approvals': 'installed', 'stock_barcode': 'installed', 'l10n_th': 'installed'}
- products: 30
- bom: AMS.400 REV 00: [AMS.400] AMS.400 REV 00
- bom_components: 18
- bom_operations: 21
- quality_points_total: 15
- raw_material_orderpoints: 17

## Custom Gap Points
- Request FA Sample: ต้องมีฟอร์มและ approval เฉพาะ | Standard position: ใช้ Sales/CRM + Activity เป็น workaround ได้
- Request Raw Material: ฟอร์มเบิก/ขอวัตถุดิบเฉพาะและ approval หลายระดับ | Standard position: ใช้ Manufacturing component demand / internal transfer ได้บางส่วน
- PCC / Process Control Chart: รูปแบบเอกสาร PCC เฉพาะลูกค้า | Standard position: ใช้ Quality Check เป็น data source ได้ แต่ template/report ต้อง custom
- Document Control: ทะเบียนเอกสารและ revision control เฉพาะ | Standard position: ใช้ Documents/PLM ได้บางส่วน แต่ format และ workflow ต้อง custom/config เพิ่ม
- Legacy Thai Forms / QR Label: แบบฟอร์มและ QR ตามรูปเดิม | Standard position: ข้อมูลมีใน Odoo แต่ report layout ต้อง custom

## Odoo UI Screenshots
- `odoo_screenshots/01_PO_P00005.png`
- `odoo_screenshots/02_Receipt_WH_IN_00003.png`
- `odoo_screenshots/03_SO_S00004.png`
- `odoo_screenshots/04_MO_WH_MO_00006.png`
- `odoo_screenshots/05_Delivery_WH_OUT_00004.png`
- `odoo_screenshots/06_Invoice_INV_2026_00003.png`
