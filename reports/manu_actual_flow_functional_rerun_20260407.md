# Local UAT Manufacturing Functional Rerun

- Database: `uat`
- Date tag: `20260407`
- Passed: `17/18`

## F01 - MTS shortage creates MO
- Phase: `01_??????????????????????????????????????????????????????`
- MU IDs: `MU06-01`
- Status: `passed`
- Result:
```json
{
  "case": "mts_min_max_live",
  "pass": true,
  "orderpoint_id": 175,
  "original_rule": {
    "product_min_qty": 0.0,
    "product_max_qty": 0.0,
    "qty_multiple": 1.0,
    "trigger": "auto"
  },
  "replenish_target_level": 100371.0,
  "qty_on_hand_before": 100121.0,
  "qty_forecast_before": 100121.0,
  "qty_on_hand_after": 100371.0,
  "qty_forecast_after": 100371.0,
  "mo_names_after_replenish": [
    "GMP/MOPH/00044"
  ],
  "completed_mos": [
    "GMP/MOPH/00044"
  ],
  "pickings_after_run": [],
  "costing": [
    {
      "mo_name": "GMP/MOPH/00044",
      "product_code": "FG-PNC-TH-01001",
      "state": "done",
      "product_qty": 250.0,
      "finished_qty": 250.0,
      "cost_method": "fifo",
      "valuation": "real_time",
      "standard_price_before": 0.1929,
      "standard_price_after": 0.1956,
      "raw_cost_total": 0.0,
      "labor_cost_total": 0.0,
      "mold_cost_total": 0.0,
      "employee_cost_total": 0.0,
      "mold_cost_field_total": 0.0,
      "finished_value_total": 316.0783,
      "actual_unit_cost": 1.2643,
      "calculated_total_cost": 0.0,
      "valuation_variance": 316.0783,
      "valuation_logic_ok": false,
      "journal_entries": [
        "STJ/26/04/27337"
      ],
      "labor_move": false,
      "mold_move": false
    }
  ]
}
```

## F02 - MTS enough stock creates no document
- Phase: `01_??????????????????????????????????????????????????????`
- MU IDs: `MU06-02`
- Status: `passed`
- Result:
```json
{
  "product": "TMP MTS ENOUGH FG",
  "qty_available": 10.0,
  "orderpoint_min": 5.0,
  "orderpoint_max": 5.0
}
```

## F03 - MTS child chain creates child MOs and transfers
- Phase: `01_??????????????????????????????????????????????????????`
- MU IDs: `MU06-03, MU02-03`
- Status: `failed`
- Error: `Expected child MOs for deep MTS chain.`

## F04 - Manual MO full flow closes successfully
- Phase: `02_?????????????????????????????????`
- MU IDs: `MU02-01, MU07-01`
- Status: `passed`
- Result:
```json
{
  "mo": "TMP ACTUAL MO",
  "state": "done",
  "product_qty": 5.0,
  "raw_required_qty": 10.0,
  "raw_done_qty": 10.0,
  "finished_moves": [
    "TMP ACTUAL MO"
  ],
  "workorders": [
    {
      "name": "TMP ACTUAL MO WC - ACTUAL MO OP",
      "state": "done",
      "qty_produced": 5.0
    }
  ]
}
```

## F05 - Manual MO with partial materials stays short
- Phase: `02_?????????????????????????????????`
- MU IDs: `MU02-02`
- Status: `passed`
- Result:
```json
{
  "mo": "TMP PARTIAL MAT MO",
  "state": "confirmed",
  "raw_required_qty": 10.0,
  "raw_reserved_qty": 4.0,
  "forecast_availability": -6.0,
  "reservation_state": "partially_available"
}
```

## F06 - MTO sales flow creates and completes supply
- Phase: `02_?????????????????????????????????`
- MU IDs: `MU05-01`
- Status: `passed`
- Result:
```json
{
  "case": "local_mto_full",
  "pass": false,
  "order": {
    "name": "SOD-263066",
    "state": "sale",
    "invoice_status": "to invoice",
    "amount_total": 0.0,
    "pickings": [
      "GMP/PICK/03587",
      "GMP/OUT/02509"
    ],
    "invoices": []
  },
  "invoice": {},
  "mo_names_after_confirm": [],
  "completed_mos": [],
  "pickings_after_confirm": [
    {
      "name": "GMP/PICK/03587",
      "type": "internal",
      "state": "done"
    }
  ],
  "pickings_after_processing": [
    {
      "name": "GMP/PICK/03587",
      "type": "internal",
      "state": "done"
    },
    {
      "name": "GMP/OUT/02509",
      "type": "outgoing",
      "state": "done"
    }
  ],
  "done_pickings": [
    "GMP/PICK/03587",
    "GMP/OUT/02509"
  ],
  "sale_line_delivery": [
    {
      "product": "FG-MTK-IL-01001",
      "qty_ordered": 1.0,
      "qty_delivered": 1.0,
      "qty_invoiced": 0.0,
      "is_foc": false
    }
  ],
  "cogs_accounts": [],
  "foc_expected_account": "600005",
  "foc_expected_account_used": false,
  "costing": [],
  "notes": [
    "Invoice must be auto-created and auto-posted after delivery.",
    "Costing is reported from the real MOs created by the sales flow."
  ]
}
```

