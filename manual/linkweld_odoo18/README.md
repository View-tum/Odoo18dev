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
- Captured 13 untouched originals, 13 deterministic numbered-circle copies, and a structured DOM extract covering 19 sections and 60 setting boxes.
- Detailed Thai chapter: `source/ACC-001_accounting_settings_th.md`.
- Next evidence batch: Accounting Configuration menus (`ACC-002` onward), followed by existing-transaction traceability.
- No Odoo configuration, master data, or transaction has been created or modified.
