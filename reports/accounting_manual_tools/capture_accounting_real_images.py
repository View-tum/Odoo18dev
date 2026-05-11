from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


ROOT = Path(r"C:\365_project\TheCool18e\Dev")
TOOLS_DIR = ROOT / "reports" / "accounting_manual_tools"
OUTPUT_DIR = ROOT / "manual" / "Accouting_Manual" / "generated_20260408"
IMAGE_DIR = OUTPUT_DIR / "images"
CFG_DIR = OUTPUT_DIR / "capture_configs"

BASE_URL = "http://localhost:8811"
DB = "uat"
LOGIN = "admin"
PASSWORD = "365@gmp"


@dataclass
class CaptureSpec:
    key: str
    filename: str
    target_url: str
    actions: list[dict] = field(default_factory=list)
    highlight_selectors: list[dict] = field(default_factory=list)
    post_nav_wait_ms: int = 3500
    post_click_wait_ms: int = 1800


def build_cfg(spec: CaptureSpec) -> Path:
    cfg = {
        "base_url": BASE_URL,
        "db": DB,
        "login": LOGIN,
        "password": PASSWORD,
        "output_dir": str(IMAGE_DIR),
        "filename": spec.filename,
        "target_url": spec.target_url,
        "actions": spec.actions,
        "highlight_selectors": spec.highlight_selectors,
        "post_nav_wait_ms": spec.post_nav_wait_ms,
        "post_click_wait_ms": spec.post_click_wait_ms,
    }
    out = CFG_DIR / f"{spec.key}.json"
    out.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def capture(spec: CaptureSpec) -> Path:
    cfg_path = build_cfg(spec)
    meta_path = IMAGE_DIR / f"{spec.filename}.json"
    subprocess.run(
        ["node", str(TOOLS_DIR / "capture_odoo_page.js"), str(cfg_path)],
        check=True,
        cwd=str(ROOT),
    )
    subprocess.run(
        ["python", str(TOOLS_DIR / "annotate_capture.py"), str(meta_path)],
        check=True,
        cwd=str(ROOT),
    )
    return IMAGE_DIR / f"{Path(spec.filename).stem}_annotated.png"