## F07 - MTO shortage traces upstream purchase supply
- Phase: `02_?????????????????????????????????`
- MU IDs: `MU05-02`
- Status: `passed`
- Result:
```json
{
  "order": "SOD-263067",
  "mo_names": [
    "GMP/MOPH/00045"
  ],
  "po_names": [
    "P00026"
  ],
  "component": "TMP MTO BUY COMP"
}
```

## F08 - Transfer Plastic full
- Phase: `03_??????????????????Backorder`
- MU IDs: `MU03-01`
- Status: `passed`
- Result:
```json
{
  "picking": "GMP/TRPL/00022",
  "state": "done"
}
```

## F09 - Transfer Plastic partial standard backorder
- Phase: `03_??????????????????Backorder`
- MU IDs: `MU03-02`
- Status: `passed`
- Result:
```json
{
  "original_picking": "GMP/TRPL/00023",
  "backorder": "GMP/TRPL/00024",
  "backorder_qty": 6.0
}
```

## F10 - Transfer Plastic late backorder recovery
- Phase: `03_??????????????????Backorder`
- MU IDs: `MU03-03`
- Status: `passed`
- Result:
```json
{
  "original_picking": "GMP/TRPL/00025",
  "late_backorder": "GMP/TRPL/00026",
  "late_qty": 6.0
}
```

## F11 - Transfer Pharma full
- Phase: `03_??????????????????Backorder`
- MU IDs: `MU04-01`
- Status: `passed`
- Result:
```json
{
  "picking": "GMP/TRPH/00041",
  "state": "done"
}
```

## F12 - Transfer Pharma partial standard backorder
- Phase: `03_??????????????????Backorder`
- MU IDs: `MU04-02`
- Status: `passed`
- Result:
```json
{
  "original_picking": "GMP/TRPH/00042",
  "backorder": "GMP/TRPH/00043",
  "backorder_qty": 6.0
}
```

## F13 - Transfer Pharma late backorder recovery
- Phase: `03_??????????????????Backorder`
- MU IDs: `MU04-03`
- Status: `passed`
- Result:
```json
{
  "original_picking": "GMP/TRPH/00044",
  "late_backorder": "GMP/TRPH/00045",
  "late_qty": 6.0
}
```

## F14 - MO partial standard backorder
- Phase: `05_??????????????????????????????????????????`
- MU IDs: `MU07-02`
- Status: `passed`
- Result:
```json
{
  "original_mo": "GMP/MOPH/00046-001",
  "backorder_mo": "GMP/MOPH/00046-001",
  "backorder_qty": 4.0
}
```

## F15 - Overproduction sync updates demand
- Phase: `05_??????????????????????????????????????????`
- MU IDs: `MU07-04`
- Status: `passed`
- Result:
```json
{
  "mo": "TMP OVER MO",
  "new_product_qty": 12.0,
  "new_component_qty": 12.0
}
```

## F16 - Return leftovers from staging to stock
- Phase: `05_??????????????????????????????????????????`
- MU IDs: `MU08-02`
- Status: `passed`
- Result:
```json
{
  "picking": "GMP/TRPH/00046",
  "source": "GMP/Stock/คลังลอย",
  "destination": "GMP/Stock"
}
```

## F17 - Stock movement trace from MO raw to FG
- Phase: `07_????????????????????????????????????UoM`
- MU IDs: `MU10-02`
- Status: `passed`
- Result:
```json
{
  "mo": "TMP TRACE MO",
  "raw_moves": [
    {
      "name": "TMP TRACE MO",
      "qty": 6.0,
      "state": "done"
    }
  ],
  "finished_moves": [
    {
      "name": "TMP TRACE MO",
      "qty": 2.0,
      "state": "done"
    }
  ],
  "from_manual_flow": "TMP ACTUAL MO"
}
```

## F18 - BOM demand equals actual component demand on MO
- Phase: `07_????????????????????????????????????UoM`
- MU IDs: `MU10-03`
- Status: `passed`
- Result:
```json
{
  "mo": "GMP/MOPH/00047",
  "bom_component_per_unit": 2.0,
  "fg_qty": 3.0,
  "expected_component_qty": 6.0,
  "move_component_qty": 6.0
}
```
