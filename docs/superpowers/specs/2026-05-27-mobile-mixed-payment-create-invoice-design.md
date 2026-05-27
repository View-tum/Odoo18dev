# Mobile Mixed Payment Create Invoice Design

## Status

Approved design direction: `A - Quick Payment Rows`

Approved on: 2026-05-27

## Objective

Provide a tablet-friendly payment section in the existing Mobile Warehouse `Create Invoice(s)` wizard. A sale user can receive one invoice through multiple tender types in one action, while Odoo posts correct accounting entries and reconciles accounts receivable automatically.

Supported settlement types:

- Bank
- Cash
- Cheque
- Rounding write-off

Example:

```text
Invoice Total     150,000.10
Bank              100,000.00
Cash               50,000.00
Rounding                0.10
Balance                  0.00
```

## Standard Vs Pain Point

Standard Odoo correctly separates customer invoices, inbound payments, reconciliation, and payment differences. Bank, Cash, and Cheque must therefore remain payment transactions, while Rounding must remain a write-off rather than a payment.

The current custom Mobile Warehouse flow supports only one `mobile_payment_method` per invoice wizard and therefore cannot receive a mixed payment such as Bank plus Cash plus Rounding in one tablet operation.

The design extends the existing wizard only for Mobile Warehouse sales and reuses existing accounting configuration and cheque processing. It does not alter standard Odoo addons.

## Scope

### In Scope

- Replace the single mobile payment selector in the Mobile Warehouse wizard with Quick Payment Rows.
- Allow multiple Bank, Cash, and Cheque rows.
- Allow one or more Rounding write-off rows.
- Create and post the invoice, create inbound payments, apply write-off, and reconcile until the invoice is paid in one user action.
- Treat an inbound cheque as received payment immediately, posting to cheque received clearing and leaving subsequent bank clearance to the existing cheque lifecycle.
- Validate settlement totals before accounting documents are created.

### Out Of Scope

- Changing standard Sale invoice behavior outside Mobile Warehouse.
- Broadening the current Mobile Warehouse invoice-method choices; the existing delivered/regular invoice restriction remains unchanged.
- Treating a rounding line as revenue discount, invoice discount, or payment journal entry.
- Redesigning cheque deposit, cheque return, or bank reconciliation flows.
- Adding a maximum rounding amount.

## Existing Components To Reuse

- `sale_auto_confirm_invoice`: existing Mobile Warehouse invoice wizard, journal settings, invoice posting, and auto-payment entry point.
- `cheque_management`: inbound cheque details and cheque received clearing entries.
- `account_payment_auto_difference`: configured write-off account, label, analytic distribution, and multi-deduction behavior.

## Tablet User Interface

The existing `Create Invoice(s)` popup keeps its invoice-method and invoice-date section. For Mobile Warehouse only, its single payment-method selector is replaced by the following area:

```text
Receive Payment                              Invoice Total 150,000.10

[ + Bank ] [ + Cash ] [ + Cheque ] [ + ปัดเศษ ]

Type         Amount          Journal / Account
Bank         100,000.00      BAY CA #046-0-14721-8          [Remove]
Cash          50,000.00      เงินสดรับชำระ Mobile             [Remove]
ปัดเศษ             0.10      Auto Difference / Write-off     [Remove]

Payment Received                             150,000.00
Write-off                                          0.10
Balance                                            0.00

[ Create Invoice & Receive Payment ] [ Cancel ]
```

Journal or account values are read-only for sale users. They are displayed so the operator can identify the receiving route, but the system derives them from configuration.

For each Cheque row, the row expands inline to require:

- Cheque Number
- Bank
- Branch
- Cheque Date

## Data Model Design

Add a transient settlement line model owned by the invoice wizard:

- Model: `sale.advance.payment.inv.mobile.line`
- Parent field: `wizard_id`
- Parent one-to-many: `mobile_payment_line_ids` on `sale.advance.payment.inv`

Each line contains:

- `sequence`
- `payment_type`: `bank`, `cash`, `cheque`, `rounding`
- `amount`
- Computed/read-only mapped `journal_id` for Bank, Cash, and Cheque
- Computed/read-only mapped `writeoff_account_id` for Rounding
- Cheque data fields required only when `payment_type == "cheque"`

The settlement rows are transient only. Once the action succeeds, the persistent audit records are the posted customer invoice, posted account payments, inbound cheque records, reconciliation records, and write-off journal items.

## Configuration Mapping

The flow uses existing configured values:

| Row Type | Configuration Source | Accounting Use |
| --- | --- | --- |
| Bank | `mobile_bank_transfer_journal_id` | Inbound payment journal |
| Cash | `mobile_cash_journal_id` | Inbound payment journal |
| Cheque | `mobile_cheque_journal_id` | Inbound cheque payment journal and cheque received clearing route |
| Rounding | `auto_diff_account_id`, label and analytic distribution | Payment difference write-off |

No sale user is allowed to select an arbitrary ledger account from the wizard.

## Processing Flow

