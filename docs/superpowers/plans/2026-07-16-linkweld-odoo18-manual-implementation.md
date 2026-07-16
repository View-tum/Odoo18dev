# Linkweld Odoo 18 Manual Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce two Thai evidence-based Odoo 18 manuals covering every non-Technical Settings and Configuration menu installed on Linkweld, with field-level emphasis on Accounting and Manufacturing and no database changes.

**Architecture:** Use a read-only evidence pipeline: inventory visible menus, register each configuration with a stable ID, capture the current screen, trace it to existing records, label evidence strength, author Markdown sources, generate DOCX deliverables, and render every page for visual QA. Work is divided into independently reviewable Accounting, Manufacturing, remaining-module, and publishing batches.

**Tech Stack:** Odoo 18 Enterprise staging, in-app Browser read-only automation, Markdown, CSV, PNG, bundled Python `C:\Users\tumsu\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`, `python-docx`, LibreOffice renderer from the Documents skill.

## Global Constraints

- Language: Thai with Odoo technical names in English.
- Evidence mode: Read-only.
- Primary focus: Accounting and Manufacturing.
- Cover every visible business Settings and Configuration menu in installed modules.
- Exclude Developer Mode Technical menus.
- Never create, edit, save, post, confirm, reset, cancel, install, activate, archive, or delete configuration, master data, or transactions.
- Use only existing Linkweld master data and existing transactions as system evidence.
- Never expose passwords, API keys, tokens, unnecessary bank details, or unnecessary personal data.
- Label every claimed outcome as `Confirmed`, `Partially Confirmed`, `Inferred`, `Not Available`, or `Risk`.
- An inferred explanation must never be presented as a confirmed Linkweld outcome.

---

## File Structure

- Create: `manual/linkweld_odoo18/README.md` - scope, safety rules, and production status.
- Create: `manual/linkweld_odoo18/register/configuration_register.csv` - authoritative configuration inventory.
- Create: `manual/linkweld_odoo18/register/evidence_log.csv` - screenshot and record traceability.
- Create: `manual/linkweld_odoo18/register/menu_inventory.csv` - installed-module menu coverage.
- Create: `manual/linkweld_odoo18/evidence/<module>/<configuration_id>/original/` - untouched screenshots grouped by configuration.
- Create: `manual/linkweld_odoo18/evidence/<module>/<configuration_id>/annotated/` - pixel-faithful screenshots with deterministic numbered red rectangular frames and callouts.
- Create: `manual/linkweld_odoo18/source/01_settings_manual_th.md` - Settings Manual source.
- Create: `manual/linkweld_odoo18/source/02_accounting_manufacturing_manual_th.md` - Accounting and Manufacturing Manual source.
- Create: `manual/linkweld_odoo18/scripts/build_linkweld_manuals.py` - deterministic DOCX builder.
- Create: `manual/linkweld_odoo18/tests/test_manual_sources.py` - structural and privacy checks.
- Create: `manual/linkweld_odoo18/output/01_Linkweld_Odoo18_Settings_Manual_TH.docx` - final Settings Manual.
- Create: `manual/linkweld_odoo18/output/02_Linkweld_Odoo18_Accounting_Manufacturing_Manual_TH.docx` - final Accounting and Manufacturing Manual.
- Create: `manual/linkweld_odoo18/qa/` - rendered page images and QA reports; do not deliver as final artifacts.
- Modify: `C:\365_project\TheCool18e\LINKWELD_DEV_HANDOFF.md` - batch completion, evidence gaps, risks, and next action.

## Data Contracts

`configuration_register.csv` columns:

```text
configuration_id,module,menu_path,configuration_name,current_value,evidence_status,business_owner,accounting_impact,manufacturing_impact,stock_impact,tax_impact,change_risk,source_reference,inspection_date,uat_case_id,notes
```

`evidence_log.csv` columns:

```text
evidence_id,configuration_id,evidence_type,file_path,company_context,record_model,record_identifier,record_state,inspection_date,redacted,description
```

