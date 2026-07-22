# Linkweld Accounting Control and Journal Entry Playbook Design

## Document Control

- Project: Linkweld (Thailand) Co., Ltd.
- System: Odoo 18 Enterprise staging
- Design date: 2026-07-22
- Language: Thai with Odoo field and model names in English
- Delivery pattern: Separate companion book linked to the existing Accounting manual
- Evidence method: Evidence-first Read-only
- Example method: Formula plus hypothetical THB amounts; never copy confidential transaction values

## Objective

Create a separate Thai `Accounting Control & JE Playbook` covering every installed Standard, Thai localization, OCA, and Linkweld custom addon that can create, alter, classify, reconcile, reverse, report, or control accounting entries. The playbook must tell Accounting what to inspect, which policy controls the behavior, what business event triggers accounting, the expected Debit/Credit pattern, and which UAT evidence is required before go-live.

The playbook complements the completed `ACC-001` through `ACC-030` configuration manual. It does not replace that manual and does not present hypothetical journal entries as confirmed Linkweld postings.

## Deliverables

1. `03_Linkweld_Odoo18_Accounting_Control_JE_Playbook_TH.docx`
2. `03_accounting_control_je_playbook_th.md`
3. `accounting_module_je_matrix.csv` for filtering by module, document, trigger, tax, account role, and UAT status
4. Cross-reference section added to the existing Accounting manual source and README
5. Updated `LINKWELD_DEV_HANDOFF.md`

## Scope Rule

The term “every module” means every installed or locally maintained module that can affect Accounting. Pure UI, communication, theme, or infrastructure modules with no accounting effect are listed in an exclusion appendix with the reason they require no JE chapter.

### Included Module Families

1. Core Accounting and Invoicing
2. Sales, CRM handoff, Subscription where installed, Rental, Website/eCommerce, and Point of Sale where installed
3. Purchase, Purchase Agreements, 3-way matching, and Expenses
4. Inventory, Barcode, landed costs, automated valuation, lots/serials, consignment, and inter-warehouse flows
5. Manufacturing, subcontracting, by-products, scrap, unbuild, repair, quality, and maintenance where installed
6. Assets, depreciation, disposal, deferred expense, deferred revenue, loans, and budgets
7. Project, Timesheets, Helpdesk, field service where installed, and analytic accounting
8. Payment providers, payment methods, bank, cash, cheques, reconciliation, and currency differences
9. Documents, Approvals, and other controls that govern evidence or authorization without directly posting
10. Thailand localization: VAT, WHT, tax invoice, tax report, PND3, PND53, WHT certificate, and Thai partner/company fields
11. OCA/local forks and Linkweld custom addons that inherit accounting, payment, tax, stock valuation, sales, purchase, MRP, asset, or reporting models

### Excluded

- Developer Mode > Technical menus
- Credentials, tokens, bank-account numbers, partner identity, confidential prices, payroll identities, or transaction amounts
- Addons that are not installed and have no approved target-state requirement, except where an installed local fork creates a compatibility risk
- Creation or modification of settings, master data, transactions, journal entries, reports, modules, users, or access rights
- Claims that a hypothetical JE is the actual Linkweld posting

## Evidence Classification

- `Confirmed Linkweld`: Existing read-only evidence proves configuration and posting behavior.
- `Partially Confirmed`: Configuration or source document is visible, but the full JE/result is not.
- `Standard Example`: Odoo 18 standard behavior represented with hypothetical values.
- `Custom Review Required`: Local addon changes the standard flow and requires source review or Clone-UAT evidence.
- `Not Available`: Safe evidence is unavailable.

Every JE table must display one of these labels.

## Journal Entry Example Standard

Use a consistent hypothetical baseline unless the scenario requires another basis:

- Net amount: THB 100,000.00
- VAT: 7% = THB 7,000.00
- Gross amount: THB 107,000.00
- WHT example: 3% of approved tax base = THB 3,000.00
- Customer/vendor settlement example after WHT: THB 104,000.00

Each example includes:

1. Business event and posting trigger
2. Document state before and after posting
3. Debit account role
4. Credit account role
5. Formula and hypothetical amount
6. VAT/WHT treatment
7. Currency and exchange-difference treatment where relevant
8. Stock Valuation Layer or Asset Board relationship where relevant
9. Reversal, refund, return, cancellation, or correction JE
10. Reconciliation target and period-close control

Account names are policy roles such as Accounts Receivable, Accounts Payable, Output VAT, Input VAT, Stock Valuation, Stock Input, Stock Output, WIP, COGS, Fixed Asset, Accumulated Depreciation, Depreciation Expense, Deferred Revenue, and Deferred Expense. A Linkweld account code is shown only when prior sanitized evidence confirms it and the mapping is material to the control.

## Chapter Template by Module

Each module chapter contains:

1. Module purpose and accounting boundary
2. Installed Standard/OCA/custom addon map
3. Source documents and responsible roles
4. Accounting configuration checklist
5. Accounting policy decisions and approval owner
6. Posting triggers and prohibited early actions
7. Standard JE formula
8. Hypothetical JE example
9. VAT/WHT/localization impact
10. Stock, manufacturing, asset, analytic, and report dependencies
11. Reversal and exception paths
12. Reconciliation and period-close checks
13. Access control and audit evidence
14. Standard Odoo versus Linkweld pain point
15. Positive, negative, reversal, access, and regression UAT cases
16. Evidence status and cross-reference to ACC configuration IDs

## Planned Module Chapters

### Part 1: Order to Cash

