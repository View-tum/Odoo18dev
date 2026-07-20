# TCG Delivery Lot Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Confirm the approved 905 UAT Delivery Orders that remain in Draft, run standard availability, align eligible UAT lot reservations with read-only Production evidence, and report every OUT-reference or allocation difference.

**Architecture:** Use a two-system, fail-closed workflow. A reusable Odoo-shell script exports Production evidence without writes, builds and validates a UAT plan, and applies only prevalidated lot reservations through Odoo 18 ORM inside one savepoint per picking. The UAT contextual Server Action performs only standard `action_confirm()` and `action_assign()` on selected draft pickings.

**Tech Stack:** Odoo 18 Enterprise ORM, Python 3, Odoo shell, JSON/CSV evidence, `unittest`, authenticated UAT browser session, SSH tunnel for database/server access.

## Global Constraints

- Production at `tcc.thecool.com` is read-only.
- UAT target is `tcg-uat.365odoo.com`.
- Company is exactly `บริษัท เดอะ คูล จำกัด`.
- Operation Type is exactly `บริษัท เดอะ คูล จำกัด: Delivery Orders`.
- The approved UAT scope is the current 905-record result set, restricted at execution time to records still in `draft`.
- Pair records by Source Document, Operation Type, and Company; OUT references are comparison outputs and must not be changed.
- Do not create lots, alter stock quantities, validate pickings, fabricate valuation layers, or create accounting entries.
- Skip and report missing, ambiguous, mismatched, or insufficient-stock rows.
- Use Odoo ORM for all UAT stock reservation changes; no SQL writes.
- Production and UAT credentials, private keys, and connection strings must not be written to source files or evidence files.

---

## File Structure

- Create `reports/uat_testpacks/tcg_delivery_lot_alignment.py`: pure matching functions plus Odoo-shell export, preflight, apply, and verify entry points.
- Create `reports/uat_testpacks/tests/test_tcg_delivery_lot_alignment.py`: deterministic unit tests for pairing, ambiguity, quantity checks, and fail-closed plan generation.
- Create at runtime `reports/uat_evidence/tcg_delivery_lot_alignment/<run_id>/production.json`: read-only Production snapshot.
- Create at runtime `reports/uat_evidence/tcg_delivery_lot_alignment/<run_id>/uat_before.json`: exact UAT scope and pre-change reservation snapshot.
- Create at runtime `reports/uat_evidence/tcg_delivery_lot_alignment/<run_id>/plan.json`: immutable preflight plan with SHA-256 digest.
- Create at runtime `reports/uat_evidence/tcg_delivery_lot_alignment/<run_id>/result.csv`: reader-facing comparison and exception report.
- Create at runtime `reports/uat_evidence/tcg_delivery_lot_alignment/<run_id>/result.json`: machine-verifiable post-execution evidence.

### Task 1: Deterministic matching and validation core

**Files:**
- Create: `reports/uat_testpacks/tcg_delivery_lot_alignment.py`
- Create: `reports/uat_testpacks/tests/test_tcg_delivery_lot_alignment.py`

**Interfaces:**
- Produces: `picking_key(row: dict) -> tuple[str, str, str]`
- Produces: `pair_pickings(production_rows: list[dict], uat_rows: list[dict]) -> dict`
- Produces: `build_lot_plan(pair: dict) -> dict`
- Produces: `sha256_json(value: object) -> str`

- [ ] **Step 1: Write failing unit tests**