`menu_inventory.csv` columns:

```text
module,menu_level_1,menu_level_2,menu_level_3,menu_path,visible,access_result,configuration_id,coverage_status,inspection_date
```

Configuration ID prefixes:

```text
GEN = General Settings and Companies
ACC = Accounting
MRP = Manufacturing
INV = Inventory
PUR = Purchase
SAL = Sales
APR = Approvals
PRJ = Project
HLP = Helpdesk
DOC = Documents
WEB = Website and eCommerce
OTH = remaining installed modules
```

---

### Task 1: Create the Evidence Workspace and Safety Gate

**Files:**
- Create: `manual/linkweld_odoo18/README.md`
- Create: `manual/linkweld_odoo18/register/configuration_register.csv`
- Create: `manual/linkweld_odoo18/register/evidence_log.csv`
- Create: `manual/linkweld_odoo18/register/menu_inventory.csv`

**Interfaces:**
- Consumes: approved design `docs/superpowers/specs/2026-07-16-linkweld-odoo18-manual-design.md`.
- Produces: stable IDs and CSV schemas used by all capture and publishing tasks.

- [x] **Step 1: Create the directory structure**

Create the exact paths listed in File Structure. Do not place screenshots outside `manual/linkweld_odoo18/evidence`.

- [x] **Step 2: Write the safety checklist into README**

Include these mandatory pre-session checks:

```text
1. Confirm staging URL and company context.
2. Confirm no Edit mode is active.
3. Never click Save, Confirm, Post, Reset, Cancel, Install, Activate, Archive, Delete, or an unknown wizard action.
4. Use only navigation, search, filters, grouping, and read-only record opening.
5. Stop and mark Not Available when an action may write data.
6. Redact credentials, tokens, unnecessary bank information, and unnecessary personal data.
7. Finalize the browser session after the evidence batch.
```

- [x] **Step 3: Create CSV files with exact headers**

Write only the headers from Data Contracts. Do not pre-populate invented menu or configuration records.

- [x] **Step 4: Validate workspace structure**

Run:

```powershell
rg --files manual/linkweld_odoo18 | Sort-Object
```

Expected: README and three register CSV files are listed; no DOCX or evidence files exist yet.

- [x] **Step 5: Commit the evidence workspace**

```powershell
git add manual/linkweld_odoo18/README.md manual/linkweld_odoo18/register
git commit -m "docs: initialize Linkweld manual evidence register"
```

### Task 2: Inventory Installed Business Menus

**Files:**
- Modify: `manual/linkweld_odoo18/register/menu_inventory.csv`
- Modify: `manual/linkweld_odoo18/register/configuration_register.csv`

**Interfaces:**
- Consumes: normal Odoo menus visible to the supplied Linkweld staging user.
- Produces: complete non-Technical menu inventory and one configuration ID per configurable menu.

- [x] **Step 1: Open staging in read-only navigation mode**

Authenticate without recording credentials. Do not open Developer Mode Technical menus.

- [x] **Step 2: Inventory module Settings and Configuration menus**

Inspect Accounting, Manufacturing, Inventory, Purchase, Sales, Approvals, Project, Helpdesk, Documents, Website/eCommerce, Barcode, Assets, Budgets, and every other installed business app visible in the app switcher.

- [x] **Step 3: Record access outcomes**

For every menu path, set `access_result` to one of `Accessible`, `No Access`, `Not Installed`, or `Not Visible`. Do not infer access from source code.

- [x] **Step 4: Assign configuration IDs**

Use sequential three-digit IDs such as `ACC-001`, `ACC-002`, and `MRP-001`. Assign IDs only to menus observed in Linkweld.

- [x] **Step 5: Check coverage uniqueness**

Run:

```powershell
$rows = Import-Csv manual/linkweld_odoo18/register/menu_inventory.csv
$rows | Group-Object menu_path | Where-Object Count -gt 1
$rows | Where-Object visible -eq 'True' | Where-Object coverage_status -eq ''
```

