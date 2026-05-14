from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image


ROOT = Path(r"C:\365_project\TheCool18e\Dev")
TOOLS_DIR = ROOT / "reports" / "accounting_manual_tools"
OUTPUT_DIR = ROOT / "manual" / "Accouting_Manual" / "generated_20260408"
IMAGE_DIR = OUTPUT_DIR / "images"
CFG_DIR = OUTPUT_DIR / "capture_configs"
SAMPLES_PATH = TOOLS_DIR / "output" / "fixed_asset_ch6_live_samples_20260410.json"
TRANSACTION_PATH = TOOLS_DIR / "output" / "fixed_asset_ch6_transactions_20260410.json"

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


def load_json(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    fixed = text.replace("\xa0", " ")
    candidates = [text, fixed]
    try:
        candidates.append(fixed.encode("latin1").decode("utf-8"))
    except Exception:
        pass
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except Exception:
            continue
    raise ValueError(f"Unable to parse {path}")


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


def union_box(boxes: list[dict], width: int, height: int) -> tuple[int, int, int, int]:
    if not boxes:
        return 0, 0, width, height
    left = min(int(b["x"]) for b in boxes)
    top = min(int(b["y"]) for b in boxes)
    right = max(int(b["x"] + b["width"]) for b in boxes)
    bottom = max(int(b["y"] + b["height"]) for b in boxes)
    margin_x = 40
    margin_top = 90
    margin_bottom = 45
    return (
        max(0, left - margin_x),
        max(0, top - margin_top),
        min(width, right + margin_x),
        min(height, bottom + margin_bottom),
    )


def crop_to_boxes(image_path: Path, meta_path: Path, out_path: Path) -> Path:
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    image = Image.open(image_path).convert("RGBA")
    box = union_box(meta.get("boxes", []), image.width, image.height)
    cropped = image.crop(box)
    cropped.save(out_path)
    return out_path


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
    annotated = IMAGE_DIR / f"{Path(spec.filename).stem}_annotated.png"
    cropped = IMAGE_DIR / f"{Path(spec.filename).stem}_annotated_crop.png"
    crop_to_boxes(annotated, meta_path, cropped)
    return cropped


def reuse_existing(stem: str, target_stem: str) -> Path:
    raw = IMAGE_DIR / f"{stem}.png"
    meta = IMAGE_DIR / f"{stem}.png.json"
    annotated = IMAGE_DIR / f"{stem}_annotated.png"
    if not raw.exists() or not meta.exists() or not annotated.exists():
        raise FileNotFoundError(f"Missing archived image bundle for {stem}")
    out = IMAGE_DIR / f"{target_stem}.png"
    crop_to_boxes(annotated, meta, out)
    return out


def main() -> None:
    samples = load_json(SAMPLES_PATH)["samples"]
    transactions = load_json(TRANSACTION_PATH)
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    CFG_DIR.mkdir(parents=True, exist_ok=True)

    current_specs = [
        CaptureSpec(
            key="ch6_nav_dashboard_accounting",
            filename="ch6_nav_dashboard_accounting.png",
            target_url=f"{BASE_URL}/odoo",
            highlight_selectors=[
                {"selector": "a.o_app[data-menu-xmlid='accountant.menu_accounting']", "label": "1"},
            ],
        ),
        CaptureSpec(
            key="ch6_nav_assets",
            filename="ch6_nav_assets.png",
            target_url=f"{BASE_URL}/odoo/action-742",
            highlight_selectors=[
                {"selector": ".o_control_panel", "label": "1"},
                {"selector": "button.o_list_button_add", "label": "2"},
                {"selector": ".o_list_renderer", "label": "3"},
            ],
        ),
        CaptureSpec(
            key="ch6_nav_asset_models",
            filename="ch6_nav_asset_models.png",
            target_url=f"{BASE_URL}/odoo/action-743",
            highlight_selectors=[
                {"selector": ".o_control_panel", "label": "1"},
                {"selector": "button.o_list_button_add", "label": "2"},
                {"selector": ".o_list_renderer", "label": "3"},
            ],
        ),
        CaptureSpec(
            key="ch6_asset_model_form",
            filename="ch6_asset_model_form.png",
            target_url=f"{BASE_URL}/odoo/action-743/{samples['model_asset']['id']}",
            highlight_selectors=[
                {"selector": "[name='method']", "label": "1"},
                {"selector": "[name='account_asset_id']", "label": "2"},
                {"selector": "[name='account_depreciation_id']", "label": "3"},
                {"selector": "[name='account_depreciation_expense_id']", "label": "4"},
                {"selector": "[name='journal_id']", "label": "5"},
            ],
        ),
        CaptureSpec(
            key="ch6_asset_draft_form",
            filename="ch6_asset_draft_form.png",
            target_url=f"{BASE_URL}/odoo/action-742/{samples['draft_asset']['id']}",
            highlight_selectors=[
                {"selector": "button[name='validate']", "label": "1"},
                {"selector": "[name='model_id']", "label": "2"},
                {"selector": "[name='original_value']", "label": "3"},
                {"selector": "[name='acquisition_date']", "label": "4"},
                {"selector": "[name='journal_id']", "label": "5"},
            ],
        ),
        CaptureSpec(
            key="ch6_asset_open_form",
            filename="ch6_asset_open_form.png",
            target_url=f"{BASE_URL}/odoo/action-742/{samples['open_asset']['id']}",
            highlight_selectors=[
                {"selector": "button[name='action_asset_modify']", "label": "1"},
                {"selector": "button[name='open_entries']", "label": "2"},
                {"selector": "[name='book_value']", "label": "3"},
                {"selector": "[name='original_value']", "label": "4"},
                {"selector": "[name='account_depreciation_expense_id']", "label": "5"},
            ],
        ),
        CaptureSpec(
            key="ch6_nav_fixed_asset_report",
            filename="ch6_nav_fixed_asset_report.png",
            target_url=f"{BASE_URL}/odoo/action-1550",
            highlight_selectors=[
                {"selector": ".o_control_panel", "label": "1"},
                {"selector": ".o_content", "label": "2"},
            ],
        ),
        CaptureSpec(
            key="ch6_asset_sell_form",
            filename="ch6_asset_sell_form.png",
            target_url=f"{BASE_URL}/odoo/action-742/{transactions['sell_asset']['id']}",
            highlight_selectors=[
                {"selector": ".o_form_statusbar", "label": "1"},
                {"selector": "[name='disposal_date']", "label": "2"},
                {"selector": "[name='book_value']", "label": "3"},
                {"selector": ".o_form_sheet", "label": "4"},
            ],
        ),
        CaptureSpec(
            key="ch6_asset_dispose_form",
            filename="ch6_asset_dispose_form.png",
            target_url=f"{BASE_URL}/odoo/action-742/{transactions['dispose_asset']['id']}",
            highlight_selectors=[
                {"selector": ".o_form_statusbar", "label": "1"},
                {"selector": "[name='disposal_date']", "label": "2"},
                {"selector": "[name='book_value']", "label": "3"},
                {"selector": ".o_form_sheet", "label": "4"},
            ],
        ),
        CaptureSpec(
            key="ch6_asset_sale_invoice",
            filename="ch6_asset_sale_invoice.png",
            target_url=f"{BASE_URL}/odoo/action-262/{transactions['sale_invoice']['id']}",
            highlight_selectors=[
                {"selector": ".o_form_statusbar", "label": "1"},
                {"selector": "[name='partner_id']", "label": "2"},
                {"selector": "[name='invoice_line_ids']", "label": "3"},
                {"selector": "[name='amount_total']", "label": "4"},
            ],
        ),
        CaptureSpec(
            key="ch6_journal_depreciation",
            filename="ch6_journal_depreciation.png",
            target_url=f"{BASE_URL}/odoo/action-261/6679",
            highlight_selectors=[
                {"selector": "div[name='journal_div']", "label": "1"},
                {"selector": "a[name='aml_tab']", "label": "2"},
                {"selector": "div[name='line_ids']", "label": "3"},
            ],
        ),
        CaptureSpec(
            key="ch6_journal_sale",
            filename="ch6_journal_sale.png",
            target_url=f"{BASE_URL}/odoo/action-261/{transactions['sale_move']['id']}",
            highlight_selectors=[
                {"selector": "div[name='journal_div']", "label": "1"},
                {"selector": "a[name='aml_tab']", "label": "2"},
                {"selector": "div[name='line_ids']", "label": "3"},
            ],
        ),
        CaptureSpec(
            key="ch6_journal_disposal",
            filename="ch6_journal_disposal.png",
            target_url=f"{BASE_URL}/odoo/action-261/{transactions['disposal_move']['id']}",
            highlight_selectors=[
                {"selector": "div[name='journal_div']", "label": "1"},
                {"selector": "a[name='aml_tab']", "label": "2"},
                {"selector": "div[name='line_ids']", "label": "3"},
            ],
        ),
    ]

    results = {}
    for spec in current_specs:
        results[spec.key] = str(capture(spec).relative_to(IMAGE_DIR))

    out_path = TOOLS_DIR / "output" / "fixed_asset_ch6_image_map_20260410.json"
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out_path)


if __name__ == "__main__":
    main()
