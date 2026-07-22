# Linkweld Accounting Control and Journal Entry Playbook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a Thai Accounting Control & JE Playbook covering every Linkweld Odoo 18 accounting-sensitive Standard, Thai localization, OCA, and custom addon, then mark the completed Config Manual rows in the implementation-plan workbook.

**Architecture:** Use two auditable registers as the source of truth: a module inventory classifies every accounting-sensitive addon, and an atomic JE matrix records each posting scenario. A deterministic Python builder composes the Markdown into a Word companion book, while validation tests check module coverage, balanced hypothetical entries, VAT/WHT arithmetic, links, privacy, and document structure. A separate artifact-tool script edits only the Status cells in a preserved copy of the supplied Excel workbook and verifies the formula-driven dashboard.

**Tech Stack:** Markdown, CSV, JSON, Python 3.13, python-docx, Node.js tests, `@oai/artifact-tool` 2.8.6+, DOCX OOXML/render tools, Odoo 18 official documentation/source, local addon manifests/source.

## Global Constraints

- Odoo version is 18 Enterprise; verify version-sensitive behavior against official Odoo 18 documentation/source, with OCA/local source secondary.
- Evidence-first Read-only: no setting, master data, transaction, report, journal entry, posting, reconciliation, module, user, or access change.
- Exclude Developer Mode > Technical UI.
- Use formulas plus hypothetical THB 100,000, VAT 7%, and WHT examples; never copy confidential transaction amounts.
- Label each scenario `Confirmed Linkweld`, `Partially Confirmed`, `Standard Example`, `Custom Review Required`, or `Not Available`.
- Standard-first; explain Standard Odoo versus Thai/OCA/custom behavior and pain point.
- Never include credentials, bank-account numbers, Tax IDs, partner identity, personal data, or confidential document references.
- Preserve unrelated worktree changes and commit only files belonging to the task.
- Preserve the original Excel workbook; export the completed copy as `C:\Users\tumsu\Downloads\Linkweld_Odoo18_Implementation_Plan_Updated.xlsx`.

## File Structure

- Create `manual/linkweld_odoo18/register/accounting_sensitive_module_inventory.csv`: one row per included or explicitly excluded addon/module.
- Create `manual/linkweld_odoo18/register/accounting_module_je_matrix.csv`: one row per atomic posting/control scenario.
- Create `manual/linkweld_odoo18/source/03_accounting_control_je_playbook_th.md`: authored Thai companion-book source.
- Create `manual/linkweld_odoo18/scripts/build_accounting_je_playbook.py`: deterministic Markdown-to-DOCX builder.
- Create `manual/linkweld_odoo18/scripts/update_implementation_plan_status.mjs`: artifact-tool workbook updater and verifier.
- Create `manual/linkweld_odoo18/tests/test_accounting_je_playbook.py`: register, arithmetic, coverage, link, privacy, and DOCX tests.
- Create `manual/linkweld_odoo18/output/03_Linkweld_Odoo18_Accounting_Control_JE_Playbook_TH.docx`: final companion book.
- Modify `manual/linkweld_odoo18/source/02_accounting_manual_th.md`: add companion-book cross-reference only.
- Modify `manual/linkweld_odoo18/README.md`: add deliverables, scope, validation, and status.
- Modify `C:\365_project\TheCool18e\LINKWELD_DEV_HANDOFF.md`: record final evidence, limitations, outputs, and no-write confirmation.
- Export `C:\Users\tumsu\Downloads\Linkweld_Odoo18_Implementation_Plan_Updated.xlsx`: preserve all sheets/styles/formulas; update only `03_Config_Manual!H5:H13` to `Complete`.

---

### Task 1: Build the Accounting-Sensitive Module Inventory

**Files:**
- Create: `manual/linkweld_odoo18/register/accounting_sensitive_module_inventory.csv`
- Modify: `manual/linkweld_odoo18/tests/test_accounting_je_playbook.py`

