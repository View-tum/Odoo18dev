# Mobile Mixed Payment Custom Widget Design

## Status

Approved design direction: custom tablet widget matching the provided reference.

Approved on: 2026-05-27

This document extends `2026-05-27-mobile-mixed-payment-create-invoice-design.md`. It changes presentation only. The approved mixed-payment accounting flow remains authoritative.

## Objective

Replace the generic editable list appearance in the Mobile Warehouse `Create Invoice(s)` wizard with a compact receipt-entry surface matching the provided tablet reference:

- clearly separated invoice context and receipt entry,
- large invoice total,
- one-tap tender buttons,
- readable receipt rows with configured accounting route,
- visible write-off classification,
- clear balance and submit state.

## Standard Vs Pain Point

Standard Odoo form and one-to-many list components are appropriate for general CRUD entry, but do not produce the receipt-like tablet layout requested without exposing grid chrome, generic add controls, and accounting detail fields that compete with the cashier task.

The custom widget is limited to presentation and row editing for Mobile Warehouse invoice receipt entry. Odoo remains responsible for invoice posting, payment creation, write-off reconciliation, cheque lifecycle, and accounting entries.

## UI Contract

For Mobile Warehouse only, the wizard displays the following composition:

```text
Create Invoice(s)

Create Invoice    Regular invoice       Invoice Date     05/27/2026
--------------------------------------------------------------------

Receive Payment                                      150,000.10 ฿

[ + Bank ] [ + Cash ] [ + Cheque ] [ + ปัดเศษ ]

Type          Amount          Journal / Account
Bank          100,000.00      BAY CA #046-0-14721-8        x
Cash           50,000.00      เงินสดรับชำระ Mobile          x
ปัดเศษ          0.10          ส่วนต่างรับชำระ / Auto Difference x
               Write-off

Payment Received                                  150,000.00
Write-off                                               0.10
Balance                                                 0.00

[ Create Invoice & Receive Payment ] [ Cancel ]
```

Visual requirements:

- The popup width, spacing, border radius, and muted separators follow the reference.
- The primary color follows the current Odoo purple palette.
- The selected/add-first tender button is filled; additional tender buttons are outlined.
- Amounts are right aligned and editable in large touch targets.
- Journal/account is read-only and derived from configuration.
- Rounding is labelled `ปัดเศษ` and has a `Write-off` badge.
- The balance is green only when it is zero; exceeded totals show the existing error message and do not permit submission.
- Row removal uses a small right-aligned `x` action.
- Cheque rows reveal required cheque details without changing the overall receipt table layout.

## Component Boundary

Add an Owl field widget for `mobile_payment_line_ids`, registered only for this wizard view. The widget owns:

- rendering payment rows,
- add-row buttons,
- row amount editing,
- row removal,
- cheque-detail presentation,
- read-only configured route display.

The parent wizard view owns:

- invoice method and date,
- invoice total heading,
- received/write-off/balance summary fields,
- validation alert,
- submit and cancel buttons.

The widget writes transient rows only. It does not call payment APIs and does not construct journal entries.

## Data Contract

The widget consumes the existing transient model fields:

- `payment_type`
- `amount`
- `journal_account_name`
- `is_rounding`
- `cheque_number`
- `cheque_bank_id`
- `cheque_branch`
- `cheque_date`

It invokes existing parent wizard add-row actions for `Bank`, `Cash`, `Cheque`, and `Rounding`, or an equivalent row-command update with the same server-side defaults.

No journal or ledger account is editable from the widget.

## Accounting And Safety Contract

The existing processing behavior remains unchanged:

- Bank and Cash create standard inbound payments on their configured journals.
- Cheque creates an inbound cheque receipt and follows the existing cheque validation lifecycle.
- Rounding is a reconciliation write-off to the configured Auto Difference Account, not a receipt journal.
- Settlement totals cannot exceed the invoice total.
- Submission is allowed only when an actual payment exists and the balance is zero.
- The new UI path must continue using public payment registration behavior and must not add transaction commits or bypass tax behavior.

## Technical Implementation Scope

Expected additions or updates in `sale_auto_confirm_invoice`:

- `static/src/components/mobile_mixed_payment/`: Owl component, XML template, and SCSS.
- `__manifest__.py`: backend asset declarations for the component files.
- `views/sale_make_invoice_advance_views.xml`: mount the widget and preserve parent totals/footer.
- `models/mobile_payment_line.py`: expose display values only where needed by the widget, without posting behavior.
- `tests/`: preserve existing accounting tests and add contract checks for UI actions/display fields where server-testable.

Any currently drafted generic-list styling is replaced or reduced to avoid rendering two payment entry controls.

## Acceptance Criteria

1. The Mobile Warehouse invoice popup visually follows the reference layout at tablet width.
2. `+ Bank`, `+ Cash`, `+ Cheque`, and `+ ปัดเศษ` add the correct transient row type.
3. Rows display editable amounts and read-only configured journal/account names.
4. A rounding row displays `Write-off` and uses the configured Auto Difference account.
5. Bank `100,000.00`, Cash `50,000.00`, and Rounding `0.10` on a `150,000.10` invoice show balance `0.00` and enable the submit action.
6. A total above the invoice total displays the blocking alert and leaves submit unavailable.
7. Cheque details remain required and route through existing cheque behavior.
8. Non-Mobile Warehouse invoice wizards remain standard.
9. Existing automated accounting tests continue to pass.
10. UI verification is performed from the actual system path `Sales > Orders > Orders > <Mobile Warehouse Order> > Create Invoice`.