- Sales quotation/order to delivery and invoice
- Customer advance/down payment
- Credit note, return, discount, and bad debt
- Rental pickup, return, late fee, sale of rental asset, and disposal
- eCommerce/POS/payment provider only where installed and applicable

### Part 2: Procure to Pay

- Purchase order, receipt, vendor bill, and 3-way matching
- Vendor advance and clearing
- Vendor return and refund
- Purchase price variance and Anglo-Saxon interim accounts
- Expenses and employee reimbursement without exposing employee identity

### Part 3: Inventory and Logistics

- Automated AVCO/FIFO/Standard valuation
- Receipt, delivery, internal transfer, return, scrap, adjustment, landed cost, and consignment
- Stock Valuation, Stock Input, Stock Output, COGS, price difference, and FX
- Lot/serial traceability and cutoff controls

### Part 4: Manufacturing and Service Operations

- Raw material issue, WIP, finished goods receipt, by-product, scrap, unbuild, and subcontracting
- Standard/actual cost, work-center cost, labor/overhead, variance, and landed cost
- Repair, warranty, customer-owned material, Helpdesk, Quality, and Maintenance boundaries

### Part 5: Assets, Deferrals, and Finance

- Asset acquisition, capitalization, depreciation, modification, disposal, and sale
- Deferred expense and deferred revenue recognition
- Bank/cash/cheque, payment, reconciliation, exchange difference, and write-off
- Budget and analytic entries, noting that budgets may not create GL entries directly

### Part 6: Thailand Localization

- Output/Input VAT, zero-rated/exempt, tax invoice timing, credit note, and tax closing
- WHT purchase/payment flows, PND3, PND53, certificates, and reconciliation
- Thai tax report controls and gaps already identified in ACC-009, ACC-014, and ACC-027

### Part 7: Custom Addon Impact Register

For every installed/local accounting-sensitive addon, record:

- Technical addon name
- Standard flow extended
- Models/methods inherited
- Posting or reconciliation behavior that may change
- Standard versus custom difference
- Duplicate/overlap risk with OCA or Enterprise
- Required regression scenarios
- Evidence status

Priority custom families include payment register extensions, WHT auto-deduction, multi-tax, partner default accounts, account partner settlement, payment default journal, payment auto difference, cheque management, account billing, sale invoice automation, MRP cost extensions, asset customization, and custom reports.

## Matrix Design

`accounting_module_je_matrix.csv` contains one atomic row per posting scenario with these fields:

- Scenario ID
- Module family
- Addon/module name
- Business document
- Trigger/state
- Debit account role
- Credit account role
- Formula
- Hypothetical amount
- VAT impact
- WHT impact
- Stock/SVL impact
- Asset impact
- Analytic impact
- Reconciliation target
- Reversal scenario
- ACC cross-reference
- Evidence status
- UAT ID
- Owner
- Risk
- Source reference

## Standard vs Pain Point Method

Each chapter separates:

- `Standard Odoo 18`: Verified against official Odoo 18 documentation/source.
- `Thai/OCA extension`: Verified against the installed or target branch source.
- `Linkweld custom behavior`: Verified from local source and existing evidence.
- `Pain Point`: A gap, conflict, duplicate extension, missing policy, or unverified posting.
- `Solution`: Standard-first configuration, governance, or a bounded custom action only when standard behavior cannot meet an approved requirement.

## Safety and Privacy

1. Use existing staging evidence only.
2. Do not open confidential transactions merely to obtain a JE example.
3. Do not create, post, reverse, reconcile, export, or run a report.
4. Use hypothetical amounts and generic parties.
5. Do not include credentials, bank identifiers, Tax IDs, personal data, or transaction references.
6. Label every unexecuted behavior as Standard Example, Custom Review Required, or Not Available.
7. All functional execution remains Clone-UAT-only after owner approval.

## Validation

- All installed accounting-sensitive modules are mapped or explicitly excluded with rationale.
- Every posting scenario has balanced hypothetical Debit/Credit totals.
- VAT and WHT examples reconcile mathematically.
- Inventory examples reconcile source document, SVL, interim accounts, COGS, and GL roles.
- Manufacturing examples separate inventory valuation, WIP policy, work-center cost, and analytic cost.
- Asset examples reconcile acquisition cost, accumulated depreciation, NBV, gain/loss, and sale proceeds.
- Every custom addon has a standard-flow comparison and regression scope.
- All links to ACC-001 through ACC-030 resolve.
- DOCX passes structural, privacy, image, and page-render QA when a renderer is available.

## Acceptance Criteria

1. Accounting can identify every business module that may create or alter a JE.
2. Each module has a configuration and policy checklist with an accountable owner.
3. Every material flow includes a balanced formula and hypothetical numeric JE.
4. VAT, WHT, stock, manufacturing, asset, analytic, payment, and reporting dependencies are explicit.
5. Standard Odoo, localization, OCA, and Linkweld custom behavior are not mixed without labels.
6. Every scenario has positive, negative, reversal, access, and regression UAT coverage.
7. No confidential Linkweld transaction data or credentials are included.
8. No Odoo data is created or changed.

## Approved Decisions

- Use a separate companion book linked to the existing Accounting manual.
- Cover Standard, Thai localization, OCA, and Linkweld custom addons that affect Accounting.
- Use formulas plus hypothetical numeric examples based on THB 100,000, VAT 7%, and WHT examples.
- Preserve Evidence-first Read-only restrictions.
- Exclude Developer Mode > Technical UI and all Odoo write/testing actions from documentation evidence collection.