```python
import importlib.util
import pathlib
import unittest


MODULE_PATH = pathlib.Path(__file__).parents[1] / "tcg_delivery_lot_alignment.py"
SPEC = importlib.util.spec_from_file_location("tcg_delivery_lot_alignment", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class TestDeliveryLotAlignment(unittest.TestCase):
    def setUp(self):
        self.base = {
            "company": "บริษัท เดอะ คูล จำกัด",
            "operation_type": "บริษัท เดอะ คูล จำกัด: Delivery Orders",
            "source_document": "SO2601-00001",
            "out_reference": "TCC/OUT/2601-00001",
            "lines": [
                {
                    "product_key": "SKU-01",
                    "uom": "Units",
                    "demand_qty": 2.0,
                    "lots": [{"name": "LOT-A", "qty": 2.0}],
                }
            ],
        }

    def test_pairs_by_source_operation_and_company(self):
        production = dict(self.base)
        uat = dict(self.base, out_reference="TCC/OUT/2601-00999")
        result = MODULE.pair_pickings([production], [uat])
        self.assertEqual(len(result["matched"]), 1)
        self.assertEqual(result["matched"][0]["production"]["out_reference"], "TCC/OUT/2601-00001")
        self.assertEqual(result["matched"][0]["uat"]["out_reference"], "TCC/OUT/2601-00999")

    def test_duplicate_source_is_ambiguous(self):
        production = [dict(self.base), dict(self.base, out_reference="TCC/OUT/2601-00002")]
        result = MODULE.pair_pickings(production, [dict(self.base)])
        self.assertEqual(result["matched"], [])
        self.assertEqual(result["exceptions"][0]["reason"], "AMBIGUOUS_PRODUCTION_MATCH")

    def test_missing_lot_is_skipped(self):
        pair = {
            "production": dict(self.base),
            "uat": dict(self.base, available_lots=[]),
        }
        result = MODULE.build_lot_plan(pair)
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "LOT_NOT_FOUND_IN_UAT")

    def test_insufficient_lot_quantity_is_skipped(self):
        pair = {
            "production": dict(self.base),
            "uat": dict(self.base, available_lots=[{"product_key": "SKU-01", "name": "LOT-A", "available_qty": 1.0}]),
        }
        result = MODULE.build_lot_plan(pair)
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "INSUFFICIENT_UAT_LOT_QUANTITY")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
python -m unittest reports.uat_testpacks.tests.test_tcg_delivery_lot_alignment -v
```

Expected: failures because the module and functions do not exist.

- [ ] **Step 3: Implement the pure matching core**

```python
import hashlib
import json
from collections import defaultdict


COMPANY = "บริษัท เดอะ คูล จำกัด"
OPERATION_TYPE = "บริษัท เดอะ คูล จำกัด: Delivery Orders"


def sha256_json(value):
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def picking_key(row):
    return (
        (row.get("source_document") or "").strip(),
        (row.get("operation_type") or "").strip(),
        (row.get("company") or "").strip(),
    )


def pair_pickings(production_rows, uat_rows):
    production_by_key = defaultdict(list)
    uat_by_key = defaultdict(list)
    for row in production_rows:
        production_by_key[picking_key(row)].append(row)
    for row in uat_rows:
        uat_by_key[picking_key(row)].append(row)
    matched = []
    exceptions = []
    for key in sorted(set(production_by_key) | set(uat_by_key)):
        production = production_by_key.get(key, [])
        uat = uat_by_key.get(key, [])
        if len(production) > 1:
            exceptions.append({"key": key, "reason": "AMBIGUOUS_PRODUCTION_MATCH", "production": production, "uat": uat})
        elif len(uat) > 1:
            exceptions.append({"key": key, "reason": "AMBIGUOUS_UAT_MATCH", "production": production, "uat": uat})
        elif not production:
            exceptions.append({"key": key, "reason": "MISSING_PRODUCTION_MATCH", "production": [], "uat": uat})
        elif not uat:
            exceptions.append({"key": key, "reason": "MISSING_UAT_MATCH", "production": production, "uat": []})
        else:
            matched.append({"key": key, "production": production[0], "uat": uat[0]})
    return {"matched": matched, "exceptions": exceptions}


def build_lot_plan(pair):
    production = pair["production"]
    uat = pair["uat"]
    production_lines = {(line["product_key"], line["uom"], line["demand_qty"]): line for line in production["lines"]}
    uat_lines = {(line["product_key"], line["uom"], line["demand_qty"]): line for line in uat["lines"]}
    if set(production_lines) != set(uat_lines):
        return {"status": "skipped", "reason": "PRODUCT_OR_QUANTITY_MISMATCH", "pair": pair}
    available = {
        (row["product_key"], row["name"]): row["available_qty"]
        for row in uat.get("available_lots", [])
    }
    allocations = []
    for line_key, production_line in production_lines.items():
        product_key = line_key[0]
        for lot in production_line.get("lots", []):
            available_key = (product_key, lot["name"])
            if available_key not in available:
                return {"status": "skipped", "reason": "LOT_NOT_FOUND_IN_UAT", "pair": pair}
            if available[available_key] < lot["qty"]:
                return {"status": "skipped", "reason": "INSUFFICIENT_UAT_LOT_QUANTITY", "pair": pair}
            allocations.append({"product_key": product_key, "lot": lot["name"], "qty": lot["qty"]})
    return {"status": "ready", "reason": "", "pair": pair, "allocations": allocations}
```