Expected: no duplicate menu path rows and no blank coverage status for visible menus.

- [x] **Step 6: Finalize the browser session and commit**

```powershell
git add manual/linkweld_odoo18/register/menu_inventory.csv manual/linkweld_odoo18/register/configuration_register.csv
git commit -m "docs: inventory Linkweld configuration menus"
```

### Task 3: Capture Accounting Settings

**Files:**
- Modify: `manual/linkweld_odoo18/register/configuration_register.csv`
- Modify: `manual/linkweld_odoo18/register/evidence_log.csv`
- Create: `manual/linkweld_odoo18/evidence/accounting/ACC-*/`

**Interfaces:**
- Consumes: Accounting configuration IDs from Task 2.
- Produces: original and annotated navigation/focused images for every visible Accounting Settings section.

- [x] **Step 1: Capture Accounting Settings navigation context**

Open Accounting > Configuration > Settings without changing any field. Capture the full page at readable resolution.

- [x] **Step 2: Capture each visible Settings section**

Capture focused images for fiscal localization, taxes, currencies, customer invoices, vendor bills, payments, bank, analytics, budgets, assets, stock accounting, fiscal periods, and installed custom settings that appear on the page.

- [x] **Step 2A: Create deterministic annotated copies**

Keep every original screenshot unchanged. Create a separate annotated copy with numbered red rectangular frames sized around the relevant target. Each number must map to the manual explanation table. Do not use generative image reconstruction or cover Odoo field text and values.

- [x] **Step 3: Record the current displayed values**

Write exact displayed values into `current_value`. For blank, masked, inaccessible, or ambiguous fields, use `Not Available`; do not click Edit to reveal values.

- [x] **Step 4: Register screenshot evidence**

Create one `evidence_log.csv` row for the original image and one row for its annotated copy. Set `record_model` to `res.config.settings`, `record_state` to `Read-only inspection`, and `redacted` to `True` or `False`.

- [x] **Step 5: Perform the safety check**

Confirm no settings were saved and no success notification indicating a write appeared during the session.

- [x] **Step 6: Finalize the browser session and commit**

```powershell
git add manual/linkweld_odoo18/register manual/linkweld_odoo18/evidence/accounting
git commit -m "docs: capture Linkweld accounting settings"
```

### Task 4: Capture Accounting Configuration Menus

**Files:**
- Modify: `manual/linkweld_odoo18/register/configuration_register.csv`
- Modify: `manual/linkweld_odoo18/register/evidence_log.csv`
- Create: `manual/linkweld_odoo18/evidence/accounting/ACC-*/`

**Interfaces:**
- Consumes: Accounting menu inventory and IDs.
- Produces: configuration evidence for all visible Accounting Configuration menus.

- [ ] **Step 1: Capture organization and localization configuration**

Inspect current Company, fiscal localization, currencies, fiscal positions, account groups, chart of accounts, and tax units when visible.

- [ ] **Step 2: Capture tax configuration**

Inspect taxes, tax groups, tax grids, VAT configuration, WHT-related menus, and installed Thai reports. Open existing records only.

- [ ] **Step 3: Capture journals and payment configuration**

Inspect journals, payment methods, payment terms, outstanding accounts, bank and cash journals, cheque configuration, and installed payment customizations.

- [ ] **Step 4: Capture analytic, budget, and asset configuration**

Inspect analytic plans, analytic accounts, budgets, asset models, depreciation methods, and related visible defaults.

- [ ] **Step 5: Capture closing and reporting configuration**

Inspect lock-date controls, fiscal-year settings, report menus, and report options visible without Technical menus.

- [ ] **Step 6: Label evidence status and risk**

Use `Confirmed` only when the current configuration is directly visible. Use `Risk` in `change_risk` for posted-accounting, tax, valuation, sequence, lock-date, or payment behavior that requires owner approval.

