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
    post_nav_wait_ms: int = 4500
    post_click_wait_ms: int = 2200


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
    path = CFG_DIR / f"{spec.key}.json"
    path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


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


def make_specs() -> list[CaptureSpec]:
    return [
        CaptureSpec(
            key="nav_dashboard_manufacturing",
            filename="nav_dashboard_manufacturing_real.png",
            target_url=f"{BASE_URL}/odoo",
            highlight_selectors=[
                {"selector": "a.o_app[data-menu-xmlid='mrp.menu_mrp_root']", "label": "1"},
            ],
        ),
        CaptureSpec(
            key="nav_dashboard_inventory",
            filename="nav_dashboard_inventory_real.png",
            target_url=f"{BASE_URL}/odoo",
            highlight_selectors=[
                {"selector": "a.o_app[data-menu-xmlid='stock.menu_stock_root']", "label": "1"},
            ],
        ),
        CaptureSpec(
            key="nav_accounting_assets",
            filename="nav_accounting_assets_real.png",
            target_url=f"{BASE_URL}/odoo/action-742",
            highlight_selectors=[
                {"selector": ".o_control_panel", "label": "1"},
                {"selector": "button.o_list_button_add", "label": "2"},
                {"selector": ".o_list_renderer", "label": "3"},
            ],
        ),
        CaptureSpec(
            key="nav_accounting_asset_models",
            filename="nav_accounting_asset_models_real.png",
            target_url=f"{BASE_URL}/odoo/action-743",
            highlight_selectors=[
                {"selector": ".o_control_panel", "label": "1"},
                {"selector": "button.o_list_button_add", "label": "2"},
                {"selector": ".o_list_renderer", "label": "3"},
            ],
        ),
        CaptureSpec(
            key="nav_accounting_fixed_asset_report",
            filename="nav_accounting_fixed_asset_report_real.png",
            target_url=f"{BASE_URL}/odoo/action-1550",
            highlight_selectors=[
                {"selector": ".o_control_panel", "label": "1"},
                {"selector": ".o_content", "label": "2"},
            ],
        ),
        CaptureSpec(
            key="nav_manufacturing_orders",
            filename="nav_manufacturing_orders_real.png",
            target_url=f"{BASE_URL}/odoo/action-821",
            highlight_selectors=[
                {"selector": ".o_control_panel", "label": "1"},
                {"selector": "button.o_list_button_add", "label": "2"},
                {"selector": ".o_list_renderer", "label": "3"},
            ],
        ),
        CaptureSpec(
            key="nav_manufacturing_bom",
            filename="nav_manufacturing_bom_real.png",
            target_url=f"{BASE_URL}/odoo/action-808",
            highlight_selectors=[
                {"selector": ".o_control_panel", "label": "1"},
                {"selector": "button.o_list_button_add", "label": "2"},
                {"selector": ".o_list_renderer", "label": "3"},
            ],
        ),
        CaptureSpec(
            key="nav_manufacturing_scrap",
            filename="nav_manufacturing_scrap_real.png",
            target_url=f"{BASE_URL}/odoo/action-645",
            highlight_selectors=[
                {"selector": ".o_control_panel", "label": "1"},
                {"selector": "button.o_list_button_add", "label": "2"},
                {"selector": ".o_list_renderer", "label": "3"},
            ],
        ),
        CaptureSpec(
            key="nav_inventory_valuation",
            filename="nav_inventory_valuation_real.png",
            target_url=f"{BASE_URL}/odoo/action-705",
            highlight_selectors=[
                {"selector": ".o_control_panel", "label": "1"},
                {"selector": ".o_content", "label": "2"},
            ],
        ),
        CaptureSpec(
            key="nav_accounting_rng8",
            filename="nav_accounting_rng8_real.png",
            target_url=f"{BASE_URL}/odoo/action-1456",
            highlight_selectors=[
                {"selector": ".o_control_panel, .o_form_view", "label": "1"},
                {"selector": ".o_content", "label": "2"},
            ],
        ),
        CaptureSpec(
            key="asset_draft_form",
            filename="asset_draft_form_real.png",
            target_url=f"{BASE_URL}/odoo/action-742/11559",
            highlight_selectors=[
                {"selector": ".o_form_statusbar", "label": "1"},
                {"selector": "[name='model_id']", "label": "2"},
                {"selector": "[name='original_value']", "label": "3"},
                {"selector": "[name='acquisition_date']", "label": "4"},
            ],
        ),
        CaptureSpec(
            key="asset_running_form",
            filename="asset_running_form_real.png",
            target_url=f"{BASE_URL}/odoo/action-742/11560",
            highlight_selectors=[
                {"selector": ".o_form_statusbar", "label": "1"},
                {"selector": "[name='book_value']", "label": "2"},
                {"selector": "[name='original_value']", "label": "3"},
                {"selector": ".o_form_sheet", "label": "4"},
            ],
        ),
        CaptureSpec(
            key="asset_sell_form",
            filename="asset_sell_form_real.png",
            target_url=f"{BASE_URL}/odoo/action-742/11561",
            highlight_selectors=[
                {"selector": ".o_form_statusbar", "label": "1"},
                {"selector": "[name='disposal_date']", "label": "2"},
                {"selector": "[name='book_value']", "label": "3"},
                {"selector": ".o_form_sheet", "label": "4"},
            ],
        ),
        CaptureSpec(
            key="asset_dispose_form",
            filename="asset_dispose_form_real.png",
            target_url=f"{BASE_URL}/odoo/action-742/11562",
            highlight_selectors=[
                {"selector": ".o_form_statusbar", "label": "1"},
                {"selector": "[name='disposal_date']", "label": "2"},
                {"selector": "[name='book_value']", "label": "3"},
                {"selector": ".o_form_sheet", "label": "4"},
            ],
        ),
        CaptureSpec(
            key="asset_model_form",
            filename="asset_model_form_real.png",
            target_url=f"{BASE_URL}/odoo/action-743/10519",
            highlight_selectors=[
                {"selector": ".o_form_statusbar, .o_form_sheet", "label": "1"},
                {"selector": "[name='account_asset_id']", "label": "2"},
                {"selector": "[name='account_depreciation_id']", "label": "3"},
                {"selector": "[name='account_depreciation_expense_id']", "label": "4"},
            ],
        ),
        CaptureSpec(
            key="asset_sale_invoice",
            filename="asset_sale_invoice_real.png",
            target_url=f"{BASE_URL}/odoo/action-262/68523",
            highlight_selectors=[
                {"selector": ".o_form_statusbar", "label": "1"},
                {"selector": "[name='partner_id']", "label": "2"},
                {"selector": "[name='invoice_line_ids']", "label": "3"},
            ],
        ),
        CaptureSpec(
            key="journal_asset_sale",
            filename="journal_asset_sale_real.png",
            target_url=f"{BASE_URL}/odoo/action-261/68525",
            highlight_selectors=[
                {"selector": "div[name='journal_div']", "label": "1"},
                {"selector": "a[name='aml_tab']", "label": "2"},
                {"selector": "div[name='line_ids']", "label": "3"},
            ],
        ),
        CaptureSpec(
            key="journal_asset_disposal",
            filename="journal_asset_disposal_real.png",
            target_url=f"{BASE_URL}/odoo/action-261/68537",
            highlight_selectors=[
                {"selector": "div[name='journal_div']", "label": "1"},
                {"selector": "a[name='aml_tab']", "label": "2"},
                {"selector": "div[name='line_ids']", "label": "3"},
            ],
        ),
        CaptureSpec(
            key="journal_asset_depreciation",
            filename="journal_asset_depreciation_real.png",
            target_url=f"{BASE_URL}/odoo/action-261/6679",
            highlight_selectors=[
                {"selector": "div[name='journal_div']", "label": "1"},
                {"selector": "a[name='aml_tab']", "label": "2"},
                {"selector": "div[name='line_ids']", "label": "3"},
            ],
        ),
        CaptureSpec(
            key="manufacturing_order_form",
            filename="manufacturing_order_form_real.png",
            target_url=f"{BASE_URL}/odoo/action-821/281",
            highlight_selectors=[
                {"selector": ".o_form_statusbar", "label": "1"},
                {"selector": "[name='product_id']", "label": "2"},
                {"selector": "[name='bom_id']", "label": "3"},
                {"selector": ".o_form_sheet", "label": "4"},
            ],
        ),
        CaptureSpec(
            key="manufacturing_bom_form",
            filename="manufacturing_bom_form_real.png",
            target_url=f"{BASE_URL}/odoo/action-808/3229",
            highlight_selectors=[
                {"selector": "[name='product_tmpl_id'], [name='product_id']", "label": "1"},
                {"selector": "[name='bom_line_ids']", "label": "2"},
                {"selector": ".o_form_sheet", "label": "3"},
            ],
        ),
        CaptureSpec(
            key="product_category_fg_form",
            filename="product_category_fg_form_real.png",
            target_url=f"{BASE_URL}/odoo/action-181/2",
            highlight_selectors=[
                {"selector": "[name='property_cost_method']", "label": "1"},
                {"selector": "[name='property_valuation']", "label": "2"},
                {"selector": "[name='property_stock_valuation_account_id']", "label": "3"},
                {"selector": "[name='property_stock_account_input_categ_id']", "label": "4"},
                {"selector": "[name='property_stock_account_output_categ_id']", "label": "5"},
            ],
        ),
        CaptureSpec(
            key="product_category_rm_form",
            filename="product_category_rm_form_real.png",
            target_url=f"{BASE_URL}/odoo/action-181/112",
            highlight_selectors=[
                {"selector": "[name='property_cost_method']", "label": "1"},
                {"selector": "[name='property_valuation']", "label": "2"},
                {"selector": "[name='property_stock_valuation_account_id']", "label": "3"},
                {"selector": "[name='property_stock_account_input_categ_id']", "label": "4"},
                {"selector": "[name='property_stock_account_output_categ_id']", "label": "5"},
            ],
        ),
        CaptureSpec(
            key="journal_mfg_raw_fg02001",
            filename="journal_mfg_raw_fg02001_real.png",
            target_url=f"{BASE_URL}/odoo/action-261/68395",
            highlight_selectors=[
                {"selector": "div[name='journal_div']", "label": "1"},
                {"selector": "a[name='aml_tab']", "label": "2"},
                {"selector": "div[name='line_ids']", "label": "3"},
            ],
        ),
        CaptureSpec(
            key="journal_mfg_raw_packaging",
            filename="journal_mfg_raw_packaging_real.png",
            target_url=f"{BASE_URL}/odoo/action-261/68396",
            highlight_selectors=[
                {"selector": "div[name='journal_div']", "label": "1"},
                {"selector": "a[name='aml_tab']", "label": "2"},
                {"selector": "div[name='line_ids']", "label": "3"},
            ],
        ),
        CaptureSpec(
            key="journal_mfg_finished",
            filename="journal_mfg_finished_real.png",
            target_url=f"{BASE_URL}/odoo/action-261/68397",
            highlight_selectors=[
                {"selector": "div[name='journal_div']", "label": "1"},
                {"selector": "a[name='aml_tab']", "label": "2"},
                {"selector": "div[name='line_ids']", "label": "3"},
            ],
        ),
        CaptureSpec(
            key="manufacturing_scrap_form",
            filename="manufacturing_scrap_form_real.png",
            target_url=f"{BASE_URL}/odoo/action-645/13",
            highlight_selectors=[
                {"selector": "[name='product_id']", "label": "1"},
                {"selector": "[name='scrap_qty']", "label": "2"},
                {"selector": "[name='location_id']", "label": "3"},
                {"selector": "[name='scrap_location_id']", "label": "4"},
            ],
        ),
    ]


def main() -> None:
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    CFG_DIR.mkdir(parents=True, exist_ok=True)

    results = {}
    failures = {}
    for spec in make_specs():
        try:
            results[spec.key] = str(capture(spec))
            print(f"OK {spec.key}")
        except subprocess.CalledProcessError as exc:
            failures[spec.key] = f"capture failed: {exc}"
            print(f"FAIL {spec.key}: {exc}")
        except Exception as exc:
            failures[spec.key] = str(exc)
            print(f"FAIL {spec.key}: {exc}")

    summary_path = OUTPUT_DIR / "capture_fixed_asset_mfg_images_summary_20260409.json"
    summary_path.write_text(
        json.dumps({"results": results, "failures": failures}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Captured {len(results)} images; failures={len(failures)}")


if __name__ == "__main__":
    main()
