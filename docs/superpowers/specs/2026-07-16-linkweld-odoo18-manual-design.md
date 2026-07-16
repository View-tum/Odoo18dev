# Linkweld Odoo 18 Configuration and User Manual Design

## Document Control

- Project: Linkweld (Thailand) Co., Ltd.
- System: Odoo 18 Enterprise staging
- Design date: 2026-07-16
- Language: Thai with Odoo technical names in English
- Evidence mode: Read-only
- Primary focus: Accounting and Manufacturing

## Objective

Create two evidence-based Thai manuals that document every business-facing Settings, Configuration, and master-configuration menu available in the modules installed on Linkweld Odoo 18. The manuals must explain the current value, its purpose, the effect of enabling or disabling it, dependencies, risks, and the observable outcome in existing transactions.

The work must preserve the staging database. No settings, master data, or transactions may be created, edited, saved, posted, confirmed, reset, cancelled, installed, activated, archived, or deleted for evidence collection.

## Deliverables

1. `01_Linkweld_Odoo18_Settings_Manual_TH.docx`
2. `02_Linkweld_Odoo18_Accounting_Manufacturing_Manual_TH.docx`
3. Screenshot evidence folders organized by module and configuration ID
4. Configuration Register recording evidence status, impact, owner, and UAT coverage
5. Updated `LINKWELD_DEV_HANDOFF.md` after each completed work batch

## Scope

### Included

- Settings pages for every installed business module
- Configuration menus and submenus visible without Developer Mode
- Business master configuration such as companies, users, accounts, taxes, journals, payment terms, warehouses, locations, operation types, routes, bills of materials, work centers, and quality control points
- Installed custom-addon configuration visible in the normal user interface
- Existing master data and existing transactions that demonstrate configuration outcomes
- Related journal entries, reports, stock moves, valuation layers, manufacturing orders, and costs when existing records provide evidence
- Odoo 18 and OCA references for behavior that cannot be proven from existing Linkweld records

### Excluded

- Developer Mode Technical menus
- Technical system parameters, scheduled actions, automation rules, report actions, security rules, or mail servers that are only available under Technical menus
- Creation or modification of settings, master data, transactions, users, access rights, or accounting records
- Installation, upgrade, activation, or removal of addons
- Fabricated screenshots or test transactions presented as Linkweld evidence

## Priority

### Priority 1: Accounting

Document every visible Accounting Settings and Configuration menu. Explain effects on accounts, taxes, journals, payments, reconciliation, assets, budgets, analytic accounting, VAT, WHT, lock dates, reports, stock valuation, and audit controls. Existing transactions must be traced to journal entries or reports when access and evidence permit.

### Priority 1: Manufacturing

Document every visible Manufacturing Settings and Configuration menu. Explain effects on bills of materials, operations, work centers, work orders, planning, consumption, by-products, subcontracting, costing, WIP, stock moves, scrap, quality, maintenance, and accounting valuation. Existing manufacturing orders must be used as evidence when available.

### Priority 2

- Inventory
- Purchase
- Sales

These modules must be fully documented because their configuration drives Accounting and Manufacturing outcomes.

### Priority 3

Document all visible configuration in remaining installed modules, including Approvals, Project, Helpdesk, Documents, Website, eCommerce, Barcode, Assets, Budgets, and other installed business apps.

## Manual 1: Settings Manual

1. Scope, navigation, and read-only evidence rules
2. General Settings
3. Users, Companies, and Multi-company
4. Accounting Settings
5. Manufacturing Settings
6. Inventory Settings
7. Purchase Settings
8. Sales Settings
9. Project, Helpdesk, Documents, and Approvals Settings
10. Website, eCommerce, and remaining installed-module Settings
11. Cross-module dependency matrix
12. Enabled settings without complete transaction evidence
13. Disabled settings and expected effects
14. Configuration risks and go-live recommendations

## Manual 2: Accounting and Manufacturing Manual

### Accounting chapters

1. Accounting policy and Standard Odoo versus pain points
2. Company, fiscal localization, and currencies
3. Chart of accounts and account groups
4. Taxes, VAT, WHT, tax grids, and tax reports
5. Journals, sequences, and payment methods
6. Bank, cash, exchange rates, and exchange differences
7. Customer invoices and credit notes
8. Vendor bills and refunds
9. Receipts, payments, partial payments, and grouped payments
10. Bank reconciliation and outstanding accounts
11. Cheque management
12. Analytic accounting and budgets
13. Assets and depreciation
14. Inventory valuation, landed costs, and cost of goods sold
15. Closing, lock dates, and period controls
16. Financial, VAT, WHT, and management reports
17. Access control and segregation of duties
18. Reversal, correction, error handling, and audit trail

### Manufacturing chapters

