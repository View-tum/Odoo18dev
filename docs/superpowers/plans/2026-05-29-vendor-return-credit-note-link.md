# Vendor Return Credit Note Link Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let one Vendor Credit Note select and link multiple completed Vendor Return pickings while Warehouse can see each return's credit-note status.

**Architecture:** Extend the existing `account_credit_note_consolidated` module because it already owns Credit Note consolidation from bills and returns. Keep Odoo's standard `account.move.reversal` wizard as the entry point and add return selection, line generation helpers, and picking/account move traceability fields.

**Tech Stack:** Odoo 18 Enterprise ORM, XML views with modern modifiers, `TransactionCase` tests, existing `stock`, `purchase`, `account`, and `purchase_stock` behavior.

---

### Task 1: Add Failing Regression Tests

**Files:**
- Create: `custom/goldmints_addon-main/account_credit_note_consolidated/tests/__init__.py`
- Create: `custom/goldmints_addon-main/account_credit_note_consolidated/tests/test_vendor_return_credit_note.py`

- [x] **Step 1: Write tests for multi-return credit note flow**

Create one test case that:

- creates a stockable product, vendor, PO, receipt, and posted vendor bill;
- creates two completed vendor return pickings from the receipt;
- opens `account.move.reversal` from the bill;
- selects both return pickings;
- creates the draft Vendor Credit Note;
- asserts the Credit Note links both returns and contains return-linked invoice lines;
- asserts return picking status is `draft`, then `posted` after posting the Credit Note.

- [x] **Step 2: Verify RED**

Run:

```powershell
python server\odoo-bin -c server\odoo.conf -d GoldMints_Uat_Manu --test-enable --test-tags /account_credit_note_consolidated --stop-after-init --no-http
```

Expected: fail because `return_picking_ids`, `return_stock_move_id`, or `vendor_credit_note_state` fields do not exist yet.

### Task 2: Add Traceability Fields

**Files:**
- Modify: `custom/goldmints_addon-main/account_credit_note_consolidated/models/__init__.py`
- Modify: `custom/goldmints_addon-main/account_credit_note_consolidated/models/account_move.py`
- Create: `custom/goldmints_addon-main/account_credit_note_consolidated/models/stock_picking.py`

- [x] **Step 1: Add `account.move.return_picking_ids`**

Add a Many2many from Vendor Credit Notes to return pickings and helper action to open linked returns.

- [x] **Step 2: Add `account.move.line` return fields**

Add `return_picking_id` and `return_stock_move_id` for invoice-line traceability.

- [x] **Step 3: Add `stock.picking` computed fields**

Add `vendor_credit_note_ids`, `vendor_credit_note_count`, `vendor_credit_note_state`, and an action to open linked Credit Notes.

### Task 3: Extend Standard Credit Note Wizard

**Files:**
- Modify: `custom/goldmints_addon-main/account_credit_note_consolidated/wizard/__init__.py`
- Create: `custom/goldmints_addon-main/account_credit_note_consolidated/wizard/account_move_reversal.py`

- [x] **Step 1: Add return selection fields**

Extend `account.move.reversal` with `include_vendor_returns`, `return_picking_ids`, and preview `return_line_ids`.

- [x] **Step 2: Add transient preview line model**

Create `account.move.reversal.return.line` with selected return move, product, quantity, price, account, taxes, and source purchase/bill line.

- [x] **Step 3: Build helper methods**

Implement helpers to:

- find allowed completed vendor returns;
- build return preview lines;
- resolve price/tax/account/purchase line from matching posted bill line first, then PO line, then product fallback;
- prepare Credit Note invoice line values.

- [x] **Step 4: Override `reverse_moves`**

After standard reversal creates the draft Credit Note, replace generated invoice product lines with selected return lines, link `return_picking_ids`, and post chatter messages. If no returns are selected, keep standard behavior unchanged.

### Task 4: Add UI

**Files:**
- Modify: `custom/goldmints_addon-main/account_credit_note_consolidated/__manifest__.py`
- Create: `custom/goldmints_addon-main/account_credit_note_consolidated/wizard/account_move_reversal_views.xml`
- Modify: `custom/goldmints_addon-main/account_credit_note_consolidated/views/account_move_views.xml`
- Create: `custom/goldmints_addon-main/account_credit_note_consolidated/views/stock_picking_views.xml`
- Modify: `custom/goldmints_addon-main/account_credit_note_consolidated/security/ir.model.access.csv`

- [x] **Step 1: Add wizard section to `account.view_account_move_reversal`**

Show `Vendor Returns` only for vendor bill reversals.

- [x] **Step 2: Add Return smart button/status**

Add return status badge and Credit Notes smart button on `stock.view_picking_form`.

- [x] **Step 3: Add Credit Note linked returns UI**

Show linked returns on draft and posted vendor Credit Notes.

### Task 5: Verify

**Files:**
- All changed files above.

- [x] **Step 1: Compile Python**

Run:

```powershell
python -m py_compile custom\goldmints_addon-main\account_credit_note_consolidated\models\account_move.py custom\goldmints_addon-main\account_credit_note_consolidated\models\stock_picking.py custom\goldmints_addon-main\account_credit_note_consolidated\wizard\account_move_reversal.py custom\goldmints_addon-main\account_credit_note_consolidated\tests\test_vendor_return_credit_note.py
```

Expected: exit 0.

- [x] **Step 2: Run module tests**

Run:

```powershell
python server\odoo-bin -c server\odoo.conf -d GoldMints_Uat_Manu -u account_credit_note_consolidated --test-enable --test-tags /account_credit_note_consolidated --stop-after-init --no-http
```

Expected: `0 failed, 0 error(s)`.

- [x] **Step 3: UI smoke check**

Open the browser at `http://localhost:8811`, check:

- `Accounting > Vendors > Bills` shows the standard Credit Note wizard with Vendor Returns.
- `Inventory > Operations > Transfers` shows Vendor Credit Note status on return pickings.