**Interfaces:**
- Consumes: local addon manifests/source, existing addon-audit sections in `LINKWELD_DEV_HANDOFF.md`, and Odoo 18 installed-feature evidence.
- Produces: CSV columns `module_name,module_family,module_origin,installed_or_local,status,standard_flow_extended,accounting_effect,evidence_reference,chapter_id,review_risk,notes`.

- [ ] **Step 1: Write the failing inventory tests**

Add tests that require the exact header, unique module names, allowed origins (`Standard`, `Enterprise`, `OCA`, `Thai Localization`, `Linkweld Custom`), allowed statuses (`Included`, `Excluded - No Accounting Effect`, `Conditional`), nonblank evidence references for Included rows, and presence of these priority modules/families: Accounting, Sales, Purchase, Inventory, MRP, Rental, Assets, Analytic, Payment, Thai VAT/WHT, account partner settlement, payment register extensions, cheque management, and custom reporting.

```python
def test_module_inventory_has_required_coverage(self):
    required = {
        "account", "sale", "purchase", "stock", "mrp", "sale_renting",
        "account_asset", "analytic", "payment", "l10n_th", "l10n_th_reports",
        "account_partner_settlement", "cheque_management",
    }
    rows = self.read_csv("accounting_sensitive_module_inventory.csv")
    self.assertTrue(required.issubset({row["module_name"] for row in rows}))
    self.assertEqual(len(rows), len({row["module_name"] for row in rows}))
```

- [ ] **Step 2: Run the test and verify failure**

Run: `C:\Python313\python.exe -m unittest manual.linkweld_odoo18.tests.test_accounting_je_playbook -v`

Expected: FAIL because the inventory does not exist.

- [ ] **Step 3: Author the module inventory**

Classify all accounting-sensitive Standard/Enterprise modules confirmed by the audit, then scan local manifests for dependencies on `account`, `account_accountant`, `stock_account`, `purchase_stock`, `sale`, `purchase`, `mrp`, `payment`, `account_asset`, `analytic`, and Thai localization. Include pure UI/infrastructure addons only as explicit exclusions when needed to prove “every module” coverage. Record model/method review notes without entering Technical menus.

- [ ] **Step 4: Run inventory tests**

Expected: PASS; no duplicate module names, no missing required families, no Included row without an evidence reference or chapter ID.

- [ ] **Step 5: Commit inventory scope**

```bash
git add manual/linkweld_odoo18/register/accounting_sensitive_module_inventory.csv manual/linkweld_odoo18/tests/test_accounting_je_playbook.py
git commit -m "docs: map Linkweld accounting-sensitive modules"
```

### Task 2: Build the Core JE Matrix for Order-to-Cash, Procure-to-Pay, and Payments

**Files:**
- Create: `manual/linkweld_odoo18/register/accounting_module_je_matrix.csv`
- Modify: `manual/linkweld_odoo18/tests/test_accounting_je_playbook.py`

**Interfaces:**
- Consumes: module inventory and `ACC-001` through `ACC-030` evidence.
- Produces: CSV columns `scenario_id,module_family,module_name,business_document,trigger_state,debit_account_role,credit_account_role,formula,hypothetical_debit_thb,hypothetical_credit_thb,vat_impact,wht_impact,stock_svl_impact,asset_impact,analytic_impact,reconciliation_target,reversal_scenario,acc_reference,evidence_status,uat_id,owner,risk,source_reference`.

- [ ] **Step 1: Write failing JE arithmetic and schema tests**

Require unique `scenario_id`, exact columns, numeric Debit/Credit, balanced rows, valid evidence status, valid ACC references, and UAT IDs. Add explicit arithmetic checks for:

```python
self.assertEqual(100000 * 0.07, 7000)
self.assertEqual(100000 + 7000, 107000)
self.assertEqual(107000 - (100000 * 0.03), 104000)
```

- [ ] **Step 2: Run and verify failure**

Expected: FAIL because the JE matrix does not exist.

- [ ] **Step 3: Add atomic O2C/P2P/payment scenarios**

Include at minimum: customer invoice, customer credit note, sale return, customer advance, vendor bill, vendor refund, purchase return, vendor advance, output VAT, input VAT, WHT 1/2/3/5/15 policy examples, incoming/outgoing payment, partial payment, payment difference, bank/cash/cheque clearing, outstanding receipts/payments, reconciliation, FX realization, and bad-debt/write-off controls. Split compound postings into multiple rows sharing the same scenario prefix when one business event produces multiple journal lines.

