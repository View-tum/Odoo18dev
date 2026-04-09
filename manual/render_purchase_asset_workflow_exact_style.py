from pathlib import Path

OUT_DIR = Path(r"c:\365_project\TheCool18e\Dev\manual")
SVG_PATH = OUT_DIR / "purchase_asset_workflow_exact_style.svg"
HTML_PATH = OUT_DIR / "purchase_asset_workflow_exact_style.html"

W, H = 2400, 1120
LEFT_BAND = 120
TOP = 40
LANE_H = 200

DARK = "#123F6D"
BLUE = "#62B5E5"
WHITE = "#FFFFFF"
LINE = "#123F6D"
FONT = "'Leelawadee UI','Tahoma','Noto Sans Thai','Arial Unicode MS',sans-serif"

LANES = [
    ("ผู้อนุมัติ PR", TOP + 0 * LANE_H),
    ("ฝ่ายจัดซื้อ", TOP + 1 * LANE_H),
    ("ฝ่ายคลัง", TOP + 2 * LANE_H),
    ("ฝ่ายบัญชี", TOP + 3 * LANE_H),
    ("ฝ่ายสินทรัพย์", TOP + 4 * LANE_H),
]


def esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def text_svg(x, y, lines, size=26, bold=False, anchor="middle", fill=DARK, line_h=None):
    if isinstance(lines, str):
        lines = lines.split("\n")
    if line_h is None:
        line_h = int(size * 1.15)
    weight = "700" if bold else "400"
    parts = [
        f'<text x="{x}" y="{y}" text-anchor="{anchor}" '
        f'font-family="{FONT}" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}">'
    ]
    for i, line in enumerate(lines):
        dy = 0 if i == 0 else line_h
        parts.append(f'<tspan x="{x}" dy="{dy}">{esc(line)}</tspan>')
    parts.append("</text>")
    return "".join(parts)


def rect_node(x, y, w, h, label, fill=WHITE, number=None):
    out = []
    if number:
        out.append(text_svg(x + w / 2, y - 12, number, size=22, bold=True))
    out.append(
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
        f'fill="{fill}" stroke="{LINE}" stroke-width="3" />'
    )
    lines = label.split("\n")
    total_h = len(lines) * 32
    start_y = y + (h - total_h) / 2 + 24
    out.append(text_svg(x + w / 2, start_y, lines, size=28))
    return "".join(out)


def diamond_node(cx, cy, w, h, label, number=None):
    points = [
        (cx, cy - h / 2),
        (cx + w / 2, cy),
        (cx, cy + h / 2),
        (cx - w / 2, cy),
    ]
    out = []
    if number:
        out.append(text_svg(cx, cy - h / 2 - 12, number, size=22, bold=True))
    point_str = " ".join(f"{x},{y}" for x, y in points)
    out.append(
        f'<polygon points="{point_str}" fill="{WHITE}" '
        f'stroke="{LINE}" stroke-width="3" />'
    )
    lines = label.split("\n")
    total_h = len(lines) * 30
    start_y = cy - total_h / 2 + 18
    out.append(text_svg(cx, start_y, lines, size=26))
    return "".join(out)


def ellipse_node(cx, cy, rx, ry, label):
    return (
        f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" '
        f'fill="{DARK}" stroke="{LINE}" stroke-width="3" />'
        + text_svg(cx, cy + 10, label, size=28, bold=True, fill=WHITE)
    )


def arrow(points, label=None, lx=None, ly=None):
    point_str = " ".join(f"{x},{y}" for x, y in points)
    out = [
        f'<polyline points="{point_str}" fill="none" '
        f'stroke="{LINE}" stroke-width="3" marker-end="url(#arrow)" />'
    ]
    if label:
        if lx is None or ly is None:
            lx, ly = points[-2]
        out.append(text_svg(lx, ly - 8, label, size=22))
    return "".join(out)


def lane_band(label, y):
    cx = LEFT_BAND / 2
    cy = y + LANE_H / 2
    return (
        f'<rect x="0" y="{y}" width="{LEFT_BAND}" height="{LANE_H}" fill="{DARK}" />'
        f'<g transform="translate({cx},{cy}) rotate(-90)">'
        + text_svg(0, 0, label, size=34, bold=True, fill=WHITE)
        + "</g>"
    )


