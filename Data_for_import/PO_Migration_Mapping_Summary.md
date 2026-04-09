# PO Migration Mapping Summary

## Output files
- `PO_Migration_Mapping_Prepared.xlsx`
- `PO_Open_Import_Ready.csv`

## Scope used for PO migration
- Source workbook: `PurchaseOrder2702.xlsx`
- Source sheet: `Open Order`
- Imported scope rule: `Is Return = False` and `Remain Physical > 0`

## Key assumptions
- Quantity to import = `Remain Physical`
- Currency mapping:
  - `THB -> THB`
  - `EUB -> EUR` (assumption)
  - `JPB -> JPY` (assumption)
- Order Date = `Delivery Date` when valid, otherwise blank
- Expected Arrival = `Delivery Date` when valid, otherwise blank
- Vendor matching = `Order Account` to `Contact.ref`, with exact vendor name match
- Product matching = `Item ID` to `Product.old_default_code`

## Counts
- Open Order lines in source: 464
- Eligible open PO lines: 340
- Eligible open PO documents: 153
- Ready import lines: 122
- Ready import PO documents: 56
- Blocked lines (unmapped vendor/product): 218
- Unmapped vendors: 4
- Unmapped products: 67

## Notes
- `Vendor aging 2025.xlsx` was not used for PO import preparation. It is relevant for AP opening balance migration, not purchase order import.
- Use `PO_Open_Ready_UI` if you want a human-readable file for Odoo import mapping.
- Use `PO_Open_Ready_Tech` if you prefer technical field names.
- Review `Unmapped_Vendors` and `Unmapped_Products` before final import. Missing masters must be created or mapped first.