- [ ] **Step 7: Finalize the browser session and commit**

```powershell
git add manual/linkweld_odoo18/register manual/linkweld_odoo18/evidence/accounting
git commit -m "docs: capture Linkweld accounting configuration"
```

### Task 5: Trace Existing Accounting Transactions

**Files:**
- Modify: `manual/linkweld_odoo18/register/evidence_log.csv`
- Modify: `manual/linkweld_odoo18/register/configuration_register.csv`
- Create: `manual/linkweld_odoo18/evidence/accounting/ACC-*/`

**Interfaces:**
- Consumes: existing posted Linkweld transactions and Accounting configuration IDs.
- Produces: configuration-to-transaction and configuration-to-journal evidence.

- [ ] **Step 1: Select existing records only**

Use existing customer invoices, credit notes, vendor bills, refunds, receipts, payments, bank transactions, reconciliations, cheques, assets, budgets, landed costs, and valuation records when available.

- [ ] **Step 2: Capture transaction state and identifiers**

Record model, visible document identifier, state, company, and inspection date. Do not expose unnecessary customer, vendor, bank, or personal details.

- [ ] **Step 3: Trace journal impact**

Open existing journal items from the transaction when the navigation is read-only and safe. Capture account, debit, credit, currency, tax, analytic, and reconciliation effects needed for the manual.

- [ ] **Step 4: Map evidence to configuration IDs**

Connect each evidence row to the configuration responsible for the outcome. If multiple configurations contribute, create separate evidence rows referencing the same screenshot.

- [ ] **Step 5: Record missing evidence honestly**

Set `Partially Confirmed`, `Inferred`, or `Not Available` where existing records do not prove the complete behavior. Do not create a replacement transaction.

- [ ] **Step 6: Finalize the browser session and commit**

```powershell
git add manual/linkweld_odoo18/register manual/linkweld_odoo18/evidence/accounting
git commit -m "docs: trace Linkweld accounting evidence"
```

### Task 6: Capture Manufacturing Settings and Configuration

**Files:**
- Modify: `manual/linkweld_odoo18/register/configuration_register.csv`
- Modify: `manual/linkweld_odoo18/register/evidence_log.csv`
- Create: `manual/linkweld_odoo18/evidence/manufacturing/MRP-*/`

**Interfaces:**
- Consumes: Manufacturing IDs from Task 2 and existing Linkweld manufacturing records.
- Produces: complete visible Manufacturing configuration and outcome evidence.

- [ ] **Step 1: Capture Manufacturing Settings**

Inspect operations, work orders, by-products, subcontracting, planning, product variants, lots/serials, packages, quality, maintenance, costing, and installed custom options visible on the Settings page.

- [ ] **Step 2: Capture configuration menus**

Inspect bills of materials, operations, work centers, work center capacity and costs, product/category costing, routes, lead times, quality control points, maintenance equipment, and custom mold or production configuration that is visible.

- [ ] **Step 3: Trace existing manufacturing orders**

Use existing manufacturing orders to capture component demand, reservation, consumption, finished products, by-products, scrap, work orders, time, and completion state.

- [ ] **Step 4: Trace stock and accounting results**

Capture existing stock moves, valuation layers, product cost, WIP or variance behavior, and journal entries when they exist and can be opened safely.

- [ ] **Step 5: Label evidence and risk**

Use `Risk` for costing method, valuation, routes, consumption, by-product cost share, work center cost, and any configuration that can change stock or financial values.

- [ ] **Step 6: Finalize the browser session and commit**

```powershell
git add manual/linkweld_odoo18/register manual/linkweld_odoo18/evidence/manufacturing
git commit -m "docs: capture Linkweld manufacturing configuration"
```

### Task 7: Capture Inventory, Purchase, and Sales Configuration