def main() -> None:
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    CFG_DIR.mkdir(parents=True, exist_ok=True)

    specs = [
        CaptureSpec(
            key="nav_dashboard_accounting",
            filename="nav_dashboard_accounting_real.png",
            target_url=f"{BASE_URL}/odoo",
            highlight_selectors=[
                {"selector": "a.o_app[data-menu-xmlid='accountant.menu_accounting']", "label": "1"},
            ],
        ),
        CaptureSpec(
            key="nav_dashboard_cheque",
            filename="nav_dashboard_cheque_real.png",
            target_url=f"{BASE_URL}/odoo",
            highlight_selectors=[
                {"selector": "a.o_app[data-menu-xmlid='cheque_management.menu_cheque_root']", "label": "1"},
            ],
        ),
        CaptureSpec(
            key="nav_accounting_group_payment",
            filename="nav_accounting_group_payment_real.png",
            target_url=f"{BASE_URL}/odoo/accounting",
            actions=[
                {
                    "type": "click",
                    "selector": "button[data-menu-xmlid='account.menu_finance_receivables']",
                    "wait_ms": 1600,
                },
            ],
            highlight_selectors=[
                {"selector": "button[data-menu-xmlid='account.menu_finance_receivables']", "label": "1"},
                {
                    "selector": "a[data-menu-xmlid='account_customer_group_payment.menu_account_customer_group_payment']",
                    "label": "2",
                },
            ],
        ),
        CaptureSpec(
            key="nav_accounting_vendors_bills",
            filename="nav_accounting_vendors_bills_real.png",
            target_url=f"{BASE_URL}/odoo/accounting",
            actions=[
                {
                    "type": "click",
                    "selector": "button[data-menu-xmlid='account.menu_finance_payables']",
                    "wait_ms": 1600,
                },
            ],
            highlight_selectors=[
                {"selector": "button[data-menu-xmlid='account.menu_finance_payables']", "label": "1"},
                {"selector": "a[data-menu-xmlid='account.menu_action_move_in_invoice_type']", "label": "2"},
            ],
        ),
        CaptureSpec(
            key="nav_accounting_customers_invoices",
            filename="nav_accounting_customers_invoices_real.png",
            target_url=f"{BASE_URL}/odoo/accounting",
            actions=[
                {
                    "type": "click",
                    "selector": "button[data-menu-xmlid='account.menu_finance_receivables']",
                    "wait_ms": 1600,
                },
            ],
            highlight_selectors=[
                {"selector": "button[data-menu-xmlid='account.menu_finance_receivables']", "label": "1"},
                {"selector": "a[data-menu-xmlid='account.menu_action_move_out_invoice_type']", "label": "2"},
            ],
        ),
        CaptureSpec(
            key="nav_cheque_configuration",
            filename="nav_cheque_configuration_real.png",
            target_url=f"{BASE_URL}/odoo/action-1362",
            actions=[
                {
                    "type": "click",
                    "selector": "button[data-menu-xmlid='cheque_management.menu_cheque_configuration']",
                    "wait_ms": 1600,
                },
            ],
            highlight_selectors=[
                {"selector": "button[data-menu-xmlid='cheque_management.menu_cheque_configuration']", "label": "1"},
                {"selector": "a[data-menu-xmlid='cheque_management.menu_cheque_management_config']", "label": "2"},
                {"selector": "a[data-menu-xmlid='cheque_management.dynamic_cheque_config_menu']", "label": "3"},
            ],
        ),
        CaptureSpec(
            key="nav_cheque_operations",
            filename="nav_cheque_operations_real.png",
            target_url=f"{BASE_URL}/odoo/action-1362",
            actions=[
                {
                    "type": "click",
                    "selector": "button[data-menu-xmlid='cheque_management.menu_cheque_inbound_outbound']",
                    "wait_ms": 1600,
                },
            ],
            highlight_selectors=[
                {"selector": "button[data-menu-xmlid='cheque_management.menu_cheque_inbound_outbound']", "label": "1"},
                {"selector": "a[data-menu-xmlid='cheque_management.menu_cheque_transactions']", "label": "2"},
                {"selector": "a[data-menu-xmlid='cheque_management.menu_cheque_inbound']", "label": "3"},
                {"selector": "a[data-menu-xmlid='cheque_management.menu_cheque_outbound']", "label": "4"},
                {"selector": "a[data-menu-xmlid='cheque_management.menu_cheque_paid']", "label": "5"},
            ],
        ),
        CaptureSpec(
            key="invoice_register_payment",
            filename="invoice_register_payment_real.png",
            target_url=f"{BASE_URL}/odoo/action-262/68484",
            post_nav_wait_ms=5000,
            actions=[
                {"type": "click", "selector": "button[name='action_register_payment']", "wait_ms": 2600},
            ],
            highlight_selectors=[
                {"selector": "[name='journal_id']", "label": "1"},
                {"selector": "[name='payment_method_line_id']", "label": "2"},
                {"selector": "[name='wizard_inbound_cheque_lines']", "label": "3"},
                {"selector": ".modal-footer .btn-primary", "label": "4"},
            ],
        ),
        CaptureSpec(
            key="journal_group_payment",
            filename="journal_entry_group_payment_real.png",
            target_url=f"{BASE_URL}/odoo/action-261/61636",
            post_nav_wait_ms=6500,
            highlight_selectors=[
                {"selector": "button[name='action_open_business_doc']", "label": "1"},
                {"selector": "div[name='journal_div']", "label": "2"},
                {"selector": "a[name='aml_tab']", "label": "3"},
                {"selector": "div[name='line_ids']", "label": "4"},
            ],
        ),
        CaptureSpec(
            key="journal_cheque_out_confirmed",
            filename="journal_entry_cheque_out_confirmed_real.png",
            target_url=f"{BASE_URL}/odoo/action-261/68486",
            post_nav_wait_ms=6500,
            highlight_selectors=[
                {"selector": "div[name='journal_div']", "label": "1"},
                {"selector": "a[name='aml_tab']", "label": "2"},
                {"selector": "div[name='line_ids']", "label": "3"},
            ],
        ),
        CaptureSpec(
            key="journal_cheque_out_paid",
            filename="journal_entry_cheque_out_paid_real.png",
            target_url=f"{BASE_URL}/odoo/action-261/68488",
            post_nav_wait_ms=6500,
            highlight_selectors=[
                {"selector": "div[name='journal_div']", "label": "1"},
                {"selector": "a[name='aml_tab']", "label": "2"},
                {"selector": "div[name='line_ids']", "label": "3"},
            ],
        ),
        CaptureSpec(
            key="journal_cheque_in_confirmed",
            filename="journal_entry_cheque_in_confirmed_real.png",
            target_url=f"{BASE_URL}/odoo/action-261/68493",
            post_nav_wait_ms=6500,
            highlight_selectors=[
                {"selector": "div[name='journal_div']", "label": "1"},
                {"selector": "a[name='aml_tab']", "label": "2"},
                {"selector": "div[name='line_ids']", "label": "3"},
            ],
        ),
        CaptureSpec(
            key="journal_cheque_in_paid",
            filename="journal_entry_cheque_in_paid_real.png",
            target_url=f"{BASE_URL}/odoo/action-261/68495",
            post_nav_wait_ms=6500,
            highlight_selectors=[
                {"selector": "div[name='journal_div']", "label": "1"},
                {"selector": "a[name='aml_tab']", "label": "2"},
                {"selector": "div[name='line_ids']", "label": "3"},
            ],
        ),
        CaptureSpec(
            key="journal_cheque_void_reverse",
            filename="journal_entry_cheque_void_reverse_real.png",
            target_url=f"{BASE_URL}/odoo/action-261/68492",
            post_nav_wait_ms=6500,
            highlight_selectors=[
                {"selector": "div[name='journal_div']", "label": "1"},
                {"selector": "a[name='aml_tab']", "label": "2"},
                {"selector": "div[name='line_ids']", "label": "3"},
            ],
        ),
    ]

    results = {}
    for spec in specs:
        results[spec.key] = str(capture(spec))

    summary_path = OUTPUT_DIR / "capture_real_images_summary_20260409.json"
    summary_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Captured {len(results)} images")


if __name__ == "__main__":
    main()