svg = []
svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
svg.append(
    '<defs>'
    '<marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">'
    '<path d="M0,0 L0,6 L9,3 z" fill="#123F6D" />'
    "</marker>"
    "</defs>"
)
svg.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="{WHITE}" />')
svg.append(
    f'<rect x="{LEFT_BAND}" y="{TOP}" width="{W - LEFT_BAND - 20}" '
    f'height="{LANE_H * 5}" fill="none" stroke="{LINE}" stroke-width="2" />'
)

for label, y in LANES:
    svg.append(lane_band(label, y))
    svg.append(
        f'<line x1="{LEFT_BAND}" y1="{y}" x2="{W - 20}" y2="{y}" '
        f'stroke="{LINE}" stroke-width="2" />'
    )

svg.append(
    f'<line x1="{LEFT_BAND}" y1="{TOP + LANE_H * 5}" x2="{W - 20}" y2="{TOP + LANE_H * 5}" '
    f'stroke="{LINE}" stroke-width="2" />'
)
svg.append(text_svg(W - 300, 28, "M = Manual | S = System", size=24, bold=True, anchor="start"))

# Lane 1: PR approval
l1y = TOP
svg.append(ellipse_node(190, l1y + 100, 42, 28, "เริ่ม"))
svg.append(rect_node(280, l1y + 55, 220, 90, "อนุมัติ PR Lv1\n(M)", number="1.1"))
svg.append(rect_node(560, l1y + 55, 220, 90, "อนุมัติ PR Lv2\n(M)", number="1.2"))
svg.append(diamond_node(940, l1y + 100, 240, 120, "PR ผ่านครบ\nทุกระดับหรือไม่?", number="1.3"))
svg.append(rect_node(1105, l1y + 55, 230, 90, "PR Approved\n(S)", fill=BLUE, number="1.4"))
svg.append(arrow([(232, l1y + 100), (280, l1y + 100)]))
svg.append(arrow([(500, l1y + 100), (560, l1y + 100)]))
svg.append(arrow([(780, l1y + 100), (820, l1y + 100)]))
svg.append(arrow([(1060, l1y + 100), (1105, l1y + 100)], label="อนุมัติ", lx=1070, ly=l1y + 98))

# Lane 2: Purchase
l2y = TOP + LANE_H
svg.append(rect_node(250, l2y + 55, 240, 90, "Create RFQ จาก PR\n(M)", number="2.1"))
svg.append(rect_node(550, l2y + 40, 260, 120, "กรอก Supplier / Qty /\nCurrency\n(M)", number="2.2"))
svg.append(rect_node(890, l2y + 40, 300, 120, "RFQ Draft / Draft PO ถูกสร้าง\nPR เปลี่ยนเป็น in_progress\n(S)", fill=BLUE, number="2.3"))
svg.append(diamond_node(1335, l2y + 100, 240, 120, "PO ต้องผ่าน\napproval หรือไม่?", number="2.4"))
svg.append(rect_node(1505, l2y + 55, 190, 90, "Approve PO\n(M)", number="2.5"))
svg.append(rect_node(1755, l2y + 40, 210, 120, "PO Approved\nstate = purchase\n(S)", fill=BLUE, number="2.6"))
svg.append(arrow([(1220, l1y + 100), (1220, l2y + 20), (370, l2y + 20), (370, l2y + 55)]))
svg.append(arrow([(490, l2y + 100), (550, l2y + 100)]))
svg.append(arrow([(810, l2y + 100), (890, l2y + 100)]))
svg.append(arrow([(1190, l2y + 100), (1215, l2y + 100)]))
svg.append(arrow([(1455, l2y + 100), (1505, l2y + 100)], label="ใช่", lx=1465, ly=l2y + 98))
svg.append(arrow([(1695, l2y + 100), (1755, l2y + 100)]))

