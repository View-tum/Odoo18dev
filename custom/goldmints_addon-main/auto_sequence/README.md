# Auto Sequence (Monthly Autopilot)

This module auto-creates **monthly `ir.sequence.date_range`** records. No manual “Add a line” and no need to tick "Use subsequences per date_range".

- If prefix/suffix contains `%(range_year)s`, `%(range_y)s`, or `%(range_month)s`, the module auto-enables `use_date_range` and creates the current month's range on demand.
- A daily cron pre-fills **current + N future months** (N from `auto_sequence.months_ahead`, default 3).
- Safe: respects Odoo's internal locking and numbering; uses `sudo()` only to create ranges or toggle the flag.

## Usage
1. Install the module.
2. Set your sequence prefix like `APD-C/%(range_y)s/%(range_month)s/` (or any format with range tokens).
3. Generate documents normally—the module ensures monthly ranges exist automatically.

## Config
- System Parameter: `auto_sequence.months_ahead` (default `3`)

## Acceptance criteria
- Installing the module requires no extra configuration.
- For any sequence with %(range_year)s/%(range_y)s/%(range_month)s in prefix/suffix:
  - use_date_range becomes True automatically when generating a number.
  - If the current month’s range doesn’t exist, it is created with number_next=1.
  - Numbering proceeds via standard Odoo logic.
- Cron successfully pre-creates ranges for current month plus N future months.
- Sequences without range tokens are left untouched.

(Optional: see code comments for how to force this for all sequences.)