- [ ] **Step 4: Run the unit tests**

Run:

```powershell
python -m unittest reports.uat_testpacks.tests.test_tcg_delivery_lot_alignment -v
```

Expected: four tests pass.

- [ ] **Step 5: Commit the matching core**

```powershell
git add reports/uat_testpacks/tcg_delivery_lot_alignment.py reports/uat_testpacks/tests/test_tcg_delivery_lot_alignment.py
git commit -m "feat: add delivery lot alignment planning core"
```

### Task 2: Read-only Production and UAT snapshot modes

**Files:**
- Modify: `reports/uat_testpacks/tcg_delivery_lot_alignment.py`
- Modify: `reports/uat_testpacks/tests/test_tcg_delivery_lot_alignment.py`

**Interfaces:**
- Consumes: Odoo shell global `env`
- Produces: `export_pickings(env, ids=None, draft_only=False) -> list[dict]`
- Produces: `write_json(path: str, value: object) -> None`

- [ ] **Step 1: Add tests for exact scope and stable export**

Add fake-record tests proving that `draft_only=True` excludes non-draft rows, the export contains no credentials, and the serialized rows contain company, operation type, source document, OUT reference, product, UoM, demand, reserved lot, and reserved quantity.

- [ ] **Step 2: Run the focused tests**

Run:

```powershell
python -m unittest reports.uat_testpacks.tests.test_tcg_delivery_lot_alignment -v
```

Expected: new export tests fail before implementation.

- [ ] **Step 3: Implement snapshot extraction**

Use these exact Odoo fields:

```python
def export_pickings(env, ids=None, draft_only=False):
    domain = [
        ("company_id.name", "=", COMPANY),
        ("picking_type_id.name", "=", "Delivery Orders"),
    ]
    if ids is not None:
        domain.append(("id", "in", ids))
    if draft_only:
        domain.append(("state", "=", "draft"))
    pickings = env["stock.picking"].search(domain, order="id")
    rows = []
    for picking in pickings:
        lines = []
        for move in picking.move_ids.filtered(lambda item: item.state != "cancel"):
            lots = []
            for move_line in move.move_line_ids.filtered(lambda item: item.lot_id and item.quantity):
                lots.append({"name": move_line.lot_id.name, "qty": move_line.quantity})
            lines.append({
                "move_id": move.id,
                "product_key": move.product_id.default_code or f"PRODUCT_ID:{move.product_id.id}",
                "product_name": move.product_id.display_name,
                "uom": move.product_uom.name,
                "demand_qty": move.product_uom_qty,
                "lots": lots,
            })
        rows.append({
            "id": picking.id,
            "state": picking.state,
            "company": picking.company_id.name,
            "operation_type": picking.picking_type_id.display_name,
            "source_document": picking.origin or "",
            "out_reference": picking.name,
            "source_location_id": picking.location_id.id,
            "lines": lines,
        })
    return rows
```

