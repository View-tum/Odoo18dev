import base64
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw, ImageFont


present_dir = Path(r"C:\365_project\TheCool18e\Dev\output\AMS_PRESENT_CUSTOMER_TH")
package_dir = Path(r"C:\365_project\TheCool18e\Dev\output\ams_customer_r001_compare\AMS_R001_COMPARE_PACKAGE")
download_dir = Path(r"C:\Users\tumsu\Downloads")
source_image = Path(r"C:\Users\tumsu\AppData\Local\Temp\codex-clipboard-23c64abd-5017-473b-ac40-462b2c561ab9.png")

drawio_name = "04B_TFI_Blueprint_Standard_vs_Custom.drawio"
preview_name = "04B_TFI_Blueprint_Standard_vs_Custom_preview.png"

PAGE_W = 2060
PAGE_H = 640
IMG_W = 1920
IMG_H = 543
IMG_X = 0
IMG_Y = 72


@dataclass(frozen=True)
class Overlay:
    code: str
    x: int
    y: int
    w: int
    h: int
    category: str
    shape: str = "rect"


style_map = {
    "standard": {"fill": "#16A34A", "stroke": "#166534", "label": "Standard Odoo / Configuration"},
    "custom": {"fill": "#F97316", "stroke": "#C2410C", "label": "Custom / Report / Approval เพิ่ม"},
    "reference": {"fill": "#64748B", "stroke": "#334155", "label": "Manual / External Reference"},
}


overlays = [
    Overlay("SP", 14, 119, 103, 26, "custom"),
    Overlay("FA", 14, 163, 103, 26, "custom"),
    Overlay("QUO", 14, 205, 103, 26, "standard"),
    Overlay("PR_SALE", 14, 247, 103, 26, "custom"),
    Overlay("IMR", 14, 298, 103, 26, "custom"),
    Overlay("NOTE_MAIL", 14, 341, 103, 26, "reference"),
    Overlay("SO_PLAN", 14, 384, 103, 26, "standard"),
    Overlay("IV", 14, 466, 103, 26, "standard"),
    Overlay("BI", 14, 502, 103, 26, "standard"),
    Overlay("PR_COLLECT", 193, 247, 103, 26, "custom"),
    Overlay("PO", 193, 288, 103, 26, "standard"),
    Overlay("RM_RECEIVE", 373, 119, 103, 26, "standard"),
    Overlay("TAG_IN", 373, 162, 103, 26, "standard"),
    Overlay("RM_ISSUE", 373, 202, 103, 25, "standard"),
    Overlay("CP_RECEIVE", 373, 316, 103, 26, "standard"),
    Overlay("TAG_CP", 373, 355, 103, 26, "standard"),
    Overlay("RM_PICK_DOC", 373, 400, 103, 26, "custom"),
    Overlay("CP_ISSUE", 373, 479, 103, 26, "standard"),
    Overlay("PCC_STEP", 552, 256, 103, 26, "custom"),
    Overlay("QC_SPEC", 731, 292, 103, 26, "standard"),
    Overlay("QC_DECISION", 771, 336, 32, 32, "standard", "decision"),
    Overlay("COA", 731, 417, 103, 26, "custom"),
    Overlay("MACHINE", 912, 119, 103, 26, "standard"),
    Overlay("FG_TAG", 912, 161, 103, 26, "standard"),
    Overlay("IS", 912, 202, 103, 25, "custom"),
    Overlay("SO_CP", 912, 254, 103, 26, "standard"),
    Overlay("WI", 912, 315, 103, 26, "custom"),
    Overlay("MO_PLAN", 1091, 119, 103, 26, "standard"),
    Overlay("PROD_DONE", 1091, 160, 103, 26, "standard"),
    Overlay("REWORK", 1091, 336, 103, 26, "standard"),
    Overlay("PI", 1270, 375, 103, 26, "standard"),
    Overlay("ISSUE_SO", 1270, 436, 103, 25, "standard"),
    Overlay("PACK_CHECK", 1449, 438, 103, 26, "standard"),
    Overlay("CUSTOMER_RM", 1449, 474, 103, 25, "standard"),
    Overlay("PRODUCT_CODE", 1809, 119, 103, 26, "standard"),
    Overlay("PD", 1809, 169, 103, 26, "standard"),
    Overlay("RR", 1809, 221, 103, 26, "standard"),
    Overlay("PS", 1809, 273, 103, 25, "standard"),
    Overlay("RE", 1809, 503, 103, 25, "standard"),
]


def mx_cell(cell_id, value, style, x, y, w, h):
    return (
        f'<mxCell id="{cell_id}" value="{escape(value)}" style="{style}" vertex="1" parent="1">'
        f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry" /></mxCell>'
    )


def overlay_style(overlay):
    meta = style_map[overlay.category]
    shape = {
        "decision": "rhombus;whiteSpace=wrap;html=1;",
        "document": "shape=document;whiteSpace=wrap;html=1;boundedLbl=1;",
    }.get(overlay.shape, "rounded=1;arcSize=8;whiteSpace=wrap;html=1;")
    return (
        shape
        + f"fillColor={meta['fill']};strokeColor={meta['stroke']};"
        + "strokeWidth=2;fillOpacity=24;opacity=100;fontColor=none;spacing=0;"
    )


