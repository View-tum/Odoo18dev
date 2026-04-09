# Mold / GMP Shop Floor UAT Test - 2026-04-06

Database: `uat`
Server: `http://localhost:8811`

## Summary
- Passed: `5`
- Passed with note: `1`
- Not closed: `1`

## Result by case
- `MU14-01` Passed: card shows mold name and shots
- `MU14-02` Passed: mold changed from card and backend updated
- `MU14-03` Passed: full mold warning + Continue Anyway
- `MU14-04` Passed: full mold warning + Change Mold + Start
- `MU14-05` Passed: reset mold life in UI
- `MU14-06` Passed with note: Stop/recovery path works, but no dedicated breakdown button on card
- `MU14-07` Not closed: no suitable UAT sample to sign off done/cancel sibling behavior end-to-end in UI

## Cleanup state
- WO 363: Ready / mold 590
- WO 364: Ready / mold 650
- Mold 590: `1000/1000`
- Mold 650: `0/1000`