- [ ] **Step 4: Run matrix tests**

Expected: PASS with zero unbalanced scenarios and all numeric examples reconciling to the stated formula.

- [ ] **Step 5: Commit core matrix**

```bash
git add manual/linkweld_odoo18/register/accounting_module_je_matrix.csv manual/linkweld_odoo18/tests/test_accounting_je_playbook.py
git commit -m "docs: add core Linkweld journal entry matrix"
```

### Task 3: Extend the JE Matrix for Stock, Manufacturing, Assets, Deferrals, and Analytics

**Files:**
- Modify: `manual/linkweld_odoo18/register/accounting_module_je_matrix.csv`
- Modify: `manual/linkweld_odoo18/tests/test_accounting_je_playbook.py`

**Interfaces:**
- Consumes: product-category evidence, Anglo-Saxon stock input/output findings, asset-model evidence, and analytic evidence.
- Produces: balanced scenario rows for valuation and period recognition.

- [ ] **Step 1: Add failing coverage tests**

Require scenarios for receipt, vendor bill clearing, delivery, customer-invoice COGS, return, scrap, inventory adjustment, landed cost, MRP consumption/production, by-product, unbuild, subcontracting, WIP policy, asset acquisition/depreciation/disposal/sale, deferred expense/revenue, budget non-posting control, and analytic distribution.

- [ ] **Step 2: Run and verify missing-family failures**

- [ ] **Step 3: Add stock and manufacturing examples**

Use account roles already evidenced for Linkweld: Stock Valuation, Stock Input, Stock Output, COGS, WIP, production variance, landed-cost clearing, and inventory gain/loss. Explicitly distinguish an SVL/stock move from a GL JE and label WIP examples as policy-dependent where Standard Odoo does not create a separate WIP JE automatically for the configured flow.

- [ ] **Step 4: Add asset, deferral, budget, and analytic examples**

Calculate NBV and disposal gain/loss with formulas. Mark Budget as a control/report scenario when no GL entry is generated. Link analytic examples to `ACC-028` through `ACC-030` and label their GL independence accurately.

- [ ] **Step 5: Run tests and commit**

```bash
git add manual/linkweld_odoo18/register/accounting_module_je_matrix.csv manual/linkweld_odoo18/tests/test_accounting_je_playbook.py
git commit -m "docs: cover valuation manufacturing and asset entries"
```

### Task 4: Add Thai Localization and Custom Addon Regression Coverage

**Files:**
- Modify: `manual/linkweld_odoo18/register/accounting_module_je_matrix.csv`
- Modify: `manual/linkweld_odoo18/register/accounting_sensitive_module_inventory.csv`
- Modify: `manual/linkweld_odoo18/tests/test_accounting_je_playbook.py`

**Interfaces:**
- Consumes: local addon source and prior tax/payment audit findings.
- Produces: Thai/OCA/custom scenario rows and regression mapping.

- [ ] **Step 1: Add failing localization/custom tests**

Require VAT 7%, VAT 0%, exempt, WHT purchase/payment, PND3, PND53, WHT certificate, tax closing, payment-register extension, automatic payment difference, default journal, multi-deduction, partner settlement, cheque, billing, sale invoice automation, MRP cost customization, partner default accounts, and custom report coverage.

- [ ] **Step 2: Review local source with targeted searches**

For each addon, record inherited model, overridden method, Standard flow changed, write/post/reconcile risk, and smallest regression scope. Do not modify addon code.

- [ ] **Step 3: Add matrix and inventory rows**

Label source-only conclusions `Custom Review Required`; never label them Confirmed Linkweld without existing posting evidence. Preserve the ACC-009 caveat that the selected WHT tax has no confirmed PND grid mapping.

- [ ] **Step 4: Run tests and commit**

