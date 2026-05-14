# UAT MANU Preparation - Server 14 goldmints_uat_manu

## Source Documents
- Excel: `C:\Users\tumsu\Downloads\UAT_MANU.xlsx`
- PowerPoint: `C:\Users\tumsu\Downloads\GMP_Manufacturing_UAT_from_UAT_MANU.pptx`
- Product codes match between Excel and PowerPoint: Yes

## Selected Products From Current UAT Documents
- `FG-PNC-TH-01001`
- `FG-PSS-TH-01005`
- `SM-PLS-UP-01001`
- `FG-MTK-IL-01001`
- `SM-JOI-PK-02001`

## Stock Cleanup Result
- Product tree scope: 15 products
- Manufactured/BoM products: 5
- Leaf/purchased components: 7
- Internal quant rows before cleanup: 4
- Internal quantity before cleanup: 0.0
- Reserved quantity before cleanup: 52.0
- Stock moves unreserved: 13
- Stale reserved quant rows released separately: 3
- Final internal quant/reserved rows in scope: 0

## Final Selected Product Readiness
| Product | On Hand | Forecast | BoM | Routes |
|---|---:|---:|---|---|
| `FG-MTK-IL-01001` | 0.0 | -10000.0 | Yes (2 lines) | Auto Transfer Semi (Pharma), Manufacture (Pharma), Replenish on Order (MTO) |
| `FG-PNC-TH-01001` | 0.0 | 0.0 | Yes (2 lines) | Manufacture (Pharma) |
| `FG-PSS-TH-01005` | 0.0 | -1526.0 | Yes (3 lines) | Manufacture (Pharma) |
| `SM-JOI-PK-02001` | 0.0 | 0.0 | Yes (2 lines) | Auto Transfer Semi (Plastic), Manufacture (Plastic) |
| `SM-PLS-UP-01001` | 0.0 | 0.0 | Yes (2 lines) | Auto Transfer Semi (Plastic), Manufacture (Plastic) |

## Procurement Readiness
- Leaf components without Buy route: 0
- BoM rounding issues in this scope: 0
- MO rounding issues in this scope: 0

## Leaf Components
| Product | On Hand | Forecast | UoM | Routes |
|---|---:|---:|---|---|
| `(no default code)` | 0.0 | 0.0 | Unit | Auto Transfer RM (Packaging), Buy |
| `(no default code)` | 0.0 | 0.0 | Unit | Auto Transfer RM (Packaging), Buy |
| `PK-CAR-PS-01003` | 0.0 | 0.0 | Pcs | Auto Transfer RM (Packaging), Buy |
| `PK-CAR-PS-02003` | 0.0 | 0.0 | Pcs | Auto Transfer RM (Packaging), Buy, Replenish on Order (MTO) |
| `RM-MBS-PK-00002` | 0.0 | 0.0 | Kgs | Auto Transfer RM (Plastic), Buy |
| `RM-MBS-WH-00001` | 0.0 | 0.0 | Kgs | Auto Transfer RM (Plastic), Buy |
| `RM-PLA-PP-00001` | 0.0 | 0.0 | Kgs | Auto Transfer RM (Plastic), Buy |

## Conclusion
- Current UAT document products are aligned between PowerPoint and Excel.
- Stock and reservations for the full product tree scope are cleared to zero in internal locations.
- Leaf components have Buy routes, so PO trigger readiness is valid for this scope.
- Manufacturing products have BoMs and manufacturing routes/custom routes visible for UAT trigger testing.