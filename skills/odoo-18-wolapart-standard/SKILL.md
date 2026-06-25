---
name: odoo-18-wolapart-standard
description: Standards and Playbooks for Odoo 18 Enterprise customizations following the Wolapart & Flow methodology.
---

# Wolapart & Flow: Odoo 18 Enterprise Standards

This skill ensures that all Odoo 18 Enterprise customizations adhere to the "Standard First, Custom Later" philosophy, prioritizing seamless data flow, accounting accuracy, and clean Thai localization.

## 👥 The Supreme Council Roles
When performing tasks, maintain the perspective of the following roles:
- **Project Manager (PM):** Supplement core, don't replace it.
- **Architect:** Ensure module decoupling and migration readiness.
- **Functional Consultant:** Validate accounting and stock correctness.
- **Senior Developer:** Production-grade, core-safe code using `_inherit`.

## 🛠️ Translation & UI Standards
- **Scrap:** Always translate as **"ของเสีย"**. Avoid "เศษสินค้า".
- **Employees:** Always translate as **"พนักงาน"**.
- **Target:** Always translate as **"เป้าหมาย"**.
- **Clean UI:** Remove English text in parentheses from Thai translations (e.g., change "เสร็จสิ้น (Done)" to "เสร็จสิ้น").
- **Consistency:** Ensure terms are consistent across Form, List, and Kanban views.

## 🏭 Shopfloor & Manufacturing Standards
- **Traceability:** Capture the actual logged-in user name for all quantity adjustments.
- **Implementation:** Always use `request.env.user.name` in the backend controller to ensure reliability, avoiding frontend-only session issues.
- **Note Format:** Output logs should record the user name directly in the `note` field for auditability.

## 💰 Costing & Financial Standards
- **Landed Cost for Scrap:** Implement a flow where scrap costs from Manufacturing Orders (MO) are absorbed back into Finished Goods (FG) via Landed Costs.
- **Asset Hierarchy:**
    - Use a Parent-Child structure for complex assets.
    - Implement a `total_group_value` computed field to show the sum of (Parent + All Children) in the Hierarchy and Form views.
- **Procurement:** Enforce a **PR-to-PO Mandatory Flow** to ensure internal controls and budget validation.

## 📐 Ecosystem Harmonization & Conflict Prevention
- **Mandatory Pre-development Audit & Reuse Rule:** Before initiating any new development, you **MUST** thoroughly search, audit, and analyze all existing custom modules (the Wolapart ecosystem) and standard Odoo modules related to that business domain first.
- **Merge & Extend Existing Features (Extend, Don't Duplicate):** If there is already an existing custom module or standard feature that performs related logic or shares the same domain, you **MUST** build upon and extend that existing module or component. Creating a new, parallel custom module or duplicating fields/logic is strictly prohibited if they can coexist and be unified.
- **Strict Anti-Conflict Auditing:** You **MUST** review everything to prevent collision issues, ensuring no conflicts exist between:
  1. **Custom vs. Custom (Intra-Ecosystem):** Ensure separate custom modules do not duplicate fields, overwrite the same method twice without proper `super()` propagation, or clash on XML XPaths.
  2. **Custom vs. Standard:** Verify that custom overrides do not conflict with Odoo 18 Enterprise standard workflows or dependencies.
  3. **Custom vs. Odoo Core:** Guarantee absolute core safety and prevent upgrade issues with Odoo's framework mechanics.

## 🧪 Validation & Testing
- **Audit:** Every customization must be audited for N+1 query prevention.
- **Happy Path:** Validate the End-to-End data flow from PR to Accounting entries.
- **Regression:** Ensure new customizations do not break existing modules in the Wolapart ecosystem.

## 🔗 Module Integration Patch Notes
- When modifying `account.asset`, always check dependencies on `account_asset_related_assets`.
- When modifying `mrp.workorder`, ensure compatibility with the Parallel Console (`mrp_parallel_console`).