1. Manufacturing policy and module relationships
2. Product, unit of measure, category, and costing configuration
3. Bills of materials and variants
4. Operations, work centers, and work orders
5. Manufacturing order defaults and consumption behavior
6. Lots, serial numbers, packages, and traceability
7. Routes, replenishment, make-to-order, and subcontracting
8. By-products, scrap, unbuild, and returns
9. Quality and maintenance integration when installed
10. Manufacturing costs, WIP, variance, stock valuation, and journal impact
11. Planning, capacity, lead time, and performance reporting
12. Existing manufacturing transaction walkthroughs

### Control chapters

1. Configuration-to-transaction traceability matrix
2. UAT test cases for the Odoo Vietnam team
3. Go-live configuration checklist
4. Known gaps, risks, and decisions requiring owner approval

## Configuration Entry Template

Each configuration entry must contain:

1. Configuration ID and title
2. Module and menu path
3. Purpose and business owner
4. Screenshot of the current Linkweld configuration
5. Current Linkweld value
6. Effect when enabled or selected
7. Effect when disabled or changed
8. Dependencies and cross-module behavior
9. Accounting, tax, stock, manufacturing, document, and reporting impact
10. Existing transaction evidence
11. Existing journal entry, stock move, valuation, cost, or report evidence
12. Change risk and rollback consideration
13. Evidence status
14. UAT test case and expected result
15. Source reference and inspection date

## Evidence Status

- `Confirmed`: Configuration and resulting behavior are visible in Linkweld.
- `Partially Confirmed`: Configuration is visible, but result evidence is incomplete.
- `Inferred`: Behavior is based on Odoo 18 or OCA documentation because Linkweld has no suitable existing record.
- `Not Available`: Required data or access is unavailable.
- `Risk`: The setting must not be changed without Accounting, Manufacturing, or project-owner approval.

An inferred explanation must never be presented as a confirmed Linkweld outcome.

## Screenshot Standard

- Capture a navigation-context image and a focused configuration image.
- Capture list and form views when both are needed to understand the configuration.
- Use callout numbers without obscuring fields or values.
- Record company context and inspection date in the caption.
- Redact passwords, tokens, unnecessary bank details, and unnecessary personal information.
- Do not enter Edit mode when the page can be inspected in read-only mode.
- Do not click actions that may save, install, activate, confirm, post, reset, cancel, archive, or delete data.
- Use existing outcomes only. When no outcome exists, document the expected behavior and evidence limitation without generating replacement data.

## Read-only Safety Controls

1. Maintain a prohibited-action list before each capture session.
2. Use navigation, filters, search, grouping, and record opening only when these do not persist business data.
3. Avoid any wizard or button with uncertain side effects.
4. Stop and record `Not Available` when a screen cannot be inspected safely.
5. Do not expose credentials or secrets in screenshots, documents, logs, or handoff files.
6. Close the browser session after each evidence batch.

## Research and Evidence Workflow

1. Inventory installed modules and visible business menus.
2. Build the Configuration Register and assign configuration IDs.
3. Capture Settings and Configuration pages module by module.
4. Trace each configuration to existing master data and transactions.
5. Capture existing output evidence where available.
6. Validate version-sensitive explanations against official Odoo 18 documentation and OCA only when relevant.
7. Draft manual chapters and label evidence status.
8. Render both DOCX files to PNG and inspect every page for layout defects.
9. Correct defects, repeat rendering, and run final privacy review.
10. Update the handoff with completed scope, evidence gaps, risks, and next actions.

## Acceptance Criteria

- Every visible non-Technical Settings and Configuration menu in installed modules is listed in the Configuration Register.
- Accounting and Manufacturing entries include field-level explanations and downstream impact where applicable.
- Every screenshot is traceable to Linkweld staging, an existing record, and an inspection date.
- No test master data, transaction, or configuration change is created.
- Each claimed outcome is labeled according to evidence strength.
- UAT cases identify action, expected result, role, and related configuration ID.
- Both manuals render cleanly with readable Thai text, screenshots, tables, headers, footers, and navigation.
- Credentials, secrets, and unnecessary sensitive information are absent from the deliverables.

## Delivery Sequence

1. Accounting Settings and Configuration
2. Manufacturing Settings and Configuration
3. Inventory
4. Purchase
5. Sales
6. Remaining installed modules
7. Cross-module traceability and UAT consolidation
8. Final DOCX rendering, review, and handoff

## Approved Decisions

- Use Evidence-first Read-only methodology.
- Produce two separate manuals.
- Cover every visible configuration menu in every installed module.
- Prioritize Accounting and Manufacturing.
- Exclude Developer Mode Technical menus.
- Never create or modify master data, configuration, or transactions for testing.
