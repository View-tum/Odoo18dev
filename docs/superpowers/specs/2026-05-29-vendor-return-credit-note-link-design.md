# Vendor Return to Vendor Credit Note Link Design

## Objective

Connect vendor return pickings to vendor credit notes so Accounting can select one or more completed return documents while creating a Credit Note from a Vendor Bill, and Warehouse can see whether each return has already been credited.

## Current Context

Standard Odoo separates the stock return flow from the vendor credit note flow:

- Vendor returns are created from `stock.return.picking` and become `stock.picking` records with `return_id`.
- Vendor Credit Notes are created from the Vendor Bill `Credit Note` button through `account.move.reversal`.
- Purchase stock/accounting already relies on `purchase_line_id`, returned stock moves, valuation layers, and standard account move posting.

Existing custom modules already touch the same surface:

- `account_credit_note_consolidated` owns the current draft Credit Note item consolidation flow.
- `vendor_billing_note` already supports APD/CN selection in Billing Notes.
- `stock_picking_invrefs_edit_date_done` and `stock_picking_invoice_link` already add invoice-related metadata and links on pickings.

The implementation should extend `account_credit_note_consolidated` instead of creating a competing module.

## Standard vs Pain Point

Standard behavior:

- Accounting can create a Vendor Credit Note from a Vendor Bill.
- Warehouse can create and validate a Return Picking.
- Odoo does not force a direct operational link between those two documents in the UI.

Pain point:

- Accounting must manually identify which return picking should be credited.
- Warehouse cannot quickly see whether a completed vendor return has a draft or posted Credit Note.
- The existing custom consolidation wizard is only available after a draft Credit Note exists, so it is one step too late for the requested flow.

Proposed custom behavior:

- Extend the standard `Credit Note` wizard to select multiple completed vendor return pickings before creating the draft Credit Note.
- Generate credit note lines from the selected return moves.
- Link the created Credit Note back to all selected return pickings and stock moves.
- Show Credit Note status and smart buttons on the return picking.

Accounting and stock impact:

- No manual journal entries.
- Use standard `account.move.reversal` and draft `account.move` behavior.
- Preserve `purchase_line_id` and `stock_move_id` links on credit note lines where possible to support price difference, valuation, and audit traceability.

Rollback path:

- The change is isolated to `account_credit_note_consolidated`.
- If disabled, standard Credit Note creation remains available.
- Existing posted Credit Notes and stock moves are not mutated except for traceability links.

## Scope

In scope:

- Vendor Bill to Vendor Credit Note only: `in_invoice -> in_refund`.
- Select multiple vendor return pickings in one Credit Note.
- Return picking status and smart button for Warehouse visibility.
- Draft Credit Note creation with editable lines for Accounting review.

Out of scope:

- Customer RMA credit notes.
- Auto-posting credit notes.
- Auto-payment or reconciliation.
- Changing stock valuation logic.
- Replacing the existing Billing Note APD/CN flow.

## UI Flow

1. Warehouse validates a vendor return from `Inventory > Operations > Transfers`.
2. Accounting opens a Vendor Bill from `Accounting > Vendors > Bills`.
3. Accounting clicks the standard `Credit Note` button.
4. The Credit Note wizard shows a new `Vendor Returns` section.
5. Accounting selects one or more completed Return Pickings for the same vendor/company/currency.
6. The wizard displays preview lines grouped by return picking and product.
7. Accounting clicks the standard create/reverse action.
8. Odoo creates a Draft Vendor Credit Note with lines generated from the selected return moves.
9. Warehouse sees the return status change to `Draft Credit Note`.
10. When Accounting posts the Credit Note, Warehouse sees `Credit Note Posted`.

## Data Model

### `stock.picking`

Add fields:

- `vendor_credit_note_ids`: many2many to `account.move`, limited to `move_type = in_refund`.
- `vendor_credit_note_count`: computed integer.
- `vendor_credit_note_state`: computed selection.

Suggested states:

- `not_required`: not a vendor return.
- `waiting`: completed vendor return with no active credit note.
- `draft`: linked draft credit note exists.
- `posted`: linked posted credit note exists.
- `cancelled`: linked credit notes exist but all are cancelled.

Vendor return detection:

- Picking is a return when `return_id` is set and the picking type is an outgoing operation back to a supplier location.
- The linked vendor is `partner_id`.

### `account.move`

Add fields:

- `return_picking_ids`: many2many to `stock.picking`.

Behavior:

- Only relevant for `move_type = in_refund`.
- Used for smart buttons, domains, and return status computation.

### `account.move.line`

Add fields:

- `return_picking_id`: many2one to `stock.picking`.
- `return_stock_move_id`: many2one to `stock.move`.

Behavior:

- Set these on invoice lines generated from selected return moves.
- Preserve existing standard/custom fields such as `purchase_line_id`, `tax_ids`, `analytic_distribution`, and `account_id`.

## Wizard Design

Extend `account.move.reversal` in `account_credit_note_consolidated`.

New fields:

- `return_picking_ids`: many2many to `stock.picking`.
- `return_line_ids`: one2many transient preview lines.
- `include_vendor_returns`: boolean, default true when the active document is a vendor bill.

Preview line fields:

- `is_selected`
- `picking_id`
- `stock_move_id`
- `product_id`
- `quantity`
- `uom_id`
- `price_unit`
- `tax_ids`
- `account_id`
- `purchase_line_id`
- `source_bill_line_id`
- `name`

Line source priority:

1. Original Vendor Bill line matching the return move `purchase_line_id` and product.
2. Purchase Order line from `stock.move.purchase_line_id`.
3. Product expense account and standard price fallback.

## Selection Domain

Allowed return pickings:

- `state = done`
- `return_id != False`
- `picking_type_id.code = outgoing`
- `partner_id.commercial_partner_id` equals the Vendor Bill `commercial_partner_id`
- `company_id` equals the Vendor Bill company
- not linked to any non-cancelled Vendor Credit Note

For multiple selections:

- All selected returns must share the same partner, company, and currency context.
- The Credit Note currency follows the original Vendor Bill.

## Guard Rules

Hard blocks:

- Cannot select a return that is not done.
- Cannot select a return for another vendor or company.
- Cannot select a return already linked to a non-cancelled credit note.
- Cannot create a Credit Note with selected returns if none of the return moves has a non-zero remaining creditable quantity.

Quantity rules:

- Default quantity is the done quantity on the return stock move.
- A selected return picking is fully credited in this implementation.
- Partial credit by quantity is out of scope for this implementation.

Posting rules:

- Create Draft Vendor Credit Note only.
- When the credit note is posted, return status becomes `posted`.
- If the credit note is cancelled, the return becomes `cancelled` or `waiting` depending on whether any active linked credit note remains.

## Existing Wizard Compatibility

The existing `account.move.consolidated.reversal` wizard should not be removed immediately.

Target behavior:

- Reuse its return-line discovery and value preparation logic as helper methods.
- Keep the old `Consolidate Items` button as fallback during rollout.
- Avoid duplicated business logic between the old wizard and the extended standard Credit Note wizard.

## UI Changes

### Vendor Bill Credit Note Wizard

Add a `Vendor Returns` section under the standard reversal fields.

Suggested layout:

- Return selection field at top.
- Preview list below with Return No., Product, Quantity, Unit Price, Tax, Subtotal.
- Warning banner when a selected return has no matching Vendor Bill line and uses fallback pricing.

### Return Picking Form

At `Inventory > Operations > Transfers`:

- Add `Vendor Credit Note Status` badge near operation metadata.
- Add smart button `Credit Notes`.
- Optional search filter: `Waiting Credit Note`.

### Vendor Credit Note Form

At `Accounting > Vendors > Credit Notes`:

- Show linked `Return Pickings`.
- Add smart button or tab to open linked returns.

## Reporting and Audit

Credit Note line labels should include the return reference:

`Return <PICKING_NAME>: <PRODUCT_NAME>`

Chatter:

- Post a message on the Return Picking when a Draft Credit Note is created.
- Post a message on the Credit Note listing selected Return Pickings.

## Test Plan

Core tests:

1. Create PO, receive goods, create vendor bill, validate vendor return, create credit note from bill and select one return.
2. Create two completed return pickings for the same vendor and create one credit note selecting both.
3. Verify credit note lines match returned products, quantities, taxes, accounts, and purchase lines.
4. Verify return status changes from `waiting` to `draft`, then `posted`.
5. Verify already-linked return cannot be selected again while CN is draft or posted.
6. Verify cancelling the credit note releases or updates the return status.

Regression tests:

- Standard Vendor Bill Credit Note without selecting return still works.
- Existing `account_credit_note_consolidated` button still works.
- Vendor Billing Note APD/CN selection still accepts created `in_refund`.

## Acceptance Criteria

- A single Vendor Credit Note can link multiple completed vendor return pickings.
- Credit Note lines are generated from selected return documents.
- Warehouse can see whether each vendor return is waiting, draft credited, or posted credited.
- Accounting remains on standard Odoo credit note flow.
- No official Odoo addon is modified.
- No manual accounting entry is created outside `account.move`.
