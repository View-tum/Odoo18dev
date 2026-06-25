# Mobile Mixed Payment Custom Widget Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the temporary inline mixed-payment editor with the approved tablet-oriented Owl widget on the Mobile Warehouse create-invoice wizard without changing payment posting or accounting logic.

**Architecture:** Keep `sale.advance.payment.inv` responsible for totals, validation, invoice creation, and payment posting. Register an Owl field widget for `mobile_payment_line_ids` that renders the payment buttons and rows, edits the existing transient lines, and delegates all balance and configuration truth to server fields.

**Tech Stack:** Odoo 18 Enterprise, Python transient models, XML inherited views, Owl/web client field registry, SCSS assets, Odoo test framework, Playwright UI verification.

---

## Task 1: Lock The Server/View Contract With Tests

**Files:**
- Modify: `custom/goldmints_addon-main/sale_auto_confirm_invoice/tests/test_mobile_mixed_payment.py`
- Verify: `custom/goldmints_addon-main/sale_auto_confirm_invoice/views/sale_make_invoice_advance_views.xml`

- [ ] Add a failing assertion that the Mobile Warehouse wizard uses `widget="mobile_mixed_payment_rows"` for payment rows.
- [ ] Add a failing assertion that obsolete server-side add-row buttons are no longer present in the wizard view.
- [ ] Run the focused addon test to confirm the new contract fails before UI implementation.

## Task 2: Build The Owl Payment Rows Widget

**Files:**
- Create: `custom/goldmints_addon-main/sale_auto_confirm_invoice/static/src/components/mobile_mixed_payment/mobile_mixed_payment.js`
- Create: `custom/goldmints_addon-main/sale_auto_confirm_invoice/static/src/components/mobile_mixed_payment/mobile_mixed_payment.xml`
- Create: `custom/goldmints_addon-main/sale_auto_confirm_invoice/static/src/components/mobile_mixed_payment/mobile_mixed_payment.scss`
- Modify: `custom/goldmints_addon-main/sale_auto_confirm_invoice/__manifest__.py`

- [ ] Register a custom x2many field widget for `mobile_payment_line_ids`.
- [ ] Implement Bank, Cash, Cheque, and rounding add controls using transient one2many records only.
- [ ] Render editable amount rows, configured journal/account display, delete control, and cheque detail fields.
- [ ] Scope tablet modal styling to the Mobile Warehouse receipt panel.

## Task 3: Wire The Approved Wizard UI And Remove Draft Plumbing

**Files:**
- Modify: `custom/goldmints_addon-main/sale_auto_confirm_invoice/views/sale_make_invoice_advance_views.xml`
- Modify: `custom/goldmints_addon-main/sale_auto_confirm_invoice/models/sale_advance_payment_inv.py`
- Modify: `custom/goldmints_addon-main/sale_auto_confirm_invoice/models/mobile_payment_line.py`

- [ ] Replace the inline list/buttons with the widget and clean receipt-summary layout.
- [ ] Remove the interim `action_add_*` modal-reopen methods no longer called by the widget.
- [ ] Retain route labels and write-off display through computed server fields with explicit exception handling.

## Task 4: Validate Behavior And Tablet Rendering

**Files:**
- Test: `custom/goldmints_addon-main/sale_auto_confirm_invoice/tests/test_mobile_mixed_payment.py`

- [ ] Upgrade and run `/sale_auto_confirm_invoice` automated tests; preserve existing posting and validation assertions.
- [ ] Open `Sales > Orders > Orders > S11765 > Create Invoice` in the actual UAT UI.
- [ ] Verify tablet layout, add/remove/edit actions, over-total rejection, and balanced Bank/Cash/Rounding state without posting an invoice.
