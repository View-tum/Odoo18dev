# UAT14 MANU Rounding Update Result

Database: `goldmints_uat_manu`

## Updated UoM Rounding
| UoM | Category | Before | After | Status |
|---|---|---:|---:|---|
| Kgs | Weight | 0.01 | 1e-06 | updated |
| Liters | Volume | 0.01 | 0.0001 | updated |
| ROLL | Tank | 0.01 | 1e-05 | updated |
| Unit | Tank | 0.01 | 0.0001 | updated |

## Audit Before vs After
| Check | Before | After |
|---|---:|---:|
| Invalid UoM rounding/factor | 0 | 0 |
| Product UoM category mismatch | 0 | 0 |
| BOM header qty mismatch | 0 | 0 |
| BOM line UoM category mismatch | 0 | 0 |
| BOM line qty not multiple of rounding | 122 | 0 |
| Stock quant mismatch | 0 | 0 |
| Open stock move mismatch | 0 | 0 |
| Open stock move line mismatch | 0 | 0 |
| Open MO mismatch | 0 | 0 |
| Orderpoint mismatch | 0 | 0 |

## Current Selected UoM
| UoM | Category | Rounding | Stock Products | Purchase Products |
|---|---|---:|---:|---:|
| Pcs | Tank | 0.01 | 243 | 243 |
| ROLL | Tank | 1e-05 | 1 | 1 |
| Unit | Tank | 0.0001 | 392 | 392 |
| Liters | Volume | 0.0001 | 39 | 39 |
| Kgs | Weight | 1e-06 | 40 | 40 |
| Pcs | Weight | 0.01 | 0 | 0 |

## Conclusion
- Rounding master data is now aligned with current BOM decimal quantities.
- The previous 122 BOM line rounding issues are cleared.
- No current stock quant, open move, open move line, open MO, or orderpoint violates UoM rounding after the update.
- Pcs remains 0.01; it was not changed because current implementation uses fractional pieces in some manufacturing scaling flows.