# GMP Shop Floor Mold UAT Report

Date: 2026-04-06
Environment: `uat`
URL: `http://localhost:8811/odoo?db=uat`
Tester: Codex

## Scope

This run verifies the GMP Shop Floor mold-related UI and behavior after the latest changes:

- mold info is shown on mold-capable workorders
- mold can be changed from the card
- full-life mold warning appears on start
- user can continue anyway without being blocked
- user can switch to an alternative mold from the warning flow
- mold life can be reset from the mold form
- non-mold workcenters do not show mold UI on the card
- breakdown path entry point is available from the card `More` menu

## Test Data

- Mold warning MO: `GMP/MOPL/00011`
- Mold change MO: `GMP/MOPL/00012`
- Non-mold MO: `GMP/MOPH/00021`
- Full mold: `590` / `แม่พิมพ์พลาสติกตัวต่อสี W02`
- Alternative mold: `650` / `TEST ALT MOLD SHOPFLOOR JOI PK W02`
- Workorders:
  - `363` / `GMP/MOPL/00011`
  - `364` / `GMP/MOPL/00012`
  - `360` / `GMP/MOPH/00021`

## Result Summary

| Case | Scenario | Result | Evidence |
|---|---|---|---|
| `UI-MOLD-01` | GMP Shop Floor dashboard loads mold jobs | `PASS` | [01_dashboard.png](mold_shopfloor_uat_20260406_images/01_dashboard.png) |
| `UI-MOLD-02` | Mold workorder card shows mold name and shots | `PASS` | [02_mold_card.png](mold_shopfloor_uat_20260406_images/02_mold_card.png) |
| `UI-MOLD-03` | Full mold warning popup appears on `Start` | `PASS` | [03_full_mold_warning.png](mold_shopfloor_uat_20260406_images/03_full_mold_warning.png) |
| `UI-MOLD-04` | `Continue Anyway` starts the workorder even when mold is full | `PASS` | [04_continue_anyway_started.png](mold_shopfloor_uat_20260406_images/04_continue_anyway_started.png) |
| `UI-MOLD-05` | Mold selection dialog can be opened from the card | `PASS` | [06_change_mold_dialog.png](mold_shopfloor_uat_20260406_images/06_change_mold_dialog.png) |
| `UI-MOLD-06` | Selecting a mold from the card updates the current mold on the card | `PASS` | [07_change_mold_result.png](mold_shopfloor_uat_20260406_images/07_change_mold_result.png) |
| `UI-MOLD-07` | Switching mold from warning flow allows start with the suggested alternative mold | `PASS` | [08_change_from_warning_result.png](mold_shopfloor_uat_20260406_images/08_change_from_warning_result.png), [09_changed_mold_started.png](mold_shopfloor_uat_20260406_images/09_changed_mold_started.png) |
| `UI-MOLD-08` | `Reset Life` confirms and resets shots to zero | `PASS` | [10_reset_life_result.png](mold_shopfloor_uat_20260406_images/10_reset_life_result.png) |
| `UI-MOLD-09` | Non-mold workcenter card hides all mold UI | `PASS` | [05_non_mold_card_hidden.png](mold_shopfloor_uat_20260406_images/05_non_mold_card_hidden.png) |
| `UI-MOLD-10` | Breakdown path entry point exists via `More > Report Issue` | `PASS` | [11_more_menu_report_issue.png](mold_shopfloor_uat_20260406_images/11_more_menu_report_issue.png) |

## Detailed Notes

### UI-MOLD-01
- Opened `GMP Shop Floor > Dashboard`
- Confirmed mold test MOs are present and accessible from the dashboard cards

### UI-MOLD-02
- Opened `GMP/MOPL/00011` console
- Confirmed the card shows:
  - mold label
  - mold name
  - shot counter
  - `Mold` button

### UI-MOLD-03
- On `GMP/MOPL/00011`, clicked `Start`
- Popup appeared with:
  - current mold at full life
  - suggested alternative mold
  - actions `Cancel`, `Change Mold`, `Continue Anyway`

### UI-MOLD-04
- Clicked `Continue Anyway`
- Workorder moved to `In Progress`
- System did not block the user even though the mold was full

### UI-MOLD-05
- Opened `GMP/MOPL/00012`
- Clicked `Mold`
- Confirmed selection dialog lists compatible machine-mold combinations

### UI-MOLD-06
- From the card dialog, selected another mold
- Card updated to the newly selected mold immediately

### UI-MOLD-07
- Forced the card back to the full mold
- Clicked `Start`
- From warning popup chose `Change Mold`
- Selected the suggested alternative mold
- Card updated to alternative mold
- Clicked `Start` again
- Workorder moved to `In Progress`

### UI-MOLD-08
- Opened mold `590`
- Clicked `Reset Life`
- Confirmed popup
- Mold life reset to `0 / 1000`
- Mold status changed to `Normal`

### UI-MOLD-09
- Opened non-mold production console `GMP/MOPH/00021`
- Confirmed the card does not render:
  - mold row
  - mold button
  - mold shot counter

### UI-MOLD-10
- On mold-capable card, opened `More`
- Confirmed `Report Issue` is available as the operator entry point for breakdown/maintenance flow

## Cleanup Status

Cleanup was applied after testing:

- Workorder `363` = `ready`
- Workorder `364` = `ready`
- `console_qty` for both = `0`
- Mold `590` restored to `1000 / 1000`
- Mold `650` remains `0 / 1000`

## Overall Conclusion

All targeted shopfloor mold scenarios for this change set passed in `uat`, including the new requirement:

- mold UI shown only when relevant
- mold UI hidden for non-mold workcenters
- full-life mold warning does not block execution
- change mold flow works from both the card and the warning path
- reset life works from the mold form
