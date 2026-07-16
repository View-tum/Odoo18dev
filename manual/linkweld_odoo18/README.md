# Linkweld Odoo 18 Manual Evidence Workspace

## Purpose

This workspace contains read-only evidence and source material for two Thai manuals:

1. `01_Linkweld_Odoo18_Settings_Manual_TH.docx`
2. `02_Linkweld_Odoo18_Accounting_Manufacturing_Manual_TH.docx`

The manuals cover every visible business Settings and Configuration menu in the modules installed on Linkweld Odoo 18 Enterprise. Accounting and Manufacturing are the primary focus. Developer Mode Technical menus are excluded.

## Read-only Safety Checklist

Complete these checks before every evidence session:

1. Confirm the staging URL and company context.
2. Confirm no Edit mode is active.
3. Never click Save, Confirm, Post, Reset, Cancel, Install, Activate, Archive, Delete, or an unknown wizard action.
4. Use only navigation, search, filters, grouping, and read-only record opening.
5. Stop and mark `Not Available` when an action may write data.
6. Redact credentials, tokens, unnecessary bank information, and unnecessary personal data.
7. Finalize the browser session after the evidence batch.

## Prohibited Actions

- Do not create or modify Settings.
- Do not create or modify master data.
- Do not create, confirm, post, reset, cancel, archive, or delete transactions.
- Do not install, upgrade, activate, or remove addons.
- Do not use Developer Mode Technical menus.
- Do not fabricate screenshots or present expected behavior as confirmed Linkweld evidence.

## Evidence Status

- `Confirmed`: Configuration and resulting behavior are visible in Linkweld.
- `Partially Confirmed`: Configuration is visible, but result evidence is incomplete.
- `Inferred`: Behavior is supported by Odoo 18 or OCA references but not by a suitable existing Linkweld transaction.
- `Not Available`: Required data or access is unavailable.
- `Risk`: The setting must not be changed without owner approval.

## Workspace Layout

- `register/configuration_register.csv`: authoritative configuration inventory.
- `register/evidence_log.csv`: screenshot and existing-record traceability.
- `register/menu_inventory.csv`: installed-module menu coverage.
- `evidence/<module>/<configuration_id>/`: screenshot evidence.
- `source/`: Thai Markdown manual sources.
- `output/`: final DOCX deliverables.
- `qa/`: render output used only for quality review.

## Current Status