# Lane 3: Inventory
l3y = TOP + LANE_H * 2
svg.append(diamond_node(520, l3y + 100, 260, 130, "สินทรัพย์รายการนี้\nต้องรับของหรือไม่?", number="3.1"))
svg.append(rect_node(770, l3y + 55, 280, 90, "รับสินค้า / Validate Receipt\n(M)", number="3.2"))
svg.append(rect_node(1130, l3y + 55, 250, 90, "Receipt Completed\n(S)", fill=BLUE, number="3.3"))
svg.append(arrow([(1860, l2y + 160), (1860, l3y + 20), (520, l3y + 20), (520, l3y + 35)]))
svg.append(arrow([(650, l3y + 100), (770, l3y + 100)], label="ต้องรับ", lx=690, ly=l3y + 98))
svg.append(arrow([(1050, l3y + 100), (1130, l3y + 100)]))

# Lane 4: Accounting
l4y = TOP + LANE_H * 3
svg.append(rect_node(250, l4y + 40, 260, 120, "Create Vendor Bill\nจาก PO\n(M)", number="4.1"))
svg.append(rect_node(570, l4y + 55, 240, 90, "Post Vendor Bill\n(M)", number="4.2"))
svg.append(diamond_node(1020, l4y + 100, 290, 130, "Bill line อยู่ในหมวด\nTreat as Asset หรือไม่?", number="4.3"))
svg.append(rect_node(1220, l4y + 40, 320, 120, "ระบบแสดง Alert +\nปุ่ม Create Assets\n(S)", fill=BLUE, number="4.4"))
svg.append(arrow([(1260, l3y + 145), (1260, l4y + 20), (380, l4y + 20), (380, l4y + 40)]))
svg.append(arrow([(390, l3y + 100), (160, l3y + 100), (160, l4y + 100), (250, l4y + 100)], label="ไม่ต้องรับ", lx=180, ly=l3y + 98))
svg.append(arrow([(510, l4y + 100), (570, l4y + 100)]))
svg.append(arrow([(810, l4y + 100), (875, l4y + 100)]))
svg.append(arrow([(1165, l4y + 100), (1220, l4y + 100)], label="ใช่", lx=1170, ly=l4y + 98))

# Lane 5: Asset
l5y = TOP + LANE_H * 4
svg.append(rect_node(240, l5y + 40, 280, 120, "Open Create Assets Wizard\n(M)", number="5.1"))
svg.append(rect_node(590, l5y + 40, 340, 120, "กำหนด Asset Model /\nSplit / Parent / Target\n(M)", number="5.2"))
svg.append(rect_node(1000, l5y + 40, 260, 120, "Create Asset Draft\n(S)", fill=BLUE, number="5.3"))
svg.append(rect_node(1330, l5y + 40, 240, 120, "Validate Asset\n(M)", number="5.4"))
svg.append(rect_node(1640, l5y + 40, 290, 120, "Compute Depreciation\nBoard\n(S)", fill=BLUE, number="5.5"))
svg.append(rect_node(2000, l5y + 40, 260, 120, "Post Depreciation\nJournal\n(M)", number="5.6"))
svg.append(ellipse_node(2310, l5y + 100, 42, 28, "จบ"))
svg.append(arrow([(1380, l4y + 160), (1380, l5y + 20), (380, l5y + 20), (380, l5y + 40)]))
svg.append(arrow([(520, l5y + 100), (590, l5y + 100)]))
svg.append(arrow([(930, l5y + 100), (1000, l5y + 100)]))
svg.append(arrow([(1260, l5y + 100), (1330, l5y + 100)]))
svg.append(arrow([(1570, l5y + 100), (1640, l5y + 100)]))
svg.append(arrow([(1930, l5y + 100), (2000, l5y + 100)]))
svg.append(arrow([(2260, l5y + 100), (2268, l5y + 100)]))

svg.append("</svg>")
SVG_PATH.write_text("".join(svg), encoding="utf-8")

HTML_PATH.write_text(
    """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Purchase Asset Workflow</title>
  <style>
    body { margin: 0; background: #fff; display: flex; justify-content: center; align-items: flex-start; }
    img { max-width: 100%; height: auto; display: block; }
  </style>
</head>
<body>
  <img src="purchase_asset_workflow_exact_style.svg" alt="workflow">
</body>
</html>
""",
    encoding="utf-8",
)

print(SVG_PATH)
print(HTML_PATH)