```bash
git add manual/linkweld_odoo18/register/accounting_module_je_matrix.csv manual/linkweld_odoo18/register/accounting_sensitive_module_inventory.csv manual/linkweld_odoo18/tests/test_accounting_je_playbook.py
git commit -m "docs: map Thai and custom accounting regressions"
```

### Task 5: Author and Build the Companion Playbook

**Files:**
- Create: `manual/linkweld_odoo18/source/03_accounting_control_je_playbook_th.md`
- Create: `manual/linkweld_odoo18/scripts/build_accounting_je_playbook.py`
- Create: `manual/linkweld_odoo18/output/03_Linkweld_Odoo18_Accounting_Control_JE_Playbook_TH.docx`
- Modify: `manual/linkweld_odoo18/tests/test_accounting_je_playbook.py`

**Interfaces:**
- Consumes: module inventory, JE matrix, official Odoo links, local source references, and ACC chapter links.
- Produces: Markdown and DOCX with cover, static contents, module chapters, JE tables, controls, UAT, and exclusion appendix.

- [ ] **Step 1: Write failing content tests**

Require all seven planned parts, all module families from Included inventory rows, the exact labels `Standard Odoo 18`, `Pain Point`, `Solution`, `JE ตัวอย่าง`, `Reversal`, `Reconciliation`, and `UAT`, and all `ACC-001` through `ACC-030` cross-references where applicable.

- [ ] **Step 2: Author the Markdown source**

Use this fixed structure per module: purpose, source documents, Accounting checklist, policy owner, posting trigger, formula JE, THB numeric JE, VAT/WHT, stock/asset/analytic dependencies, reversal, reconciliation/close, access/audit, Standard vs Pain Point, and UAT. Add a module exclusion appendix and a custom-addon impact register.

- [ ] **Step 3: Implement the deterministic builder**

Reuse the `compact_reference_guide` Word design system and `editorial_cover` opening pattern from the existing manual builder. Use Tahoma as the named Thai-font override, explicit table geometry, repeating headers, real list styles, page numbers, and no credentials or live transaction values.

- [ ] **Step 4: Build and run structural tests**

Run:

```bash
C:\Python313\python.exe manual/linkweld_odoo18/scripts/build_accounting_je_playbook.py
C:\Python313\python.exe -m unittest manual.linkweld_odoo18.tests.test_accounting_je_playbook -v
```

Expected: all tests PASS; DOCX is a valid ZIP/OOXML package and contains every required module heading and JE table.

- [ ] **Step 5: Render and inspect**

Use the canonical Documents `render_docx.py` with `--emit_pdf`. Inspect every page PNG at 100% for Thai glyphs, table clipping, broken page breaks, image/text overlap, and inconsistent headers. If `soffice` remains unavailable, perform structural QA and disclose the render limitation without claiming visual QA passed.

- [ ] **Step 6: Commit the playbook**

```bash
git add manual/linkweld_odoo18/source/03_accounting_control_je_playbook_th.md manual/linkweld_odoo18/scripts/build_accounting_je_playbook.py manual/linkweld_odoo18/tests/test_accounting_je_playbook.py manual/linkweld_odoo18/output/03_Linkweld_Odoo18_Accounting_Control_JE_Playbook_TH.docx
git commit -m "docs: deliver Linkweld accounting control JE playbook"
```

### Task 6: Link the Companion Book and Complete Documentation Controls

**Files:**
- Modify: `manual/linkweld_odoo18/source/02_accounting_manual_th.md`
- Modify: `manual/linkweld_odoo18/README.md`
- Modify: `C:\365_project\TheCool18e\LINKWELD_DEV_HANDOFF.md`

**Interfaces:**
- Consumes: final playbook, inventory, matrix, test output, and render status.
- Produces: discoverable cross-links and final handoff.

- [ ] **Step 1: Add a short companion-book cross-reference**

Do not duplicate the JE content in the existing Accounting manual. Add the companion filename, intended use, evidence-label definitions, and matrix path.

- [ ] **Step 2: Update README and handoff**

Record scenario/module counts, custom-addon review scope, tests, privacy scan, render result, no Odoo writes, output paths, and remaining Clone-UAT limitations.

- [ ] **Step 3: Run privacy and path scans**

