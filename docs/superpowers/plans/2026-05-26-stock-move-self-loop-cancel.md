# Stock Move Self-Loop Cancel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent internal transfer move merges from generating recursive stock links and repair the nine confirmed UAT self-links.

**Architecture:** Keep Odoo core unchanged and amend the installed custom merge override. The override filters only links internal to a merge recordset, preserving external chain edges; the UAT repair removes only already-corrupt self-relations after storing an audit copy.

**Tech Stack:** Odoo 18 ORM, Python, PostgreSQL, Odoo `TransactionCase`

---

### Task 1: Merge Link Regression

**Files:**
- Modify: `custom/goldmints_addon-main/mrp_mps_manufacturing_type/tests/test_stock_move_merge_fields.py`

- [ ] **Step 1: Write the failing test**

Create three moves and link the two merge candidates to each other plus an external upstream and downstream move. Assert that `_merge_moves_fields()` retains the external IDs in both relation commands and omits the two candidate IDs.

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
& '.\.venv\Scripts\python.exe' '.\server\odoo-bin' -c '.\server\odoo.conf' -d test_stock_move_self_loop -i mrp_mps_manufacturing_type --test-enable --test-tags /mrp_mps_manufacturing_type --stop-after-init
```

Expected: the test fails because the current override drops downstream links and leaves internal upstream links.

### Task 2: Cycle-Safe Merge Values

**Files:**
- Modify: `custom/goldmints_addon-main/mrp_mps_manufacturing_type/models/stock_move.py`

- [ ] **Step 1: Write minimal implementation**

Update `_merge_moves_fields()` so `move_dest_ids` and `move_orig_ids` contain `Command.link()` entries only for `self.mapped(field_name) - self`.

- [ ] **Step 2: Run focused test to verify it passes**

Run the same Odoo test command from Task 1.

Expected: test command exits with no failures.

### Task 3: UAT Relation Repair

**Files:**
- Database only: `GoldMints_Uat_Manu.stock_move_move_rel`

- [ ] **Step 1: Back up affected rows and delete self-links in one transaction**

Create `stock_move_move_rel_self_loop_backup_20260526` from self-link rows joined with move and picking references, then delete only rows satisfying `move_orig_id = move_dest_id`.

- [ ] **Step 2: Verify data repair**

Query `stock_move_move_rel` for self-links and query cycles reachable upstream from the affected active MO raw moves.

Expected: zero self-links remain; any non-self historical cycle is reported separately rather than silently modified.

### Task 4: Final Validation

**Files:**
- Review: `custom/goldmints_addon-main/mrp_mps_manufacturing_type/models/stock_move.py`
- Review: `custom/goldmints_addon-main/mrp_mps_manufacturing_type/tests/test_stock_move_merge_fields.py`

- [ ] **Step 1: Review the diff**

Run:

```powershell
git diff -- custom/goldmints_addon-main/mrp_mps_manufacturing_type/models/stock_move.py custom/goldmints_addon-main/mrp_mps_manufacturing_type/tests/test_stock_move_merge_fields.py
```

- [ ] **Step 2: Report runtime requirement**

The running Odoo workers must be restarted after the code patch before new merges use the prevention logic.
