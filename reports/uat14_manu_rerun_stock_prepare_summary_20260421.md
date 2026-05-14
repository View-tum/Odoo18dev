# UAT14 MANU rerun and stock preparation

Database: `goldmints_uat_manu`

## UAT rerun result
- Total: 63
- Passed: 63
- Failed: 0
- Manual: 0

| Sheet | Cases |
|---|---:|
| 01_ตรวจสต็อกและวางแผน | 6 |
| 02_เปิดงานผลิต | 5 |
| 03_โอนและBackorder | 6 |
| 04_ShopFloorและMold | 13 |
| 05_ปิดงานและแก้ไข | 10 |
| 06_คุณภาพเอกสาร | 5 |
| 07_รายงานต้นทุนUoM | 18 |

## Stock preparation scope
- Top FG selected: FG-MTS-GH-01001, FG-MTS-JP-01001, FG-MTS-TW-01001, FG-MTS-XX-01001
- Manufactured FG/Semi tree cleared: 49 products
- Internal quant rows before clear: 82
- Internal quantity before clear: 361613419.36
- Reserved quantity before clear: 8740.0
- Stock moves unreserved: 3
- Internal quant rows after commit: 0
- Persist verify quant rows: 0
- Persist verify nonzero products: 0

## Prepared FG products
| Code | On hand after clear | Forecast | BOM components | Routes | Orderpoint |
|---|---:|---:|---:|---|---|
| FG-MTS-GH-01001 | 0.0 | -10757740.0 | 3 | Auto Transfer Semi (Pharma), Manufacture (Pharma), Replenish on Order (MTO) | Yes |
| FG-MTS-JP-01001 | 0.0 | -1460000.0 | 4 | Auto Transfer Semi (Pharma), Manufacture (Pharma), Replenish on Order (MTO) | Yes |
| FG-MTS-TW-01001 | 0.0 | -20000.0 | 8 | Auto Transfer Semi (Pharma), Manufacture (Pharma), Replenish on Order (MTO) | Yes |
| FG-MTS-XX-01001 | 0.0 | -1000.0 | 3 | Auto Transfer Semi (Pharma), Manufacture (Pharma), Replenish on Order (MTO) | Yes |

## Route diagnostic
- Products in the selected manufactured tree missing Manufacture route: 0
- Products in the selected manufactured tree missing MTO route: 14
- Missing MTO codes: RM-FIL-PS-01003, RM-FIL-PS-01004, SM-JOI-BU-02001, SM-JOI-GN-01001, SM-JOI-PK-02001, SM-JOI-PK-02002, SM-JOI-PP-02001, SM-JOI-YW-02001, SM-PLS-LO-02001, SM-PLS-MI-02001, SM-PLS-PU-02001, SM-PLS-TU-02001, SM-PLS-UP-02001, SO-PSS-UP-01001

## Candidate search note
- Top FG candidates checked: 55
- Full-chain candidates with current route setup: 1
- Current full-chain candidate(s): FG-PNF-ID-04001

## Source reports
- `C:\365_project\TheCool18e\Dev\reports\uat14_actual_run_20260421_135106.json`
- `C:\365_project\TheCool18e\Dev\reports\uat14_manu_stock_clear_commit_20260421_4fg.json`
- `C:\365_project\TheCool18e\Dev\reports\uat14_manu_stock_clear_persist_verify_20260421.json`
- `C:\365_project\TheCool18e\Dev\reports\uat14_manu_fg_top_candidate_route_check_20260421.json`