def build_drawio_page():
    encoded = base64.b64encode(source_image.read_bytes()).decode("ascii")
    cells = [
        '<mxCell id="0" />',
        '<mxCell id="1" parent="0" />',
        mx_cell(
            "title",
            "TFI business blueprint 22/04/2024 - Standard Odoo vs Custom",
            "rounded=1;arcSize=8;whiteSpace=wrap;html=1;fillColor=#FFF2CC;strokeColor=#9CA3AF;fontColor=#111827;fontStyle=1;fontSize=18;",
            510,
            14,
            620,
            38,
        ),
        mx_cell(
            "legend_standard",
            "Standard Odoo / Configuration",
            "rounded=1;arcSize=6;whiteSpace=wrap;html=1;fillColor=#16A34A;strokeColor=#166534;fontColor=#FFFFFF;fontStyle=1;fontSize=11;",
            1330,
            10,
            270,
            24,
        ),
        mx_cell(
            "legend_custom",
            "Custom / Report / Approval เพิ่ม",
            "rounded=1;arcSize=6;whiteSpace=wrap;html=1;fillColor=#F97316;strokeColor=#C2410C;fontColor=#FFFFFF;fontStyle=1;fontSize=11;",
            1330,
            39,
            270,
            24,
        ),
        mx_cell(
            "legend_ref",
            "Manual / External Reference",
            "rounded=1;arcSize=6;whiteSpace=wrap;html=1;fillColor=#64748B;strokeColor=#334155;fontColor=#FFFFFF;fontStyle=1;fontSize=11;",
            1615,
            24,
            240,
            24,
        ),
        mx_cell(
            "customer_blueprint_bg",
            "",
            f"shape=image;verticalLabelPosition=bottom;verticalAlign=top;imageAspect=0;aspect=fixed;image=data:image/png%3Bbase64,{encoded};",
            IMG_X,
            IMG_Y,
            IMG_W,
            IMG_H,
        ),
    ]
    for overlay in overlays:
        cells.append(
            mx_cell(
                "odoo_map_" + overlay.code.lower(),
                "",
                overlay_style(overlay),
                IMG_X + overlay.x,
                IMG_Y + overlay.y,
                overlay.w,
                overlay.h,
            )
        )
    return (
        f'<mxGraphModel dx="1600" dy="900" grid="1" gridSize="10" guides="1" tooltips="1" '
        f'connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{PAGE_W}" '
        f'pageHeight="{PAGE_H}" math="0" shadow="0"><root>'
        + "".join(cells)
        + "</root></mxGraphModel>"
    )


def build_drawio():
    graph = build_drawio_page()
    xml = (
        '<mxfile host="app.diagrams.net" agent="Codex" version="24.7.17" type="device">'
        f'<diagram id="tfi_exact_overlay" name="04B Exact Customer Blueprint">{graph}</diagram>'
        "</mxfile>"
    )
    for directory in [present_dir, package_dir, download_dir]:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / drawio_name).write_text(xml, encoding="utf-8")


def build_preview():
    base = Image.new("RGB", (PAGE_W, PAGE_H), "#FFFFFF")
    customer = Image.open(source_image).convert("RGB")
    base.paste(customer, (IMG_X, IMG_Y))
    overlay_layer = Image.new("RGBA", (PAGE_W, PAGE_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay_layer)
    try:
        font = ImageFont.truetype(r"C:\Windows\Fonts\tahomabd.ttf", 18)
        small_font = ImageFont.truetype(r"C:\Windows\Fonts\tahoma.ttf", 11)
    except OSError:
        font = ImageFont.load_default()
        small_font = font
    draw.rounded_rectangle((510, 14, 1130, 52), radius=8, fill="#FFF2CC", outline="#9CA3AF", width=1)
    draw.text((820, 33), "TFI business blueprint 22/04/2024 - Standard Odoo vs Custom", fill="#111827", font=font, anchor="mm")
    legend = [("standard", 1330, 10), ("custom", 1330, 39), ("reference", 1615, 24)]
    for category, x, y in legend:
        meta = style_map[category]
        w = 270 if category != "reference" else 240
        draw.rounded_rectangle((x, y, x + w, y + 24), radius=4, fill=meta["fill"], outline=meta["stroke"], width=1)
        draw.text((x + w / 2, y + 12), meta["label"], fill="#FFFFFF", font=small_font, anchor="mm")
    for overlay in overlays:
        meta = style_map[overlay.category]
        rgba = tuple(int(meta["fill"][i : i + 2], 16) for i in (1, 3, 5)) + (68,)
        stroke = tuple(int(meta["stroke"][i : i + 2], 16) for i in (1, 3, 5)) + (255,)
        x1 = IMG_X + overlay.x
        y1 = IMG_Y + overlay.y
        x2 = x1 + overlay.w
        y2 = y1 + overlay.h
        if overlay.shape == "decision":
            cx = x1 + overlay.w / 2
            cy = y1 + overlay.h / 2
            poly = [(cx, y1), (x2, cy), (cx, y2), (x1, cy)]
            draw.polygon(poly, fill=rgba)
            draw.line(poly + [poly[0]], fill=stroke, width=3)
        else:
            draw.rounded_rectangle((x1, y1, x2, y2), radius=4, fill=rgba, outline=stroke, width=2)
    out = Image.alpha_composite(base.convert("RGBA"), overlay_layer).convert("RGB")
    for directory in [present_dir, package_dir, download_dir]:
        directory.mkdir(parents=True, exist_ok=True)
        out.save(directory / preview_name, quality=95)


build_drawio()
build_preview()
print({
    "drawio": str(present_dir / drawio_name),
    "preview": str(present_dir / preview_name),
    "mode": "exact_customer_blueprint_overlay",
})
