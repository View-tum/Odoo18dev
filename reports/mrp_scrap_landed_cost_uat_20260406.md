# MRP Scrap Landed Cost UAT

- Date: 2026-04-06
- Database: uat
- Status: passed

## Checks
- module_installed: `True`
- dependency_mrp_landed_costs_installed: `True`
- legacy_scrap_record_model_exists: `False`
- configured_service_product: `True`
- service_product: `{'id': 9038, 'name': 'Scarp', 'type': 'service', 'landed_cost_ok': True, 'is_scrap_cost': True}`

## Flow Test
- test_category: `{'id': 2, 'name': 'All / FG', 'valuation': 'real_time', 'cost_method': 'fifo'}`
- temporary_mo: `TMP SCRAP LC MO`
- temporary_mo_state: `done`
- temporary_scrap: `SP/00005`
- temporary_scrap_state: `done`
- temporary_scrap_landed_cost_id: `3`
- cost_finalized: `True`
- failure_messages: `[]`
- direct_error: `None`
- created_landed_cost_names: `['LC/2026/0003']`

## Risks
- Legacy model 'mrp.scrap.record' is absent in UAT. The module now has to rely on stock.scrap only.