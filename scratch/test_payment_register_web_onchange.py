import json
from pathlib import Path

request = json.loads(Path("payment_onchange_request.json").read_text(encoding="utf-8"))
params = request["params"]
model = params["model"]
args = params["args"]
context = params.get("kwargs", {}).get("context", {})

result = env[model].with_context(context).onchange(args[1], args[2], args[3])
values = result.get("value", {})

checks = {
    "payment_type": values.get("payment_type"),
    "can_edit_wizard": values.get("can_edit_wizard"),
    "communication": values.get("communication"),
    "journal_id": values.get("journal_id"),
    "payment_method_line_id": values.get("payment_method_line_id"),
    "show_partner_bank_account": values.get("show_partner_bank_account"),
}

for key, value in checks.items():
    print(f"{key}: {value}")

assert values.get("payment_type") == "inbound", checks
assert values.get("can_edit_wizard") is True, checks
assert values.get("communication"), checks