**Files:**
- Modify: `manual/linkweld_odoo18/register/configuration_register.csv`
- Modify: `manual/linkweld_odoo18/register/evidence_log.csv`
- Create: `manual/linkweld_odoo18/evidence/inventory/INV-*/`
- Create: `manual/linkweld_odoo18/evidence/purchase/PUR-*/`
- Create: `manual/linkweld_odoo18/evidence/sales/SAL-*/`

**Interfaces:**
- Consumes: menu IDs from Task 2.
- Produces: cross-module configuration evidence required by Accounting and Manufacturing.

- [ ] **Step 1: Capture Inventory configuration**

Inspect warehouses, locations, operation types, routes, rules, product categories, valuation methods, removal strategies, putaway rules, packages, lots/serials, replenishment, landed costs, and barcode settings.

- [ ] **Step 2: Capture Purchase configuration**

Inspect vendor settings, purchase agreements, approvals, control policy, 3-way matching, units of measure, lead times, bill control, and routes that affect receipts or manufacturing supply.

- [ ] **Step 3: Capture Sales configuration**

Inspect quotations, order confirmation, invoicing policy, pricelists, discounts, units of measure, routes, delivery, customer accounts, and installed custom order configuration.

- [ ] **Step 4: Trace existing records**

Use existing receipts, deliveries, purchase orders, sales orders, replenishment records, and stock valuation outcomes. Do not create or confirm records.

- [ ] **Step 5: Finalize the browser session and commit**

```powershell
git add manual/linkweld_odoo18/register manual/linkweld_odoo18/evidence/inventory manual/linkweld_odoo18/evidence/purchase manual/linkweld_odoo18/evidence/sales
git commit -m "docs: capture Linkweld supply chain configuration"
```

### Task 8: Capture Remaining Installed Module Configuration

**Files:**
- Modify: `manual/linkweld_odoo18/register/configuration_register.csv`
- Modify: `manual/linkweld_odoo18/register/evidence_log.csv`
- Create: `manual/linkweld_odoo18/evidence/remaining/<prefix>-*/`

**Interfaces:**
- Consumes: remaining menu inventory rows from Task 2.
- Produces: complete coverage of visible non-Technical configuration menus.

- [ ] **Step 1: Capture remaining Settings pages**

Inspect Approvals, Project, Helpdesk, Documents, Website/eCommerce, Assets, Budgets, Barcode, Renting, and every remaining installed business module.

- [ ] **Step 2: Capture Configuration menus and existing outcomes**

Open existing configuration and transaction records only. Apply the same evidence status and privacy rules used for Accounting and Manufacturing.

- [ ] **Step 3: Run the menu coverage check**

```powershell
$rows = Import-Csv manual/linkweld_odoo18/register/menu_inventory.csv
$rows | Where-Object visible -eq 'True' | Where-Object coverage_status -ne 'Complete'
```

Expected: zero rows, or rows explicitly marked `No Access` or `Not Available` with notes.

- [ ] **Step 4: Finalize the browser session and commit**

```powershell
git add manual/linkweld_odoo18/register manual/linkweld_odoo18/evidence/remaining
git commit -m "docs: complete Linkweld module configuration evidence"
```

### Task 9: Author the Settings Manual Source

**Files:**
- Create: `manual/linkweld_odoo18/source/01_settings_manual_th.md`
- Test: `manual/linkweld_odoo18/tests/test_manual_sources.py`

**Interfaces:**
- Consumes: configuration register, menu inventory, evidence log, and screenshots.
- Produces: complete Thai Settings Manual Markdown source.

- [ ] **Step 1: Write source validation tests**

