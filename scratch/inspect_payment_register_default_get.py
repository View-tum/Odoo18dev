import json
from pathlib import Path

request = json.loads(Path("payment_onchange_request.json").read_text(encoding="utf-8"))
params = request["params"]
fields_spec = params["args"][3]
context = params.get("kwargs", {}).get("context", {})
fields_list = list(fields_spec)

defaults = env["account.payment.register"].with_context(context).default_get(fields_list)

for key in (
    "line_ids",
    "payment_type",
    "can_edit_wizard",
    "partner_type",
    "partner_id",
    "company_id",
    "source_amount",
    "source_amount_currency",
    "source_currency_id",
    "journal_id",
    "payment_method_line_id",
    "communication",
    "show_partner_bank_account",
):
    print(f"{key}: {defaults.get(key)}")