- Design approved.
- Implementation plan approved for execution.
- Evidence workspace initialized.
- Business menu inventory completed on 2026-07-16.
- Registered 158 visible menu paths: 154 configuration or master-configuration entries and 4 installed apps with no separate Configuration menu.
- Accounting register: 30 entries.
- Manufacturing register: 5 entries, including Products, Product Variants, Bills of Materials, and Lots/Serial Numbers.
- No duplicate menu paths or configuration IDs were found.
- Accounting Settings (`ACC-001`) evidence completed on 2026-07-16.
- Captured 13 untouched originals, 13 deterministic numbered rectangular-frame copies, and a structured DOM extract covering 19 sections and 60 setting boxes.
- Detailed Thai chapter: `source/ACC-001_accounting_settings_th.md`.
- Payment Terms (`ACC-002`) evidence completed on 2026-07-16.
- Captured 11 untouched originals, 11 deterministic numbered rectangular-frame copies, all 104 active terms, all 107 due-rule lines, and a name-to-rule risk analysis.
- Confirmed 80 terms are configured as 100% due 0 days after invoice date; 70 names were flagged for business-owner review, not automatically classified as incorrect.
- Detailed Thai chapter: `source/ACC-002_payment_terms_th.md`.
- Follow-up Levels (`ACC-003`) evidence completed on 2026-07-16.
- Captured 5 untouched originals, 5 deterministic numbered rectangular-frame copies, and a structured extract covering both existing levels and all visible notification/activity options.
- Confirmed both levels are manual: 7 Days uses Email + Letter with Attach Invoices; First reminder email uses Email with its named template. Automatic and Schedule Activity are disabled for both.
- Detailed Thai chapter: `source/ACC-003_follow_up_levels_th.md`.
- Incoterms (`ACC-004`) evidence completed on 2026-07-16.
- Captured 2 untouched originals, 2 deterministic numbered rectangular-frame copies, and a structured extract covering all 11 active standard Incoterms.
- Confirmed the Linkweld list matches the Odoo 18 standard set: EXW, FCA, FAS, FOB, CFR, CIF, CPT, CIP, DPU, DAP, and DDP.
- Detailed Thai chapter: `source/ACC-004_incoterms_th.md`.
- Add a Bank Account (`ACC-005`) evidence completed on 2026-07-16.
- Captured 1 untouched original, 1 deterministic numbered rectangular-frame copy, and a structured extract of the initial `Search for an institution` window.
- Confirmed 11 institution rows are visible, search is blank, no institution is selected, `Connect` is disabled, and `Cancel` is enabled.
- Detailed Thai chapter: `source/ACC-005_add_bank_account_th.md`.
- Reconciliation Models (`ACC-006`) evidence completed on 2026-07-16.
- Captured 4 untouched originals, 4 deterministic numbered rectangular-frame copies, and a structured extract covering all 5 models and 3 representative forms.
- Confirmed Auto-validate is enabled for Invoices/Bills Perfect Match and Bank Fees. Bank Fees uses Label Contains `bank fees` and posts 100% to account `560202` when its conditions match.
- Detailed Thai chapter: `source/ACC-006_reconciliation_models_th.md`.
- Online Synchronization (`ACC-007`) evidence completed on 2026-07-16.
- Captured 2 untouched originals, 2 deterministic numbered rectangular-frame copies, and a structured extract covering all 3 records and one representative form.
- Confirmed all 3 records have blank Name and Provider Type and are Not Connected. The representative record has Automatic synchronization enabled but no Next synchronization, expiry date, or account mapping.
- Detailed Thai chapter: `source/ACC-007_online_synchronization_th.md`.
- Chart of Accounts (`ACC-008`) evidence completed on 2026-07-16.
- Captured 4 untouched originals, 4 deterministic numbered rectangular-frame copies, and a structured extract covering 353 active company-scoped accounts, account-type counts, and 3 ACC-001 risk-reference accounts.
- Confirmed 160001 is Current Assets, 120100 is Current Liabilities, and 410000 is Other Income. Their broad type categories are plausible, but their names/purposes do not confirm suitability for Deferred Expense, Deferred Revenue, and Stock Income settings.
- Detailed Thai chapter: `source/ACC-008_chart_of_accounts_th.md`.
- Taxes (`ACC-009`) evidence completed on 2026-07-16.
- Captured 5 untouched originals, 5 deterministic numbered rectangular-frame copies, and a structured extract covering 29 active taxes, rate/type counts, candidate selection, and 4 representative VAT/WHT configurations.
- Confirmed VAT 7% accounts/grids and zero-rated output base grids. Company WHT 1% is a -1% purchase tax to account 232000 but has no visible tax grids, so PND3/PND53 inclusion remains unconfirmed until Clone-UAT report reconciliation.
- Detailed Thai chapter: `source/ACC-009_taxes_th.md`.
- Journals (`ACC-010`) evidence completed on 2026-07-16.
- Captured 4 untouched privacy-safe originals, 4 deterministic numbered rectangular-frame copies, and a sanitized structured extract covering 29 active journals, three safe forms, and one redacted bank-journal summary.
- Confirmed Vendor Bills defaults to 510000 Cost of Revenue, representative Sales/Purchase/Misc journals have Secure Posted Entries with Hash disabled and Auto-Check on Post enabled, and the Generic Bank payment methods require privacy-safe Outstanding Account regression.
- Detailed Thai chapter: `source/ACC-010_journals_th.md`.
- Currencies (`ACC-011`) evidence completed on 2026-07-16.
- Captured 5 untouched originals, 5 deterministic numbered rectangular-frame copies, and a company-scoped structured extract covering all 8 active currencies plus CNY/EUR/THB/USD forms and rate history.
- Confirmed THB is the company currency. AED and JPY are active with blank Last Update and displayed Unit per THB 1.000000; rate dates do not prove provider refresh, and ACC-001 remains configured for a manual update interval.
- Detailed Thai chapter: `source/ACC-011_currencies_th.md`.
- Fiscal Positions (`ACC-012`) evidence completed on 2026-07-16.
- Captured 1 untouched original, 1 deterministic numbered rectangular-frame copy, and a company-scoped extract confirming zero active Fiscal Positions and zero active tax/account mappings.
- No form could be sampled because no active record exists. This does not prove Fiscal Positions are unnecessary; cross-border, export, exempt, WHT, Partner assignment, and historical inactive records require Fit-gap and Clone-UAT.
- Detailed Thai chapter: `source/ACC-012_fiscal_positions_th.md`.
- Journal Groups / Multi-ledger (`ACC-013`) evidence completed on 2026-07-16.
- Captured 1 untouched original, 1 deterministic numbered rectangular-frame copy, and a company-scoped extract confirming zero `account.journal.group` records and zero Excluded Journal relationships.
- The actual page title is Multi-ledger and the inspected schema has Ledger group, Company, Excluded Journals, and Sequence but no Active or Included Journals field. No report was run, so Local GAAP/IFRS/Fiscal output remains unverified.
- Detailed Thai chapter: `source/ACC-013_journal_groups_th.md`.
- Tax Groups (`ACC-014`) evidence completed on 2026-07-16 through a read-only direct standard action because the developer-hidden menu is not visible to this user.
- Captured 4 untouched privacy-safe originals, 4 deterministic numbered rectangular-frame copies, and a company-scoped extract covering all 6 Tax Groups plus VAT 7%, TAX 1%, and Taxes forms.
- All 6 groups have blank Tax Payable, Tax Receivable, Tax Advance, Preceding Subtotal, and PoS receipt label fields. This is a Tax Closing configuration risk, not a proven defect until Clone-UAT closing/report reconciliation.
- Detailed Thai chapter: `source/ACC-014_tax_groups_th.md`.
- Tax Units (`ACC-015`) evidence completed on 2026-07-16 through a read-only direct standard action because the developer-hidden menu is not visible to this user.
- Captured 1 untouched privacy-safe original, 1 deterministic numbered rectangular-frame copy, and a company-scoped extract confirming zero Tax Units, zero member relationships, and no Tax ID read.
- No form or report was opened. Fiscal Position synchronization was not called; local Odoo source shows that action can delete/recreate generated Fiscal Positions and change Partner assignments, so it is restricted to approved Clone UAT.
- Detailed Thai chapter: `source/ACC-015_tax_units_th.md`.
- Account Tags (`ACC-016`) evidence completed on 2026-07-16 through a read-only direct standard action because the developer-hidden menu is not visible to this user.
- Captured 4 untouched privacy-safe originals, 4 deterministic numbered rectangular-frame copies, and an extract covering all 33 active tags, 15 complete Thailand positive/negative tax-tag pairs, and aggregate Account/Tax Repartition/Product usage.
- Pair structure is complete, but Tax Return behavior remains unverified. Only 2 accessible Accounts use any tag and Operating Activities usage is 0, so Cash Flow classification requires an approved mapping and Clone-UAT reconciliation.
- Detailed Thai chapter: `source/ACC-016_account_tags_th.md`.
- Next evidence batch: Accounting Configuration menu `ACC-017` Account Groups, followed by existing-transaction traceability.
- No Odoo configuration, master data, or transaction has been created or modified.