Create tests that assert the Settings source contains all configuration IDs from `menu_inventory.csv`, contains no credential markers such as `PW:`, `password=`, `api_key`, or `session_id`, and labels every configuration with an evidence status.

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
& 'C:\Users\tumsu\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest manual/linkweld_odoo18/tests/test_manual_sources.py -q
```

Expected: FAIL because `01_settings_manual_th.md` does not exist.

- [ ] **Step 3: Author the Settings Manual**

Use the approved chapter structure. For each configuration include purpose, current value, enabled effect, disabled effect, dependencies, impacts, risk, evidence status, screenshot path, source, and UAT case.

- [ ] **Step 4: Run tests and verify pass**

Expected: all Settings source coverage and privacy tests pass.

- [ ] **Step 5: Commit**

```powershell
git add manual/linkweld_odoo18/source/01_settings_manual_th.md manual/linkweld_odoo18/tests/test_manual_sources.py
git commit -m "docs: author Linkweld Odoo settings manual"
```

### Task 10: Author the Accounting and Manufacturing Manual Source

**Files:**
- Create: `manual/linkweld_odoo18/source/02_accounting_manufacturing_manual_th.md`
- Modify: `manual/linkweld_odoo18/tests/test_manual_sources.py`

**Interfaces:**
- Consumes: Accounting, Manufacturing, Inventory, Purchase, and Sales evidence.
- Produces: complete Thai Accounting and Manufacturing Markdown source with cross-module traces.

- [ ] **Step 1: Extend source validation tests**

Assert every `ACC-*` and `MRP-*` configuration ID appears in the source, every `Confirmed` result references at least one evidence file, and every `Inferred` result includes an Odoo 18 or OCA source URL.

- [ ] **Step 2: Run tests and verify failure**

Expected: FAIL because `02_accounting_manufacturing_manual_th.md` does not exist.

- [ ] **Step 3: Author Accounting chapters**

Follow the approved Accounting chapter sequence and include transaction-to-journal examples only from existing records.

- [ ] **Step 4: Author Manufacturing chapters**

Follow the approved Manufacturing chapter sequence and include existing manufacturing-order, stock-move, valuation, cost, and journal evidence where available.

- [ ] **Step 5: Add UAT and go-live controls**

For each configuration ID, provide role, precondition using approved UAT data, test action for the Vietnam team, expected result, accounting or stock control, and sign-off owner. These are instructions only and must not be executed on primary staging.

- [ ] **Step 6: Run tests and verify pass**

Expected: all Accounting, Manufacturing, evidence, source-reference, and privacy tests pass.

- [ ] **Step 7: Commit**

```powershell
git add manual/linkweld_odoo18/source/02_accounting_manufacturing_manual_th.md manual/linkweld_odoo18/tests/test_manual_sources.py
git commit -m "docs: author Linkweld accounting manufacturing manual"
```

### Task 11: Build and Visually Verify DOCX Deliverables

**Files:**
- Create: `manual/linkweld_odoo18/scripts/build_linkweld_manuals.py`
- Create: `manual/linkweld_odoo18/output/01_Linkweld_Odoo18_Settings_Manual_TH.docx`
- Create: `manual/linkweld_odoo18/output/02_Linkweld_Odoo18_Accounting_Manufacturing_Manual_TH.docx`
- Create: `manual/linkweld_odoo18/qa/settings/`
- Create: `manual/linkweld_odoo18/qa/accounting_manufacturing/`

**Interfaces:**
- Consumes: both Markdown sources, register CSV files, and evidence PNGs.
- Produces: two styled DOCX files with headings, tables, captions, page numbers, and screenshots.

- [ ] **Step 1: Implement deterministic document generation**

The builder must expose:

```python
def build_manual(source_path: Path, output_path: Path, document_title: str) -> None:
    """Build one DOCX from a validated Markdown source and local evidence images."""

def add_evidence_image(document, image_path: Path, caption: str) -> None:
    """Insert a scaled image and keep the caption with the image."""

def add_configuration_table(document, rows: list[tuple[str, str]]) -> None:
    """Insert a two-column configuration table with a repeating header."""