Use `stock.picking.type.display_name` in the output and verify it equals the approved fully qualified operation type. Use the stored name only in the search domain because the display name is computed.

- [ ] **Step 4: Add entry points**

Support exact modes:

```text
TCG_ALIGNMENT_MODE=export-production
TCG_ALIGNMENT_MODE=export-uat-before
TCG_ALIGNMENT_MODE=build-plan
TCG_ALIGNMENT_MODE=apply-uat
TCG_ALIGNMENT_MODE=verify-uat
```

Require `TCG_ALIGNMENT_RUN_DIR` for every mode and require `TCG_UAT_IDS_FILE` for UAT modes. Abort if the UAT ID file does not contain exactly 905 unique integer IDs.

- [ ] **Step 5: Run syntax and unit validation**

Run:

```powershell
python -m py_compile reports/uat_testpacks/tcg_delivery_lot_alignment.py
python -m unittest reports.uat_testpacks.tests.test_tcg_delivery_lot_alignment -v
```

Expected: compilation succeeds and all tests pass.

- [ ] **Step 6: Commit snapshot support**

```powershell
git add reports/uat_testpacks/tcg_delivery_lot_alignment.py reports/uat_testpacks/tests/test_tcg_delivery_lot_alignment.py
git commit -m "feat: add production and UAT delivery snapshots"
```

### Task 3: Access preflight and immutable dry-run plan

**Files:**
- Modify: `reports/uat_testpacks/tcg_delivery_lot_alignment.py`
- Create at runtime: `reports/uat_evidence/tcg_delivery_lot_alignment/<run_id>/*`

**Interfaces:**
- Consumes: Production snapshot and exact 905 UAT IDs
- Produces: `plan.json` and its SHA-256 digest

- [ ] **Step 1: Verify the SSH host key before trusting it**

Run:

```powershell
ssh-keyscan -t ed25519,rsa 159.223.84.50 | ssh-keygen -lf -
```

Expected: one or more fingerprints are printed. Compare them with the server-owner-approved fingerprint before adding the host to `known_hosts`. Do not use `StrictHostKeyChecking=no`.

- [ ] **Step 2: Establish read-only Production access**

Open the Production PostgreSQL tunnel with local port `15432` mapped to `10.104.0.3:5432`. Open the UAT tunnel with local port `15433` mapped to the approved UAT PostgreSQL endpoint on port `5433`. Keep credentials in the process environment only.

- [ ] **Step 3: Capture the exact UAT list scope**

Use the authenticated UAT list view, select all 905 records, and export only their IDs through a non-mutating read path. Save the sorted unique IDs to `uat_ids.json`. Abort unless:

```python
assert len(ids) == 905
assert len(ids) == len(set(ids))
assert all(isinstance(item, int) and item > 0 for item in ids)
```

- [ ] **Step 4: Export Production and UAT snapshots**

Run the script in the corresponding Odoo shell environments. Production mode must execute with a PostgreSQL role verified as read-only or inside an explicit read-only transaction.

- [ ] **Step 5: Build the dry-run plan**

The plan builder must:

- verify exactly 905 UAT IDs;
- retain only UAT rows still in Draft;
- pair by source document, operation type, and company;
- check product, UoM, demand, lot existence, and available UAT lot quantity;
- produce `ready` and `skipped` rows;
- include both OUT references without changing either;
- record the preflight plan SHA-256 digest.

- [ ] **Step 6: Review the dry-run gate**

Do not continue to Task 4 unless the report states:

```text
uat_scope_count = 905
production_write_count = 0
uat_write_count = 0
ambiguous_rows are all skipped
missing_lot_rows are all skipped
insufficient_quantity_rows are all skipped
```