1. The user opens `Create Invoice(s)` from a Mobile Warehouse sale order.
2. The wizard initializes with Quick Payment Rows available and preserves the current Mobile Warehouse invoice method restriction.
3. The user adds payment and optional rounding lines.
4. Before posting anything, the wizard validates company configuration, cheque details, positive amounts, and totals.
5. The wizard creates and posts the customer invoice through the current invoice flow.
6. For each non-rounding line, the wizard creates one inbound payment using its configured journal.
7. If rounding exists, its summed amount is attached as payment-difference write-off to the final actual payment row processed, so it closes the remaining receivable without producing a false cash or bank receipt.
8. Cheque payment rows populate inbound cheque detail lines through the existing cheque mechanism.
9. The payments and write-off are reconciled with the posted invoice.
10. When balance is zero, the invoice payment status becomes `Paid` or the equivalent reconciled state produced by the existing accounting stack.

## Accounting Entries

### Bank Plus Cash Plus Rounding

Invoice total: `150,000.10`

Payments:

- Bank: `100,000.00`
- Cash: `50,000.00`
- Rounding: `0.10`

Expected journal effect:

```text
Customer Invoice
Dr Accounts Receivable                 150,000.10
    Cr Revenue / Output VAT             150,000.10

Bank Payment
Dr Bank Clearing                        100,000.00
    Cr Accounts Receivable              100,000.00

Final Cash Payment With Rounding
Dr Cash                                  50,000.00
Dr Rounding Difference                        0.10
    Cr Accounts Receivable               50,000.10
```

### Cheque Payment

When a cheque is received:

```text
Cheque Payment
Dr Cheque Received Clearing              payment amount
    Cr Accounts Receivable               payment amount
```

The invoice is paid upon cheque receipt. The existing cheque lifecycle later transfers the cheque balance to bank when it is deposited or cleared:

```text
Cheque Clearance
Dr Bank                                  payment amount
    Cr Cheque Received Clearing          payment amount
```

## Validation Rules

### Amount Rules

- Every added row must have `amount > 0`.
- At least one actual payment row is required: Bank, Cash, or Cheque.
- Rounding is a positive customer short-payment write-off only.
- Rounding has no configured maximum amount.
- The user may enter any positive rounding amount provided the total settlement does not exceed the invoice total.

Define:

```text
actual_payment_total = sum(Bank, Cash, Cheque)
rounding_total = sum(Rounding)
settlement_total = actual_payment_total + rounding_total
```

Validation:

```text
settlement_total > invoice_total  => Block with error before creating invoice or payments
settlement_total < invoice_total  => Keep action blocked and show remaining Balance
settlement_total = invoice_total  => Allow Create Invoice & Receive Payment
```

Error message for over-entry:

```text
ยอดรับชำระรวมและยอดปัดเศษเกินยอดใบแจ้งหนี้ กรุณาตรวจสอบยอดก่อนสร้างใบแจ้งหนี้
```

### Configuration Rules

- Each non-rounding row must resolve to a configured journal in the same company as the sale order.
- A Rounding row requires the existing Auto Difference Account to be configured.
- A Cheque row requires an inbound cheque-capable journal/payment method and complete cheque detail values.
- Multi-company selections remain blocked for the Mobile Warehouse auto-payment action.

## Compatibility And Safety

- Official Odoo addons are not modified.
- Changes are contained in custom inheritance and XML extensions.
- The existing down payment account behavior remains unchanged.
- Non-Mobile Warehouse invoicing does not render Quick Payment Rows and preserves its existing behavior.
- Tax calculation remains on the posted invoice; Rounding affects reconciliation only.
- Bank, Cash, and Cheque reporting remains based on actual payment records.
- The new implementation must work with existing uncommitted adjustments in payment difference and cheque modules rather than overwriting them.

## Planned Implementation Boundaries

Likely custom changes:

- `sale_auto_confirm_invoice/models/`: add transient payment line model and refactor wizard payment registration to iterate configured rows.
- `sale_auto_confirm_invoice/views/`: render the Quick Payment Rows list and totals in the existing popup.
- `sale_auto_confirm_invoice/security/`: grant suitable access to the new transient line model if required.
- `sale_auto_confirm_invoice/__manifest__.py`: declare explicit custom dependencies where the wizard directly calls cheque and auto-difference behavior.
- `sale_auto_confirm_invoice/tests/`: add focused transaction tests for mixed payment, cheque, write-off, and validation.

Existing payment-difference and cheque modules are reuse points, not broad refactoring targets.

## Acceptance Tests

1. Mobile Warehouse invoice with Bank only posts and reconciles as paid.
2. Mobile Warehouse invoice with Bank and Cash creates two correctly journaled inbound payments and reconciles as paid.
3. Mobile Warehouse invoice with Cheque creates inbound cheque details, posts to cheque received clearing, and reconciles as paid.
4. Mobile Warehouse invoice with Bank, Cash, and Rounding creates only real receipt payments plus a write-off and reconciles as paid.
5. Rounding can exceed `1.00` and succeeds when the settlement total exactly matches the invoice total.
6. Settlement total greater than invoice total is blocked before invoice or payment creation.
7. Settlement total less than invoice total cannot execute the paid action and displays its balance.
8. Missing Bank, Cash, Cheque journal, Auto Difference Account, or cheque-required field blocks execution with a clear error.
9. Non-Mobile Warehouse invoices behave as before.
10. Existing Mobile Warehouse invoice tax calculation and down payment configuration are unchanged.
