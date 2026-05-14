# Rounding Audit - goldmints_uat_manu

## Overall Result
- UoM records checked: 40
- Invalid UoM rounding/factor: 0
- Product stock/purchase UoM category mismatch: 0
- BOM header quantity mismatch: 0
- BOM line UoM category mismatch: 0
- BOM line quantity not matching UoM rounding: 122
- Stock quant mismatch: 0
- Open stock move mismatch: 0
- Open stock move line mismatch: 0
- Open MO quantity mismatch: 0
- Orderpoint quantity mismatch: 0

## Effective Precision Control
- sale: 2
- purchase: 3
- mrp: 6
- account: 2
- expense: 2
- stock: 6
- product: 6

## UoM Usage
| Category | UoM | Rounding | Stock Products | Purchase Products |
|---|---|---:|---:|---:|
| Length / Distance | km | 0.01 | 3 | 3 |
| Tank | Pcs | 0.01 | 243 | 243 |
| Tank | ROLL | 0.01 | 1 | 1 |
| Tank | Set | 0.01 | 2 | 2 |
| Tank | Unit | 0.01 | 392 | 392 |
| Volume | Liters | 0.01 | 39 | 39 |
| Weight | Kgs | 0.01 | 40 | 40 |
| Weight | Pound | 0.01 | 1 | 1 |
| Working Time | Hours | 0.01 | 1 | 1 |

## BOM Line Issues by UoM
| UoM | Current Rounding | Issue Count | Max Decimal Places Needed | Suggested Rounding | Example Qty |
|---|---:|---:|---:|---:|---|
| Kgs | 0.01 | 59 | 6 | 0.000001 | 0.000043, 0.00052, 0.0007, 0.0015, 0.0016, 0.0017, 0.0021, 0.00279 |
| Liters | 0.01 | 54 | 4 | 0.0001 | 0.0008, 0.0011, 0.0012, 0.0038, 0.0055, 0.0085 |
| ROLL | 0.01 | 8 | 5 | 0.00001 | 0.00088, 0.00089 |
| Unit | 0.01 | 1 | 4 | 0.0001 | 0.0015 |