### Task 4: Create and execute the UAT contextual action

**Files:**
- No repository source change
- Create in UAT database: one `ir.actions.server` record

**Interfaces:**
- Consumes: selected UAT recordset from the exact 905-record list
- Produces: standard confirmation and availability results for rows still in Draft

- [ ] **Step 1: Create the UAT Server Action**

Create:

```text
Name: Mark as To Do
Model: stock.picking
Action To Do: Execute Python Code
Binding View Types: list
```

Use this code:

```python
draft_records = records.filtered(lambda picking: picking.state == "draft")
if draft_records:
    draft_records.action_confirm()
    draft_records.action_assign()
```

- [ ] **Step 2: Verify menu visibility without executing**

Return to the Delivery Orders list, select one disposable UAT Draft record, and confirm `Actions > Mark as To Do` is visible. Deselect it without invoking the action.

- [ ] **Step 3: Reconfirm the execution gate**

Immediately before execution, verify:

```text
selected_count = 905
plan_digest = reviewed preflight digest
production access = read-only
no UAT record has been validated
```

- [ ] **Step 4: Execute once**

Select all 905 records from the approved result set and invoke `Actions > Mark as To Do` once. Do not retry automatically if the request errors or times out; inspect backend state first.

- [ ] **Step 5: Capture post-action state**

Export UAT state and record how many of the original 905 IDs are now `confirmed`, `waiting`, `partially_available`, or `assigned`, and list any still in `draft`, `done`, or `cancel`.

### Task 5: Fail-closed lot alignment through Odoo ORM

**Files:**
- Modify: `reports/uat_testpacks/tcg_delivery_lot_alignment.py`
- Modify: `reports/uat_testpacks/tests/test_tcg_delivery_lot_alignment.py`

**Interfaces:**
- Consumes: reviewed `plan.json`, exact UAT IDs, expected plan digest
- Produces: per-picking atomic reservation result

- [ ] **Step 1: Add tests for atomic reservation behavior**

Test that a failed lot reservation raises inside a picking savepoint and preserves the original standard reservation. Test that a successful reservation calls `_do_unreserve()` and `_update_reserved_quantity()` only for the exact planned move, lot, source location, and quantity.

- [ ] **Step 2: Implement digest and scope guards**

Before any write:

```python
if sha256_json(plan["payload"]) != expected_digest:
    raise RuntimeError("PLAN_DIGEST_MISMATCH")
if sorted(plan["uat_ids"]) != sorted(approved_uat_ids):
    raise RuntimeError("UAT_SCOPE_MISMATCH")
if len(approved_uat_ids) != 905:
    raise RuntimeError("UAT_SCOPE_COUNT_MISMATCH")
```

- [ ] **Step 3: Implement per-picking savepoints**

For each `ready` plan row:

```python
with env.cr.savepoint():
    picking = env["stock.picking"].browse(row["uat_id"]).exists()
    if not picking or picking.state in ("draft", "done", "cancel"):
        raise RuntimeError("UAT_PICKING_STATE_NOT_ELIGIBLE")
    moves = picking.move_ids.filtered(lambda move: move.state not in ("done", "cancel"))
    moves._do_unreserve()
    for allocation in row["allocations"]:
        move = moves.filtered(lambda item: (item.product_id.default_code or f"PRODUCT_ID:{item.product_id.id}") == allocation["product_key"])
        if len(move) != 1:
            raise RuntimeError("AMBIGUOUS_UAT_MOVE")
        lot = env["stock.lot"].search([
            ("name", "=", allocation["lot"]),
            ("product_id", "=", move.product_id.id),
            ("company_id", "in", [False, picking.company_id.id]),
        ])
        if len(lot) != 1:
            raise RuntimeError("LOT_NOT_UNIQUE_IN_UAT")
        taken = move._update_reserved_quantity(
            allocation["qty"],
            move.location_id,
            lot_id=lot,
            strict=False,
        )
        if float_compare(
            taken,
            allocation["qty"],
            precision_rounding=move.product_id.uom_id.rounding,
        ) != 0:
            raise RuntimeError("INSUFFICIENT_UAT_LOT_QUANTITY")
```

