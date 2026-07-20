# Draft Delivery Confirmation and Production Lot Alignment

## Context

The target system is Odoo 18 Enterprise UAT at `tcg-uat.365odoo.com`. The source of truth for Delivery Order references and lot allocation is the Production system at `tcc.thecool.com`.

The approved scope is all 905 records in the current UAT Delivery Orders result set, restricted at execution time to records whose state is still `draft`.

## Standard Odoo vs Pain Point

Odoo 18 provides `stock.picking.action_confirm()` to confirm draft stock moves, and `stock.picking.action_assign()` to perform the standard availability and reservation flow. Server actions can be bound to a model and exposed in the contextual Actions menu for mass execution.

The Delivery Orders list currently has no “Mark as To Do” contextual action. In addition, UAT must use the same lot allocations as Production where the corresponding lot exists and has sufficient available quantity in UAT.

## Design

### Mark as To Do action

Create one database-level Server Action in UAT:

- Name: `Mark as To Do`
- Model: `stock.picking`
- Action type: Execute Python Code
- Binding: contextual Actions menu for `stock.picking`
- Binding view type: list
- Behavior: filter the selected recordset to `state == "draft"` and invoke `action_confirm()` once on that recordset

The action must not use `sudo()`, write the picking state directly, validate transfers, or process unselected records.

### Production comparison

Read Production without making any changes. Restrict both systems to:

- Company: `บริษัท เดอะ คูล จำกัด`
- Operation Type: `บริษัท เดอะ คูล จำกัด: Delivery Orders`

Pair Production and UAT pickings by:

1. Source Document
2. Operation Type
3. Company

The OUT references are comparison outputs, not pairing keys. No sequence or OUT reference is changed.

Ambiguous matches, missing matches, product differences, and quantity differences are skipped and reported.

### UAT confirmation and lot allocation

For the 905 records in the approved UAT result set:

1. Re-check the record scope and retain only records still in `draft`.
2. Invoke the standard `action_confirm()` flow.
3. Invoke the standard `action_assign()` availability flow.
4. Compare the resulting allocation with the matched Production picking.
5. Where required, use Odoo ORM reservation mechanisms to align the UAT lot allocation with Production.

A Production lot may be allocated in UAT only when:

- the exact lot exists in UAT for the same product and company;
- the required quantity is available in the relevant UAT source location; and
- the product, unit of measure, and demanded quantity match without ambiguity.

If any condition fails, leave that picking unchanged after the standard confirmation/availability step and include it in the exception report. Do not create lots or alter stock quantities.

## Data Flow

1. Capture the exact 905-record UAT scope before making changes.
2. Export a read-only Production mapping for the approved company and operation type.
3. Build an unambiguous Production-to-UAT match table.
4. Record a pre-execution report with UAT OUT, Production OUT, source document, products, quantities, and lots.
5. Create the contextual UAT Server Action without executing it.
6. Select the approved 905 UAT records and invoke the action.
7. Run standard availability and align eligible lots through Odoo ORM.
8. Produce a post-execution comparison and exception report.

## Safety and Integrity

- Existing access rights and company checks remain enforced.
- Non-draft records are ignored.
- No picking is validated and no completed or cancelled record is changed.
- Production is strictly read-only.
- No SQL statement writes to either database.
- No lot, stock quant, stock move, valuation layer, or accounting entry is fabricated.
- Stock reservations occur only through Odoo ORM and standard reservation rules.
- Pickings with missing lots, insufficient availability, or ambiguous mappings are skipped and reported.
- Deleting or unbinding the Server Action removes the menu but does not reverse pickings already confirmed by users.

## Outputs

Produce a comparison report containing:

- UAT OUT reference
- Production OUT reference
- Source Document
- Match status
- Product and quantity comparison
- Production lot
- UAT lot before and after
- Confirmation and availability result
- Exception reason

The report must clearly list OUT references that differ between Production and UAT.

## Verification

- Confirm the action appears in the Delivery Orders list Actions menu.
- Confirm creating the action does not change any Delivery Order.
- Confirm the execution scope contains exactly the intended 905 UAT records before applying the draft-state filter.
- Confirm only records that were still draft were processed.
- Confirm Production received no writes.
- Confirm no picking was validated and no stock valuation or accounting entry was created.
- Confirm aligned UAT lots match Production for every successful row.
- Confirm skipped rows retain stock integrity and have an explicit exception reason.