## BOM Line Issue Samples
| Product Code | Qty | UoM | Rounding | BOM |
|---|---:|---|---:|---|
| RM-PLA-PP-00001 | 8.792 | Kgs | 0.01 | BOM-001-64: [SM-PLS-UP-02001] ชิ้นส่วนยาดมตัวบน W02 |
| RM-PLA-PP-00001 | 8.792 | Kgs | 0.01 | BOM-001-32: [SM-PLS-UP-01001] ชิ้นส่วนยาดมตัวบน W01 |
| RM-MBS-WH-00001 | 0.108 | Kgs | 0.01 | BOM-001-32: [SM-PLS-UP-01001] ชิ้นส่วนยาดมตัวบน W01 |
| RM-PLA-PP-00001 | 13.609 | Kgs | 0.01 | BOM-003-64: [SM-PLS-LO-02001] ชิ้นส่วนยาดมตัวล่างW02 |
| RM-MBS-WH-00001 | 0.181 | Kgs | 0.01 | BOM-003-64: [SM-PLS-LO-02001] ชิ้นส่วนยาดมตัวล่างW02 |
| RM-PLA-PP-00001 | 13.609 | Kgs | 0.01 | BOM-003-32: [SM-PLS-LO-01001] ชิ้นส่วนยาดม PS ตัวล่างW01 |
| RM-MBS-WH-00001 | 0.181 | Kgs | 0.01 | BOM-003-32: [SM-PLS-LO-01001] ชิ้นส่วนยาดม PS ตัวล่างW01 |
| RM-PLA-PP-00001 | 9.385 | Kgs | 0.01 | BOM-005-64: [SM-JOI-PP-02001] ตัวต่อสี W02 ม่วง |
| RM-MBS-VL-00001 | 0.135 | Kgs | 0.01 | BOM-005-64: [SM-JOI-PP-02001] ตัวต่อสี W02 ม่วง |
| RM-PLA-PP-00001 | 9.385 | Kgs | 0.01 | BOM-005-32: [SM-JOI-PP-01001] ตัวต่อสี W01 ม่วง |
| RM-MBS-VL-00001 | 0.135 | Kgs | 0.01 | BOM-005-32: [SM-JOI-PP-01001] ตัวต่อสี W01 ม่วง |
| RM-PLA-PP-00001 | 9.385 | Kgs | 0.01 | BOM-006-64: [SM-JOI-PK-02001] ตัวต่อสี W02 ชมพู |
| RM-MBS-PK-00002 | 0.135 | Kgs | 0.01 | BOM-006-64: [SM-JOI-PK-02001] ตัวต่อสี W02 ชมพู |
| RM-PLA-PP-00001 | 9.385 | Kgs | 0.01 | BOM-006-32: [SM-JOI-PK-01001] ตัวต่อสี W01 ชมพู |
| RM-MBS-PK-00002 | 0.135 | Kgs | 0.01 | BOM-006-32: [SM-JOI-PK-01001] ตัวต่อสี W01 ชมพู |
| RM-PLA-PP-00001 | 9.385 | Kgs | 0.01 | BOM-007-64: [SM-JOI-BU-02001] ตัวต่อสี W02 ฟ้า |
| RM-MBS-BU-00001 | 0.135 | Kgs | 0.01 | BOM-007-64: [SM-JOI-BU-02001] ตัวต่อสี W02 ฟ้า |
| RM-PLA-PP-00001 | 9.385 | Kgs | 0.01 | BOM-007-32: [SM-JOI-BU-01001] ตัวต่อสี W01 ฟ้า |
| RM-MBS-BU-00001 | 0.135 | Kgs | 0.01 | BOM-007-32: [SM-JOI-BU-01001] ตัวต่อสี W01 ฟ้า |
| RM-PLA-PP-00001 | 9.385 | Kgs | 0.01 | BOM-008-64: [SM-JOI-YW-02001] ตัวต่อสี W02 เหลือง |
| RM-MBS-YL-00001 | 0.135 | Kgs | 0.01 | BOM-008-64: [SM-JOI-YW-02001] ตัวต่อสี W02 เหลือง |
| RM-PLA-PP-00001 | 9.385 | Kgs | 0.01 | BOM-008-32: [SM-JOI-YW-01001] ตัวต่อสี W01 เหลือง |
| RM-MBS-YL-00001 | 0.135 | Kgs | 0.01 | BOM-008-32: [SM-JOI-YW-01001] ตัวต่อสี W01 เหลือง |
| RM-PLA-PP-00001 | 9.385 | Kgs | 0.01 | BOM-009-64: [SM-JOI-GN-01001] ตัวต่อสี W02 เขียว |
| RM-MBS-GR-00001 | 0.135 | Kgs | 0.01 | BOM-009-64: [SM-JOI-GN-01001] ตัวต่อสี W02 เขียว |
| RM-PLA-PP-00001 | 9.385 | Kgs | 0.01 | BOM-009-32: [SM-JOI-GR-02001] ตัวต่อสี W01 เขียว |
| RM-MBS-GR-00001 | 0.135 | Kgs | 0.01 | BOM-009-32: [SM-JOI-GR-02001] ตัวต่อสี W01 เขียว |
| SO-PSS-UP-01001 | 0.0008 | Liters | 0.01 | BOM-016: [RM-FIL-PS-01004] ก้นกรองชุบน้ำยา PS |
| SO-PSS-LO-01001 | 0.0011 | Liters | 0.01 | BOM-017: [FG-PSS-TH-04001] ยาดมโป๊ยเซียนชมพูสะท้อนแสง |
| SO-PSS-LO-01001 | 0.0011 | Liters | 0.01 | BOM-018: [FG-PSS-TH-04002] ยาดมโป๊ยเซียนม่วง |
| SO-PSS-LO-01001 | 0.0012 | Liters | 0.01 | BOM-019: [FG-PSS-TH-04003] ยาดมโป๊ยเซียนชมพู |
| SO-PSS-LO-01001 | 0.0011 | Liters | 0.01 | BOM-020: [FG-PSS-TH-04004] ยาดมโป๊ยเซียนฟ้า |
| SO-PSS-LO-01001 | 0.0011 | Liters | 0.01 | BOM-021: [FG-PSS-TH-04005] ยาดมโป๊ยเซียนเหลือง |
| SO-PSS-LO-01001 | 0.0011 | Liters | 0.01 | BOM-022: [FG-PSS-TH-04006] ยาดมโป๊ยเซียนเขียว |
| RM-PET-RO-00001 | 0.0122 | Kgs | 0.01 | BOM-023: [FG-PSS-TH-03001] ยาดมโป๊ยเซียนแผง |
| PK-SHF-PS-01003 | 0.00089 | ROLL | 0.01 | [FG-PSS-TH-02001] ยาดมโป๊ยเซียนกล่อง 5 โหล  |
| PK-SHF-PS-01006 | 0.004 | Kgs | 0.01 | [FG-PSS-TH-02003] ยาดมโป๊ยเซียนกล่อง 2 โหล หุ้ม |
| PK-SHF-PS-01004 | 0.004 | Kgs | 0.01 | [FG-PSS-TH-02004] ยาดมโป๊ยเซียนถุงโหล |
| SO-PSS-LO-01001 | 0.0011 | Liters | 0.01 | [FG-PSS-MY-04001] ยาดมโป๊ยเซียนสีชมพูสะท้อนแสง มาเลเซีย |
| SO-PSS-LO-01001 | 0.0011 | Liters | 0.01 | [FG-PSS-MY-04002] ยาดมโป๊ยเซียนสีม่วง มาเลเซีย |
| SO-PSS-LO-01001 | 0.0011 | Liters | 0.01 | [FG-PSS-MY-04003] ยาดมโป๊ยเซียนชมพู มาเลเซีย |
| SO-PSS-LO-01001 | 0.0011 | Liters | 0.01 | [FG-PSS-MY-04004] ยาดมโป๊ยเซียนฟ้า มาเลเซีย |
| SO-PSS-LO-01001 | 0.0011 | Liters | 0.01 | [FG-PSS-MY-04005] ยาดมโป๊ยเซียนเหลือง มาเลเซีย |
| SO-PSS-LO-01001 | 0.0011 | Liters | 0.01 | [FG-PSS-MY-04006] ยาดมโป๊ยเซียนเขียว มาเลเซีย |
| PK-SHF-PS-01003 | 0.00089 | ROLL | 0.01 | [FG-PSS-MY-02001] ยาดมโป๊ยเซียน 5โหล มาเลเซีย |
| PK-SHF-PS-01003 | 0.00089 | ROLL | 0.01 | [FG-PSS-MM-02001] ยาดมโป๊ยเซียน 5โหล พม่า |
| SO-PSS-LO-01001 | 0.0011 | Liters | 0.01 | [FG-PSS-DE-04001] ยาดมโป๊ยเซียนสีชมพูสะท้อนแสง เยอรมัน |
| SO-PSS-LO-01001 | 0.0011 | Liters | 0.01 | [FG-PSS-DE-04002] ยาดมโป๊ยเซียนสีม่วง เยอรมัน |
| SO-PSS-LO-01001 | 0.0011 | Liters | 0.01 | [FG-PSS-DE-04003] ยาดมโป๊ยเซียนชมพู เยอรมัน |
| SO-PSS-LO-01001 | 0.0011 | Liters | 0.01 | [FG-PSS-DE-04004] ยาดมโป๊ยเซียนฟ้า เยอรมัน |
| SO-PSS-LO-01001 | 0.0011 | Liters | 0.01 | [FG-PSS-DE-04005] ยาดมโป๊ยเซียนเหลือง เยอรมัน |
| SO-PSS-LO-01001 | 0.0011 | Liters | 0.01 | [FG-PSS-DE-04006] ยาดมโป๊ยเซียนเขียว เยอรมัน |
| PK-SHF-PS-01003 | 0.00089 | ROLL | 0.01 | [FG-PSS-DE-02001] ยาดมโป๊ยเซียน 5โหล เยอรมัน |
| SO-PSS-LO-01001 | 0.0011 | Liters | 0.01 | [FG-PSK-TH-03001] ยาดมโป๊ยเซียนพวงกุญแจ สีชมพูสะท้อนแสง |
| SO-PSS-LO-01001 | 0.0011 | Liters | 0.01 | [FG-PSK-TH-03002] ยาดมโป๊ยเซียนพวงกุญแจ สีม่วง |
| SO-PSS-LO-01001 | 0.0011 | Liters | 0.01 | [FG-PSK-TH-03003] ยาดมโป๊ยเซียนพวงกุญแจ สีชมพู |
| SO-PSS-LO-01001 | 0.0011 | Liters | 0.01 | [FG-PSK-TH-03004] ยาดมโป๊ยเซียนพวงกุญแจ สีฟ้า |
| SO-PSS-LO-01001 | 0.0011 | Liters | 0.01 | [FG-PSK-TH-03005] ยาดมโป๊ยเซียนพวงกุญแจ สีเหลือง |
| SO-PSS-LO-01001 | 0.0012 | Liters | 0.01 | [FG-PSK-TH-03006] ยาดมโป๊ยเซียนพวงกุญแจ สีเขียว |
| PK-SHF-PS-01003 | 0.00089 | ROLL | 0.01 | [FG-PSK-TH-02001] ยาดมโป๊ยเซียนพวงกุญแจ กล่อง 5โหล |
| SO-MTS-XX-01001 | 0.0011 | Liters | 0.01 | [FG-MTS-XX-04001] ยาดม Mark II สีชมพูสะท้อนแสง |
| SO-MTS-XX-01001 | 0.0011 | Liters | 0.01 | [FG-MTS-XX-04002] ยาดม Mark II สีม่วง |
| SO-MTS-XX-01001 | 0.0011 | Liters | 0.01 | [FG-MTS-XX-04003] ยาดม Mark II สีชมพู |
| SO-MTS-XX-01001 | 0.0011 | Liters | 0.01 | [FG-MTS-XX-04004] ยาดม Mark II สีฟ้า |
| SO-MTS-XX-01001 | 0.0011 | Liters | 0.01 | [FG-MTS-XX-04005] ยาดม Mark II สีเหลือง |
| SO-MTS-XX-01001 | 0.0011 | Liters | 0.01 | [FG-MTS-XX-04006] ยาดม Mark II สีเขียว |
| PK-SHF-PS-01003 | 0.00089 | ROLL | 0.01 | [FG-MTS-XX-02001] ยาดม Mark II กล่อง 5 โหล (หุ้ม) |
| PK-SHF-PS-01003 | 0.00089 | ROLL | 0.01 | [FG-MTS-GH-02001] ยาดม Mark II กล่อง 5 โหล กาน่า(หุ้ม) |
| SO-MTS-XX-01001 | 0.0011 | Liters | 0.01 | [FG-MTS-TW-02001] ยาดม Mark II ไต้หวัน สีชมพูสะท้อนแสง |
| SO-MTS-XX-01001 | 0.0011 | Liters | 0.01 | [FG-MTS-TW-02002] ยาดม Mark II ไต้หวัน สีม่วง |
| SO-MTS-XX-01001 | 0.0011 | Liters | 0.01 | [FG-MTS-TW-02003] ยาดม Mark II ไต้หวัน สีชมพู |
| SO-MTS-XX-01001 | 0.0011 | Liters | 0.01 | [FG-MTS-TW-02004] ยาดม Mark II ไต้หวัน สีฟ้า |
| SO-MTS-XX-01001 | 0.0011 | Liters | 0.01 | [FG-MTS-TW-02005] ยาดม Mark II ไต้หวัน สีเหลือง |
| SO-MTS-XX-01001 | 0.0011 | Liters | 0.01 | [FG-MTS-TW-02006] ยาดม Mark II ไต้หวัน สีเขียว |
| SO-MTS-XX-01001 | 0.0011 | Liters | 0.01 | [FG-MTK-IL-04001] ยาดม Mark II อิสราเอล |
| PK-SHF-PS-01007 | 0.00279 | Kgs | 0.01 | [FG-MTK-IL-02001] ยาดม Mark II อิสราเอล 1 กล่อง |
| PK-SHF-PN-01004 | 0.0016 | Kgs | 0.01 | d3: [FG-PNF-ID-02001] พิมเสน แก้วแบน 3cc 1โหล อินโดนีเซีย |
| SO-PNS-XX-01001 | 0.0055 | Liters | 0.01 | d2: [FG-PNR-ID-04001] พิมเสนโรลออน 5cc ไม่หุ้ม อินโดนีเซีย |
| PK-SHF-PN-02001 | 0.0015 | Kgs | 0.01 | d2: [FG-PNR-ID-02001] พิมเสนโรลออน 5cc 1โหล อินโดนีเซีย |
| SO-PNS-XX-01001 | 0.0085 | Liters | 0.01 | d1: [FG-PNC-ID-04001] พิมเสนสำลี 8cc ไม่หุ้ม อินโดนีเซีย |

## Recommendation
- Current transactional data is clean: no stock quant, open stock move, open stock move line, open MO, or orderpoint currently violates UoM rounding.
- Master data is not fully aligned: BOM line quantities require more precision than current UoM rounding for Kgs, Liters, ROLL, and Unit.
- Recommended DB changes before heavy UAT: Kgs to 0.000001, Liters to 0.0001, ROLL to 0.00001, Unit to 0.0001 only if Unit is intentionally fractional.
- Keep Pcs at 0.01 for this implementation if fractional piece quantities can occur from BOM scaling; use 1.0 only if the business wants to block all fractional pieces.
- Precision Control display settings are effectively 6 digits for MRP/Stock/Product because the code takes max(config, Product Unit of Measure decimal precision). This display setting does not replace UoM rounding validation.