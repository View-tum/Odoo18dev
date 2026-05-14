
from pathlib import Path
import json
OUT = Path(r"C:\365_project\TheCool18e\Dev\reports\accounting_manual_tools\output\fixed_asset_mfg_exists_check_20260409.json")
ids = {
  'draft_asset': 11559,
  'running_asset': 11560,
  'sell_asset': 11561,
  'dispose_asset': 11562,
  'sale_invoice': 68523,
  'sale_move': 68525,
  'disposal_move': 68537,
  'sample_mo': 281,
}
res = {}
for key, rid in ids.items():
    model = {
      'draft_asset':'account.asset','running_asset':'account.asset','sell_asset':'account.asset','dispose_asset':'account.asset',
      'sale_invoice':'account.move','sale_move':'account.move','disposal_move':'account.move','sample_mo':'mrp.production'}[key]
    rec = env[model].browse(rid)
    exists = bool(rec.exists())
    res[key] = {'exists': exists, 'model': model, 'name': rec.display_name if exists else ''}
OUT.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding='utf-8')
print(str(OUT))