Import `float_compare` from `odoo.tools.float_utils`. Using `strict=False` preserves Odoo's standard child-location search while the explicit `lot_id` still restricts the reservation to the Production lot. Catch the exception outside the savepoint, record the reason, and continue to the next picking. The rollback must restore the standard reservation for the failed picking.

- [ ] **Step 4: Run focused tests and syntax checks**

Run:

```powershell
python -m py_compile reports/uat_testpacks/tcg_delivery_lot_alignment.py
python -m unittest reports.uat_testpacks.tests.test_tcg_delivery_lot_alignment -v
```

Expected: compilation succeeds and all tests pass.

- [ ] **Step 5: Apply the reviewed plan once**

Run `apply-uat` only with the exact reviewed plan digest. Do not rerun a successful row. Persist each result with `success`, `skipped`, or `rolled_back` status.

- [ ] **Step 6: Commit lot alignment support**

```powershell
git add reports/uat_testpacks/tcg_delivery_lot_alignment.py reports/uat_testpacks/tests/test_tcg_delivery_lot_alignment.py
git commit -m "feat: align UAT delivery lots with production"
```

### Task 6: Post-execution integrity verification and reporting

**Files:**
- Modify: `reports/uat_testpacks/tcg_delivery_lot_alignment.py`
- Create at runtime: `reports/uat_evidence/tcg_delivery_lot_alignment/<run_id>/result.csv`
- Create at runtime: `reports/uat_evidence/tcg_delivery_lot_alignment/<run_id>/result.json`

**Interfaces:**
- Consumes: Production snapshot, UAT before snapshot, applied results, UAT after snapshot
- Produces: final comparison and integrity evidence

- [ ] **Step 1: Export UAT after-state**

Read the same exact 905 UAT IDs and include picking state, move state, reserved quantities, lots, and picked flags.

- [ ] **Step 2: Verify business integrity**

Assert:

```text
No original 905 picking is done because of this workflow.
No original 905 picking is cancel because of this workflow.
No stock move is done because of this workflow.
No stock valuation layer was created for the original 905 pickings.
No account move was created from this workflow.
Every successful aligned row has the same product/lot/quantity allocation as Production.
Every skipped or rolled-back row has a non-empty exception reason.
Production remains unchanged.
```

- [ ] **Step 3: Write the final reports**

The CSV columns must be:

```text
uat_out,production_out,source_document,match_status,product_key,demand_qty,production_lot,uat_lot_before,uat_lot_after,confirmation_result,availability_result,alignment_result,exception_reason
```

- [ ] **Step 4: Run final verification**

Run:

```powershell
python -m py_compile reports/uat_testpacks/tcg_delivery_lot_alignment.py
python -m unittest reports.uat_testpacks.tests.test_tcg_delivery_lot_alignment -v
git diff --check
```

Expected: all commands succeed.

- [ ] **Step 5: Commit report support**

```powershell
git add reports/uat_testpacks/tcg_delivery_lot_alignment.py reports/uat_testpacks/tests/test_tcg_delivery_lot_alignment.py
git commit -m "test: verify delivery lot alignment integrity"
```

## Execution Checkpoints

1. Stop if the SSH host fingerprint cannot be independently verified.
2. Stop if the exact UAT scope is not 905 unique IDs.
3. Stop if Production cannot be proven read-only.
4. Stop before Task 4 if the dry-run plan or exception counts are not reviewed.
5. Do not automatically retry the mass Server Action after a timeout.
6. Stop lot alignment if the plan digest or UAT scope changes.
7. Never process a picking that became Draft, Done, or Cancel after the Server Action.
