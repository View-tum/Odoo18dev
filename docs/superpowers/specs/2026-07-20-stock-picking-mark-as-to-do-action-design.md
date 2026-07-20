# Stock Picking “Mark as To Do” Server Action

## Context

The target system is Odoo 18 Enterprise UAT at `tcg-uat.365odoo.com`. Users need a contextual action for confirming selected draft Delivery Orders from the `stock.picking` list view.

## Standard Odoo vs Pain Point

Odoo 18 provides `stock.picking.action_confirm()` to confirm draft stock moves and trigger the standard scheduler. Server actions can be bound to a model and exposed in the contextual Actions menu for mass execution.

The Delivery Orders list currently has no “Mark as To Do” contextual action, so users cannot invoke the standard confirmation flow conveniently for a selected recordset.

## Design

Create one database-level Server Action:

- Name: `Mark as To Do`
- Model: `stock.picking`
- Action type: Execute Python Code
- Binding: contextual Actions menu for `stock.picking`
- Binding view type: list
- Behavior: filter the selected recordset to `state == "draft"` and invoke `action_confirm()` once on that recordset

The action must not use `sudo()`, write the picking state directly, validate transfers, or process unselected records.

## Data Flow

1. The user selects one or more stock pickings in the list view.
2. The user chooses `Actions > Mark as To Do`.
3. The server action receives the selected `records`.
4. Only draft pickings are retained.
5. Odoo’s standard `action_confirm()` confirms their draft moves and triggers the standard stock scheduler.

## Safety and Integrity

- Existing access rights and company checks remain enforced.
- Non-draft records are ignored.
- No picking is validated and no completed or cancelled record is changed.
- Stock reservations may occur only through Odoo’s standard confirmation and reservation rules.
- Rollback is performed by deleting or unbinding the Server Action; this does not reverse documents already confirmed by users.

## Verification

- Confirm the action appears in the Delivery Orders list Actions menu.
- Confirm creating the action does not change any Delivery Order.
- Do not execute the action against the current 905 records as part of setup.
- A later functional test, if authorized, must use a representative disposable UAT record rather than the full selection.
