# Odoo 18 Agent Workflow Prompt Library

This prompt library is designed for:
- GPT-5.5 `xhigh` as planner / architect
- GPT-5.3-Codex `xhigh` as implementer
- optional GPT-5.5 or GPT-5.3-Codex as QA / writer

It is optimized for:
- Odoo 18 Enterprise
- custom development under `custom/view_dev/<module_name>/`
- multi-chat workflow
- single-chat fallback
- easy maintenance and copy/paste usage

## Recommended Default Workflow

### Chat A — Planner / Architect
Use:
- `01_PLANNER_ARCHITECT_GPT55.md`

Input:
- your business requirement
- traceback if debugging
- relevant context, constraints, screenshots, user flow

Output:
- analysis
- option A / B
- recommendation
- `HANDOFF_SPEC`

### Chat B — Implementer
Use:
- `02_IMPLEMENTER_GPT53_CODEX.md`

Input:
- approved `HANDOFF_SPEC` from Chat A

Output:
- folder tree
- full files
- install / upgrade commands
- `IMPLEMENTATION_RESULT`

### Chat C — QA / Reviewer
Use:
- `03_QA_REVIEWER.md`

Input:
- approved `HANDOFF_SPEC`
- generated code
- `IMPLEMENTATION_RESULT`

Output:
- test cases
- regression risks
- validation checklist
- `QA_RESULT`

### Chat D — Writer
Use:
- `04_TECHNICAL_WRITER.md`

Input:
- `HANDOFF_SPEC`
- `IMPLEMENTATION_RESULT`
- `QA_RESULT`

Output:
- installation guide
- configuration guide
- user guide
- developer maintenance notes

## Fastest Practical Workflow

If you want fewer chats:

### 2-chat workflow
- Chat A: Planner
- Chat B: Implementer + QA + Writer

### 1-chat workflow
Use:
- `00_MASTER_ROUTER.md`

This is less strict but still structured.

## Debug Workflow

When the task is:
- traceback
- install error
- upgrade error
- runtime behavior bug
- cron/background issue

Use:
- `99_DEBUG_BRANCH.md`

Do not start from the planner prompt for pure debugging.

## Copy/Paste Sequence

### Step 1 — Planner kickoff
Paste the planner prompt, then add:

```text
TASK
<your requirement here>
END_TASK
```

### Step 2 — Approve design
If the design is acceptable, reply:

```text
APPROVED_HANDOFF_SPEC
Proceed with implementation using this exact spec.
```

### Step 3 — Implementer
Paste the implementer prompt, then paste:

```text
HANDOFF_SPEC
...
END_HANDOFF_SPEC
```

### Step 4 — QA
Paste the QA prompt, then include:

```text
HANDOFF_SPEC
...
END_HANDOFF_SPEC

IMPLEMENTATION_RESULT
...
END_IMPLEMENTATION_RESULT
```

### Step 5 — Writer
Paste the writer prompt, then include:

```text
HANDOFF_SPEC
...
END_HANDOFF_SPEC

IMPLEMENTATION_RESULT
...
END_IMPLEMENTATION_RESULT

QA_RESULT
...
END_QA_RESULT
```

## Editing Strategy

If you want to tune behavior later:
- change business governance in `00_MASTER_ROUTER.md`
- change analysis depth in `01_PLANNER_ARCHITECT_GPT55.md`
- change coding standard in `02_IMPLEMENTER_GPT53_CODEX.md`
- change testing strictness in `03_QA_REVIEWER.md`
- change documentation tone in `04_TECHNICAL_WRITER.md`
- change debugging discipline in `99_DEBUG_BRANCH.md`

## Design Principles Used

- standard first, custom later
- core-safe Odoo customization only
- explicit handoff contracts between chats
- minimal duplication between prompts
- easy review and future editing

