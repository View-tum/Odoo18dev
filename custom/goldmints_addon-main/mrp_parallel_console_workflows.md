# Workflow Diagram: Odoo 18 MRP Parallel Console & Scrap Flow

This document visualizes the entire lifecycle of a Shopfloor Workorder, from starting the job, doing partial completions, recording scraps, and finally closing the Manufacturing Order (MO).

You can copy and paste the Mermaid code below into [Mermaid Live Editor](https://mermaid.live/) to generate a beautiful diagram, or view it natively in GitHub/VSCode.

## 1. Overall Shopfloor Workorder Flow (Start to Finish)

```mermaid
stateDiagram-v2
    %% Entities
    actor User as Shopfloor Operator
    participant UI as Console UI (JS)
    participant Ctrl as Controller (Python)
    participant DB as Odoo Database

    %% Flow
    User ->> UI: 1. Click "Start" on Workorder
    UI ->> Ctrl: check_components()
    Ctrl -->> UI: OK (Components Available)
    UI ->> Ctrl: start_workorder()
    Ctrl ->> DB: Start Timer & Change state to 'progress'

    Note right of User: Operator is working...

    User ->> UI: 2. Click "Quick Done" (Partial / Full completion)
    UI ->> Ctrl: quick_done(qty)
    Ctrl ->> DB: Log qty to 'console_qty'
    Ctrl ->> DB: Stop Timer (if finished)
    Ctrl ->> DB: Update state to 'done' (if fully done)
    Ctrl -->> UI: Success

    User ->> UI: 3. Click "Close Production" (Top Menu)
    UI ->> Ctrl: apply_console(workorder_ids)
    Ctrl ->> DB: Sync Component Demands
    Ctrl ->> DB: Validate Lots (if tracked)
    Ctrl ->> DB: Auto-Validate Scraps (draft -> done)
    Ctrl ->> DB: Create Backorder (if qty_produced < product_qty)
    Ctrl ->> DB: Close MO (button_mark_done)
    Ctrl -->> UI: MO Closed Successfully
```

<br>

## 2. The New Auto-Replenish Scrap Workflow

This diagram explains exactly what happens under the hood when a user records a damaged component (Scrap). It highlights the custom logic we just implemented.

```mermaid
flowchart TD
    A[User clicks 'Scrap' & fills Qty] --> B(UI: Validate Qty <= Max Allowed)
    B -- Exceeds --> C[UI Error: Cannot exceed planned qty]
    B -- Valid --> D{Is Product a Component <br> or Finished Good?}

    D -- Finished Good --> E[Create stock.scrap as Draft]
    E --> F[End. Awaits MO Closure for Landed Cost.]

    D -- Component --> G[Create stock.scrap as Draft]
    G --> H{Check Stock at <br> Pre-Production Location}

    H -- Stock >= Scrap Qty --> I[Scenario A: Auto-Consume]
    I --> J[Find raw_move in MO]
    J --> K[Increase 'product_uom_qty' by Scrap Qty]
    K --> L[Post Message: '✅ Scrap Replenish: Found sufficient stock']

    H -- Stock < Scrap Qty --> M[Scenario B: Auto-Transfer]
    M --> N[Find Main Store Location]
    N --> O[Create Internal Transfer picking from Store to Pre-Production]
    O --> P[Increase 'product_uom_qty' in MO]
    P --> Q[Post Message: '📦 Scrap Replenish: Created Internal Transfer']

    L --> Z([Shopfloor UI refreshes silently])
    Q --> Z
```

<br>

## 3. End of Shift / MO Closure Workflow (Backorder & Scrap Handling)

Since your factory produces "day by day" but opens MOs "weekly", this is how Odoo handles the discrepancies when closing the MO.

```mermaid
sequenceDiagram
    actor Supervisor
    participant System as Odoo Backend
    participant Inv as Inventory Layer
    participant Cost as Costing/Accounting

    Supervisor->>System: Clicks "Apply Console" (Close MO)

    activate System
    System->>System: 1. Sum up all 'console_qty' from Workorders
    System->>System: 2. Set 'qty_producing' = Total Done

    System->>Inv: 3. Attempt to Validate Draft Scraps
    alt Stock is available for Scrap
        Inv-->>System: Validated (Stock Deducted)
    else Stock is insufficient
        Inv-->>System: Skipped (Left as Draft)
    end

    System->>Inv: 4. Consume raw materials based on BOM ratio

    alt Total Done < Planned Qty (Partial Week)
        System->>System: 5. Generate Backorder automatically
        System->>Supervisor: Prompt: "MO Closed. Backorder MO-001-002 created for remaining."
    else Total Done >= Planned Qty
        System->>Supervisor: Prompt: "MO Closed successfully."
    end
    deactivate System

    Note over System,Cost: [Landed Cost Step (Manual/Accountant)]
    Cost->>Cost: Create Landed Cost for MO
    Cost->>System: Fetch Draft/Done Scraps linked to MO
    System-->>Cost: Returns Scrap Value (e.g. $50)
    Cost->>Inv: Apportion $50 to the Finished Goods' valuation
```
