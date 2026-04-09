# Manufacturing / Shopfloor Auto UAT Suite

- Date: 2026-04-06
- Database: uat
- Scope: manufacturing_shopfloor_auto

## Summary

- Shell cases: 14
- Reference UI cases: 10
- Total cases: 24
- Passed: 24
- Failed: 0
- Overall OK: True

## Shell Cases

### AUTO-01 - custom auto modules installed
- Status: passed
- Result: `{"modules": {"mrp_parallel_console": true, "mrp_mold_management": true, "mrp_scrap_auto_replenish": true, "mrp_workcenter_lock": true, "late_backorder_recovery": true, "mrp_scrap_finished_Good": true}}`

### AUTO-02 - workcenter lock blocks second start on same machine
- Status: passed
- Result: `{"workcenter": "TMP LOCK WC", "first_workorder": "TMP LOCK WC - LOCK OP", "second_workorder": "TMP LOCK WC - LOCK OP 2", "block_message": "ไม่สามารถเริ่มงานได้ เนื่องจาก Work Center นี้กำลังทำงานอยู่แล้ว\n\nWork Center: TMP LOCK WC\nWork Order ที่กำลังทำงาน: TMP LOCK WC - LOCK OP\n\nกรุณาจบหรือหยุดงานเดิมก่อนเริ่มงานใหม่บนเครื่องนี้."}`

### AUTO-03 - parallel split distributes planned qty by capacity
- Status: passed
- Result: `{"mo": "TMP PAR SPLIT MO", "workorders": [{"name": "TMP PAR FAST - PAR SPLIT OP", "workcenter": "TMP PAR FAST", "planned_qty": 6.0}, {"name": "TMP PAR SLOW - PAR SPLIT OP", "workcenter": "TMP PAR SLOW", "planned_qty": 3.0}]}`

### AUTO-04 - mold matrix auto-assigns mold and duration
- Status: passed
- Result: `{"mo": "TMP MOLD MO", "workorder": "TMP MOLD MACHINE - MOLD OP (TMP MOLD TOOL)", "assigned_mold": "TMP MOLD TOOL", "duration_expected": 2.5}`

### AUTO-05 - parallel mold guard prevents duplicate mold usage
- Status: passed
- Result: `{"mo": "TMP GUARD MO", "active_workorders": [{"name": "TMP GUARD A - GUARD OP (TMP GUARD MOLD)", "state": "ready", "molds": ["TMP GUARD MOLD"]}], "cancelled_workorders": [{"name": "TMP GUARD B - GUARD OP", "state": "cancel"}]}`

### AUTO-06 - mold UI helper shows only on mold-capable workorders
- Status: passed
- Result: `{"mold_workorder": "TMP UI MOLD MACHINE - UI MOLD OP (TMP UI MOLD TOOL)", "mold_ui": true, "plain_workorder": "TMP UI PLAIN MACHINE - UI PLAIN OP", "plain_ui": false}`

### AUTO-07 - console timer and qty logs aggregate effective quantity
- Status: passed
- Result: `{"workorder": "TMP TIMER WC - TIMER OP", "start": "2026-04-06 10:13:24", "stop": "2026-04-06 10:13:24", "effective_qty": 5.0}`

### AUTO-08 - employee cost total computes from productivity logs
- Status: passed
- Result: `{"mo": "TMP LABOR MO", "employee_cost_total": 120.0}`

### AUTO-09 - overproduction sync updates MO and component demand
- Status: passed
- Result: `{"mo": "TMP OVER MO", "new_product_qty": 12.0, "new_component_qty": 12.0}`

### AUTO-10 - scrap wizard limits products to MO raw and finished goods
- Status: passed
- Result: `{"workorder": "TMP SCRAP WC - SCRAP OP", "allowed_product_ids": [9089, 9090]}`

### AUTO-11 - scrap auto-replenish uses same-location stock when available
- Status: passed
- Result: `{"mo": "TMP SCRAP SAME MO", "raw_move_qty": 7.0, "scrap_id": 5}`

### AUTO-12 - scrap auto-replenish creates internal transfer when source is short
- Status: passed
- Result: `{"mo": "TMP SCRAP INT MO", "raw_move_qty": 7.0, "replenishment_picking": "GMP/TRPH/00022"}`

### AUTO-13 - late backorder recovery recreates stock picking backorder
- Status: passed
- Result: `{"original_picking": "GMP/TRPH/00023", "late_backorder": "GMP/TRPH/00024", "late_qty": 6.0}`

### AUTO-14 - late backorder recovery recreates MO backorder
- Status: passed
- Result: `{"original_mo": "TMP LATE BO MO", "late_backorder_mo": "TMP LATE BO MO-001", "late_qty": 6.0}`

## Reference UI Cases

### UI-MOLD-01 - dashboard loads mold jobs
- Status: passed
- Source: `reports\mold_shopfloor_uat_full_20260406.json`
- Evidence: reports/mold_shopfloor_uat_20260406_images/01_dashboard.png

### UI-MOLD-02 - mold card shows mold and shots
- Status: passed
- Source: `reports\mold_shopfloor_uat_full_20260406.json`
- Evidence: reports/mold_shopfloor_uat_20260406_images/02_mold_card.png

### UI-MOLD-03 - full mold warning appears on start
- Status: passed
- Source: `reports\mold_shopfloor_uat_full_20260406.json`
- Evidence: reports/mold_shopfloor_uat_20260406_images/03_full_mold_warning.png

### UI-MOLD-04 - continue anyway starts workorder
- Status: passed
- Source: `reports\mold_shopfloor_uat_full_20260406.json`
- Evidence: reports/mold_shopfloor_uat_20260406_images/04_continue_anyway_started.png

### UI-MOLD-05 - change mold dialog opens from card
- Status: passed
- Source: `reports\mold_shopfloor_uat_full_20260406.json`
- Evidence: reports/mold_shopfloor_uat_20260406_images/06_change_mold_dialog.png

### UI-MOLD-06 - selecting mold from card updates card
- Status: passed
- Source: `reports\mold_shopfloor_uat_full_20260406.json`
- Evidence: reports/mold_shopfloor_uat_20260406_images/07_change_mold_result.png

### UI-MOLD-07 - change mold from warning and start with alternative mold
- Status: passed
- Source: `reports\mold_shopfloor_uat_full_20260406.json`
- Evidence: reports/mold_shopfloor_uat_20260406_images/08_change_from_warning_result.png, reports/mold_shopfloor_uat_20260406_images/09_changed_mold_started.png

### UI-MOLD-08 - reset life resets shots to zero
- Status: passed
- Source: `reports\mold_shopfloor_uat_full_20260406.json`
- Evidence: reports/mold_shopfloor_uat_20260406_images/10_reset_life_result.png

### UI-MOLD-09 - non-mold workcenter hides mold UI
- Status: passed
- Source: `reports\mold_shopfloor_uat_full_20260406.json`
- Evidence: reports/mold_shopfloor_uat_20260406_images/05_non_mold_card_hidden.png

### UI-MOLD-10 - breakdown entry point available under More menu
- Status: passed
- Source: `reports\mold_shopfloor_uat_full_20260406.json`
- Evidence: reports/mold_shopfloor_uat_20260406_images/11_more_menu_report_issue.png
