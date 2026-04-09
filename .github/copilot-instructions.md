# TheCool18e — AI agent guide (concise)

**Note:** Communicate in Thai only for human conversation (project convention). All code, labels, comments and docs must be English.

Quick orientation
- This repo runs an Odoo 18 development server under `server/`. Custom modules live in `custom/view_dev/` so developers can iterate without touching core `server/addons/`.

Key paths & quick facts
- `server/odoo-bin` — Odoo entrypoint (use with `-c server/odoo.conf`).
- `server/odoo.conf` — canonical config. Read it first: it lists `addons_path`, HTTP port (8811), DB connection, and other runtime settings.
	- Current `addons_path` includes: `server/addons`, `custom/addons`, `custom/view_dev`, `custom/goldmints_addon-main`.
- `custom/view_dev/` — primary place to add or modify modules (preferred).
- `custom/addons/`, `custom/goldmints_addon-main/` — third-party or legacy addons.
- `server/odoo.log` — main runtime log for stack traces and errors (check after reproducing an issue).

Module layout & manifest patterns
- Minimal module shape: `<module>/__manifest__.py`, `models/`, `views/`, `security/ir.model.access.csv` (if you add models), and `static/src/{js,css}` for assets.
- Common dependencies: Most modules depend on `["base"]` or specific Odoo apps (`["purchase", "sale", "mrp", "stock", "account"]`). Check similar modules in `custom/view_dev/` for dependency patterns.
- Assets in the manifest follow this pattern:
	- "assets": { "web.assets_backend": [ "<module>/static/src/js/foo.js", "<module>/static/src/css/foo.scss" ] }
	- Example: `custom/view_dev/mrp_parallel_console/__manifest__.py` demonstrates `web.assets_backend` entries and `ir.model.access.csv` usage.

Conventions and do-not-touch rules
- Never edit core code under `server/addons/`. Use `_inherit` to extend models/views.
- Prefix XML IDs with the module name (e.g. `mrp_parallel_console.view_bom_form_inherit`).
- Prefer modern view attributes like `invisible="expression"` and `readonly="expression"` instead of legacy `attrs` dicts in Python code.
- Module conditional loading: Use `odoo_module.get_module_path("module_name")` checks to gracefully handle optional dependencies (see `mrp_parallel_console/models/mrp_mps_parallel_machines.py`).

Run / update / debug (PowerShell examples)
- Read `server/odoo.conf` first to pick the right `http_port`, `addons_path`, and DB settings.
- Example: start the server (adjust Python path if needed):
	& 'C:\Python313\python.exe' 'C:\365_project\TheCool18e\Dev\server\odoo-bin' -c 'C:\365_project\TheCool18e\Dev\server\odoo.conf'
- Example: update one module quickly and exit (fast verification):
	& 'C:\Python313\python.exe' 'C:\365_project\TheCool18e\Dev\server\odoo-bin' -u module_name -d database_name --stop-after-init -c 'C:\365_project\TheCool18e\Dev\server\odoo.conf'
- After running a repro, check `server/odoo.log` for stack traces and the PowerShell terminal for real-time debug messages.
- For view or JS changes: modifying an asset usually requires a module update (`-u`) or server restart.

Where to look for good examples
- `custom/view_dev/mrp_parallel_console/` — full-featured example (models, views, JS/SCSS, wizards, manifest assets).
- `custom/view_dev/product_price_guard/` — small, focused example for manifest & model extension.

Agent-specific, actionable rules
- Always read `server/odoo.conf` before suggesting runtime commands (ports, addons_path, and DB). Use the exact config path when running `odoo-bin`.
- Prefer edits in `custom/view_dev/<module>`. If adding a module, include a minimal `__manifest__.py` and `security/ir.model.access.csv` when models are added.
- Preserve XML ID prefixes and any `assets` entries in manifests—these are commonly referenced by frontend templates.
- For view or JS changes, search the module's `static/src/` and manifest `assets` entries first.
- When extending models: use `_inherit = "original.model"` pattern, check dependencies in manifest, and follow existing patterns from similar modules.

When in doubt
- Point devs to these files to verify or ask about intent: `server/odoo.conf`, `server/odoo.log`, and `custom/view_dev/mrp_parallel_console/__manifest__.py`.

Keep instructions short and actionable. Ask for clarification when a change would touch core `server/` files, the DB, or deployment config.
