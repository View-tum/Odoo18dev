# Local UAT MANU Assessment

Workbook: `UAT_GoldMints_Test Scenario_MANU.xlsx`
Database: `uat` on local Odoo (`localhost:8811`) 

## Coverage Summary

- Total `Product_backlog` items: `60`
- Backlog items linked to MU test cases: `15`
- Backlog items not linked to any MU test case: `45`
- Total MU test cases in workbook: `51`
- MU test cases with local UAT evidence: `17`
- Product_backlog design coverage: `25.00%`
- Case-level local evidence coverage: `33.33%`

## Key Finding

The workbook does **not** fully cover `Product_backlog`. Only 15 of 60 backlog IDs are mapped into MU cases. The remaining 45 backlog IDs currently have no detailed MU test step linked to them.

## MU Cases With Local UAT Evidence

- `MU01-01`: `Passed`
  Note: Verified from local UAT product form + forecast report for FG-PNC-TH-01001. User can read On Hand, Forecasted, and linked moves.
  Evidence: reports/manu_uat_20260406_mu01_mu04_images/MU01_01_product_search.png; MU01_01_product_form.png; MU01_01_forecast_report.png
- `MU01-02`: `Passed with note`
  Note: Verified from local UAT replenishment and product route screenshots for FG-PSS-TH-01005. Review used existing live records and did not trigger new replenishment documents.
  Evidence: reports/manu_uat_20260406_mu01_mu04_images/MU01_02_replenishment_fg_pss.png; MU01_02_product_route_fg_pss.png
- `MU01-03`: `Passed with note`
  Note: Verified from existing local UAT MO trace for FG-PNC-TH-01001. Review confirms replenishment path reaches Manufacturing Pharma. This was traced from existing document, not by generating a brand new procurement run.
  Evidence: reports/manu_uat_20260406_mu01_mu04_images/MU01_03_mo_created_fg_pnc.png
- `MU04-03`: `Passed`
  Note: Late backorder recovery verified on local UAT for Transfer Pharma. After user selected No Backorder, Create Backorder became available and recreated the missing picking.
  Evidence: reports/late_backorder_recovery_uat_test_20260403_final.json
- `MU07-03`: `Passed`
  Note: Late backorder recovery verified on local UAT for Manufacturing Pharma. MO remained done, and Create Backorder recreated the remaining production quantity.
  Evidence: reports/late_backorder_recovery_uat_test_20260403_final.json
- `MU08-01`: `Passed with note`
  Note: Scrap flow is verified on local UAT through shell-driven scenarios: scrap wizard product restriction, same-location replenish, internal-transfer replenish, and scrap landed cost finalization. Coverage is technical/business-flow level rather than a pure manual UI walkthrough.
  Evidence: reports/shopfloor_auto_uat_suite_20260406.json; reports/mrp_scrap_landed_cost_uat_20260406.json
- `MU09-01`: `Passed`
  Note: Auto assignment of mold and workcenter verified in local UAT. Mold matrix assigned compatible mold and computed expected duration.
  Evidence: reports/shopfloor_auto_uat_suite_20260406.json
- `MU09-02`: `Passed`
  Note: Parallel mold guard verified in local UAT. Duplicate mold usage across sibling workorders was prevented.
  Evidence: reports/shopfloor_auto_uat_suite_20260406.json
- `MU09-03`: `Passed with note`
  Note: Local UAT verifies qty logs aggregation and labor cost calculation. Reject-qty capture was not separately signed off in this evidence set, so this case is treated as pass with note.
  Evidence: reports/shopfloor_auto_uat_suite_20260406.json
- `MU11-04`: `Passed`
  Note: Plastic GMP Shop Floor flow with mold and workcenter verified directly in UI on local UAT.
  Evidence: reports/mold_shopfloor_uat_test_20260406.json; reports/mold_shopfloor_uat_full_20260406.json
- `MU14-01`: `Passed`
  Note: Card shows mold name and shot counter.
  Evidence: reports/mold_shopfloor_uat_test_20260406.json; reports/mold_shopfloor_uat_20260406_images/02_mold_card.png
- `MU14-02`: `Passed`
  Note: Change mold from card before start.
  Evidence: reports/mold_shopfloor_uat_test_20260406.json; reports/mold_shopfloor_uat_20260406_images/06_change_mold_dialog.png; reports/mold_shopfloor_uat_20260406_images/07_change_mold_result.png
- `MU14-03`: `Passed`
  Note: Full mold warning with Continue Anyway.
  Evidence: reports/mold_shopfloor_uat_test_20260406.json; reports/mold_shopfloor_uat_20260406_images/03_full_mold_warning.png; reports/mold_shopfloor_uat_20260406_images/04_continue_anyway_started.png
- `MU14-04`: `Passed`
  Note: Full mold warning with Change Mold then Start.
  Evidence: reports/mold_shopfloor_uat_test_20260406.json; reports/mold_shopfloor_uat_20260406_images/08_change_from_warning_result.png; reports/mold_shopfloor_uat_20260406_images/09_changed_mold_started.png
- `MU14-05`: `Passed`
  Note: Reset mold life after maintenance.
  Evidence: reports/mold_shopfloor_uat_test_20260406.json; reports/mold_shopfloor_uat_20260406_images/10_reset_life_result.png
- `MU14-06`: `Passed with note`
  Note: Breakdown recovery path is usable from Shop Floor via More > Report Issue and stop/recovery behavior. There is still no dedicated breakdown button on the card.
  Evidence: reports/mold_shopfloor_uat_test_20260406.json; reports/mold_shopfloor_uat_20260406_images/11_more_menu_report_issue.png
- `MU14-07`: `Not closed`
  Note: No suitable local UAT sample was available to sign off done/cancel sibling queue behavior end-to-end in UI.
  Evidence: reports/mold_shopfloor_uat_test_20260406.json

## Backlog IDs Not Covered By Any MU Case

`MA05`, `MA09`, `MA19`, `MA20`, `MA21`, `MA22`, `MA23`, `MA24`, `MA25`, `MA26`, `MA27`, `MA28`, `MA29`, `MA30`, `MA31`, `MA32`, `MA33`, `MA34`, `MA35`, `MA36`, `MA37`, `MA38`, `MA39`, `MA40`, `MA41`, `MA42`, `MA43`, `MA44`, `MA45`, `MA46`, `MA47`, `MA48`, `MA49`, `MA50`, `MA51`, `MA52`, `MA53`, `MA54`, `MA55`, `MAXX`, `RP41`, `RP42`, `RP68`, `RP69`, `RP70`

## Backlog IDs Already Touched By Local UAT Evidence

`MA01`, `MA02`, `MA04`, `MA06`, `MA07`, `MA08`, `MA10`, `MA11`, `MA13`, `MA14`, `MA16`, `MA17`, `MA18`