```bash
rg -n -i "tech@linkweldthailand\.com|PW:\s*test|password\s*[:=]" manual/linkweld_odoo18 C:\365_project\TheCool18e\LINKWELD_DEV_HANDOFF.md
```

Expected: zero credential findings; all Markdown/file links resolve.

- [ ] **Step 4: Commit documentation links**

```bash
git add manual/linkweld_odoo18/source/02_accounting_manual_th.md manual/linkweld_odoo18/README.md
git commit -m "docs: link accounting JE companion manual"
```

### Task 7: Update the Implementation Plan Workbook Status

**Files:**
- Create: `manual/linkweld_odoo18/scripts/update_implementation_plan_status.mjs`
- Read: `C:\Users\tumsu\Downloads\Linkweld_Odoo18_Implementation_Plan.xlsx`
- Export: `C:\Users\tumsu\Downloads\Linkweld_Odoo18_Implementation_Plan_Updated.xlsx`

**Interfaces:**
- Consumes: a fully passing documentation test suite and completed deliverables.
- Produces: workbook copy with `03_Config_Manual!H5:H13 = Complete`; all other planning statuses unchanged.

- [ ] **Step 1: Load workspace dependencies and import the workbook**

Use `codex_app__load_workspace_dependencies`; create a task-local `node_modules` junction to the returned dependency path. Import with:

```javascript
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";
const input = await FileBlob.load(inputPath);
const workbook = await SpreadsheetFile.importXlsx(input);
```

- [ ] **Step 2: Inspect and render before editing**

Inspect `Dashboard!A1:H14` and `03_Config_Manual!A1:H13`, then render both sheets. Confirm the current baseline is Complete 0, In Progress 0, Not Started 28, Overall Progress 0.0%, and that `H5:H13` is `Not Started`.

- [ ] **Step 3: Apply the minimal value-only update**

```javascript
const config = workbook.worksheets.getItem("03_Config_Manual");
config.getRange("H5:H13").values = Array.from({ length: 9 }, () => ["Complete"]);
```

Do not change formatting, formulas, validations, charts, row heights, column widths, or any other Status cell.

- [ ] **Step 4: Verify formulas and visual output**

Inspect `03_Config_Manual!A4:H13` and `Dashboard!A4:H14`. Expected dashboard after recalculation: Complete 9, In Progress 0, Not Started 19, Other Open 0, Total 28, Overall Progress 32.1%. Scan for `#REF!`, `#DIV/0!`, `#VALUE!`, `#NAME?`, and `#N/A`. Render all five sheets and visually confirm no clipping or style changes.

- [ ] **Step 5: Export the preserved copy**

```javascript
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save("C:/Users/tumsu/Downloads/Linkweld_Odoo18_Implementation_Plan_Updated.xlsx");
```

- [ ] **Step 6: Record workbook completion in the handoff**

Add exact updated range, before/after counts, output path, formula-error result, and visual-verification status. Do not commit the Downloads workbook into the repository.

### Task 8: Final End-to-End Verification and Delivery

**Files:**
- Verify all files created or modified in Tasks 1-7.

**Interfaces:**
- Consumes: complete playbook, registers, updated workbook, tests, and handoff.
- Produces: final user delivery and message to task `019f6878-50d2-7522-a5d9-826c69363f68`.

- [ ] **Step 1: Run the full validation suite**

Verify CSV widths, unique IDs, module coverage, balanced entries, VAT/WHT arithmetic, ACC links, DOCX structure, credential scan, workbook formulas, and output existence.

- [ ] **Step 2: Review git scope**

Confirm no unrelated changes are staged or committed. Report pre-existing unrelated worktree changes without altering them.

- [ ] **Step 3: Send the handoff**

Send final paths, counts, validation results, Excel status range and dashboard values, render limitation if any, and no-Odoo-write confirmation to task `019f6878-50d2-7522-a5d9-826c69363f68`.

- [ ] **Step 4: Deliver to the user**

Provide standalone links to the final DOCX and updated XLSX, plus a short statement of module/scenario coverage, tests, and any remaining Clone-UAT or render limitation.