```

Use A4 portrait, readable Thai fonts, consistent heading levels, 8-point-or-greater captions, page numbering, and table rows that do not clip or overlap.

- [ ] **Step 2: Generate both DOCX files**

```powershell
& 'C:\Users\tumsu\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' manual/linkweld_odoo18/scripts/build_linkweld_manuals.py
```

Expected: both DOCX files exist and are non-empty.

- [ ] **Step 3: Run source and privacy validation**

```powershell
& 'C:\Users\tumsu\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest manual/linkweld_odoo18/tests/test_manual_sources.py -q
```

Expected: PASS.

- [ ] **Step 4: Render the Settings Manual**

```powershell
& 'C:\Users\tumsu\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' 'C:\Users\tumsu\.codex\plugins\cache\openai-primary-runtime\documents\26.709.11516\skills\documents\render_docx.py' manual/linkweld_odoo18/output/01_Linkweld_Odoo18_Settings_Manual_TH.docx --output_dir manual/linkweld_odoo18/qa/settings
```

Expected: one `page-*.png` per DOCX page.

- [ ] **Step 5: Render the Accounting and Manufacturing Manual**

```powershell
& 'C:\Users\tumsu\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' 'C:\Users\tumsu\.codex\plugins\cache\openai-primary-runtime\documents\26.709.11516\skills\documents\render_docx.py' manual/linkweld_odoo18/output/02_Linkweld_Odoo18_Accounting_Manufacturing_Manual_TH.docx --output_dir manual/linkweld_odoo18/qa/accounting_manufacturing
```

Expected: one `page-*.png` per DOCX page.

- [ ] **Step 6: Inspect every rendered page**

Check every page at 100 percent for missing Thai glyphs, clipped text, overlapping images, broken tables, orphaned captions, unreadable screenshots, incorrect page breaks, and exposed sensitive information. Correct the source or builder and repeat generation and rendering until all pages pass.

- [ ] **Step 7: Run final file checks and commit**

```powershell
Get-Item manual/linkweld_odoo18/output/*.docx | Select-Object Name,Length
git add manual/linkweld_odoo18/scripts manual/linkweld_odoo18/output manual/linkweld_odoo18/tests
git commit -m "docs: publish Linkweld Odoo 18 manuals"
```

### Task 12: Final Reconciliation and Handoff

**Files:**
- Modify: `manual/linkweld_odoo18/README.md`
- Modify: `C:\365_project\TheCool18e\LINKWELD_DEV_HANDOFF.md`

**Interfaces:**
- Consumes: final register, evidence, tests, renders, and DOCX files.
- Produces: evidence-based completion status and next action for the Linkweld Dev task.

- [ ] **Step 1: Reconcile coverage**

Confirm every visible non-Technical configuration menu has a configuration ID and one of the five evidence statuses. Count status totals and record them in README.

- [ ] **Step 2: Reconcile privacy and write safety**

Confirm no credential strings exist in source, registers, image filenames, or handoff. Confirm the audit log contains no claimed Save, Post, Confirm, Install, Activate, Archive, Delete, or configuration-change action.

- [ ] **Step 3: Update handoff**

Record completed modules, files produced, validation results, evidence gaps, high-risk settings, and the next owner action. State explicitly that no Odoo configuration, master data, or transaction was created or modified.

- [ ] **Step 4: Commit the final README**

```powershell
git add manual/linkweld_odoo18/README.md
git commit -m "docs: finalize Linkweld manual evidence status"
```

- [ ] **Step 5: Deliver the two DOCX files**

Provide links to the final Settings Manual and Accounting/Manufacturing Manual. Do not link QA render images unless requested.

---

## Verification Summary

The complete execution is acceptable only when:

```text
1. Every visible non-Technical configuration menu is inventoried.
2. Accounting and Manufacturing configurations have field-level explanations.
3. Confirmed outcomes link to existing Linkweld evidence.
4. Missing outcomes are labeled Partially Confirmed, Inferred, or Not Available.
5. No settings, master data, or transactions were created or modified.
6. Privacy tests pass.
7. Both DOCX files render without visual defects.
8. LINKWELD_DEV_HANDOFF.md reflects the final evidence status.
```
