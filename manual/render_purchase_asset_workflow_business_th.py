from pathlib import Path

OUT_DIR = Path(r"c:\365_project\TheCool18e\Dev\manual")
SVG_PATH = OUT_DIR / "purchase_asset_workflow_business_th.svg"
HTML_PATH = OUT_DIR / "purchase_asset_workflow_business_th.html"

W, H = 3050, 1120
LEFT_BAND = 130
TOP = 40
LANE_H = 200

DARK = "#123F6D"
BLUE = "#62B5E5"
WHITE = "#FFFFFF"
LINE = "#123F6D"
FONT = "'Leelawadee UI','Tahoma','Noto Sans Thai','Arial Unicode MS',sans-serif"

LANES = [
    ("ผู้ขอซื้อ / ผู้อนุมัติ", TOP + 0 * LANE_H),
    ("ฝ่ายจัดซื้อ", TOP + 1 * LANE_H),
    ("ฝ่ายคลังสินค้า", TOP + 2 * LANE_H),
    ("ฝ่ายบัญชีเจ้าหนี้", TOP + 3 * LANE_H),
    ("ฝ่ายทะเบียนสินทรัพย์", TOP + 4 * LANE_H),
]


def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


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
    out.append(
        '<polygon points="%s" fill="%s" stroke="%s" stroke-width="3" />'
        % (" ".join(f"{x},{y}" for x, y in points), WHITE, LINE)
    )
    lines = label.split("\n")
    total_h = len(lines) * 30
    start_y = cy - total_h / 2 + 18
    out.append(text_svg(cx, start_y, lines, size=25))
    return "".join(out)


def ellipse_node(cx, cy, rx, ry, label):
    return (
        f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" '
        f'fill="{DARK}" stroke="{LINE}" stroke-width="3" />'
        + text_svg(cx, cy + 10, label, size=28, bold=True, fill=WHITE)
    )


def arrow(points, label=None, lx=None, ly=None):
    out = [
        '<polyline points="%s" fill="none" stroke="%s" stroke-width="3" marker-end="url(#arrow)" />'
        % (" ".join(f"{x},{y}" for x, y in points), LINE)
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
svg.append(text_svg(W - 420, 28, "M = ผู้ใช้งานทำ | S = ระบบทำอัตโนมัติ", size=24, bold=True, anchor="start"))

# Lane 1
l1y = TOP
svg.append(ellipse_node(200, l1y + 100, 42, 28, "เริ่ม"))
svg.append(rect_node(290, l1y + 55, 230, 90, "สร้างใบ PR\n(M)", number="1.1"))
svg.append(rect_node(580, l1y + 55, 250, 90, "ส่งใบ PR\nขออนุมัติ\n(M)", number="1.2"))
svg.append(rect_node(890, l1y + 55, 250, 90, "อนุมัติใบ PR\nระดับ 1\n(M)", number="1.3"))
svg.append(rect_node(1200, l1y + 55, 250, 90, "อนุมัติใบ PR\nระดับ 2\n(M)", number="1.4"))
svg.append(diamond_node(1600, l1y + 100, 260, 120, "ใบ PR ผ่าน\nการอนุมัติครบแล้วหรือไม่?", number="1.5"))
svg.append(rect_node(1780, l1y + 55, 320, 90, "ระบบเปิดให้สร้าง RFQ\nจาก PR ได้\n(S)", fill=BLUE, number="1.6"))
svg.append(arrow([(242, l1y + 100), (290, l1y + 100)]))
svg.append(arrow([(520, l1y + 100), (580, l1y + 100)]))
svg.append(arrow([(830, l1y + 100), (890, l1y + 100)]))
svg.append(arrow([(1140, l1y + 100), (1200, l1y + 100)]))
svg.append(arrow([(1730, l1y + 100), (1780, l1y + 100)], label="ผ่าน", lx=1742, ly=l1y + 98))

# Lane 2
l2y = TOP + LANE_H
svg.append(rect_node(220, l2y + 55, 290, 90, "สร้างใบ RFQ\nจาก PR\n(M)", number="2.1"))
svg.append(rect_node(570, l2y + 40, 320, 120, "กรอกผู้ขาย จำนวน ราคา\nและรายละเอียดการสั่งซื้อ\n(M)", number="2.2"))
svg.append(rect_node(970, l2y + 40, 380, 120, "ระบบสร้าง RFQ /\nใบสั่งซื้อฉบับร่าง\nและเปลี่ยนสถานะ PR เป็นกำลังดำเนินการ\n(S)", fill=BLUE, number="2.3"))
svg.append(diamond_node(1555, l2y + 100, 260, 120, "ใบสั่งซื้อต้อง\nขออนุมัติเพิ่มหรือไม่?", number="2.4"))
svg.append(rect_node(1750, l2y + 55, 250, 90, "อนุมัติใบสั่งซื้อ\n(M)", number="2.5"))
svg.append(rect_node(2060, l2y + 40, 350, 120, "ใบสั่งซื้ออนุมัติแล้ว\nพร้อมทำรับสินค้า\nหรือทำใบแจ้งหนี้เจ้าหนี้\n(S)", fill=BLUE, number="2.6"))
svg.append(arrow([(1940, l1y + 100), (1940, l2y + 20), (365, l2y + 20), (365, l2y + 55)]))
svg.append(arrow([(510, l2y + 100), (570, l2y + 100)]))
svg.append(arrow([(890, l2y + 100), (970, l2y + 100)]))
svg.append(arrow([(1350, l2y + 100), (1425, l2y + 100)]))
svg.append(arrow([(1685, l2y + 100), (1750, l2y + 100)], label="ต้องอนุมัติ", lx=1700, ly=l2y + 98))
svg.append(arrow([(2000, l2y + 100), (2060, l2y + 100)]))

# Lane 3
l3y = TOP + LANE_H * 2
svg.append(diamond_node(650, l3y + 100, 320, 130, "รายการที่ซื้อเป็นสินทรัพย์\nที่ต้องรับเข้าคลังก่อนหรือไม่?", number="3.1"))
svg.append(rect_node(980, l3y + 55, 350, 90, "รับสินค้าและยืนยัน\nการรับเข้าคลัง\n(M)", number="3.2"))
svg.append(rect_node(1420, l3y + 55, 310, 90, "ระบบบันทึกว่า\nรับสินค้าเรียบร้อย\n(S)", fill=BLUE, number="3.3"))
svg.append(arrow([(2235, l2y + 160), (2235, l3y + 20), (650, l3y + 20), (650, l3y + 35)]))
svg.append(arrow([(810, l3y + 100), (980, l3y + 100)], label="ต้องรับของ", lx=860, ly=l3y + 98))
svg.append(arrow([(1330, l3y + 100), (1420, l3y + 100)]))

# Lane 4
l4y = TOP + LANE_H * 3
svg.append(rect_node(220, l4y + 40, 320, 120, "สร้างใบแจ้งหนี้เจ้าหนี้\nจากใบสั่งซื้อ\n(M)", number="4.1"))
svg.append(rect_node(620, l4y + 55, 290, 90, "ตรวจสอบและยืนยัน\nใบแจ้งหนี้เจ้าหนี้\n(M)", number="4.2"))
svg.append(diamond_node(1180, l4y + 100, 350, 130, "รายการในใบแจ้งหนี้\nถูกตั้งให้เป็นสินทรัพย์\nหรือไม่?", number="4.3"))
svg.append(rect_node(1430, l4y + 40, 390, 120, "ระบบแสดงข้อความเตือน\nและปุ่มสำหรับสร้างสินทรัพย์\n(S)", fill=BLUE, number="4.4"))
svg.append(arrow([(1570, l3y + 145), (1570, l4y + 20), (380, l4y + 20), (380, l4y + 40)]))
svg.append(arrow([(490, l3y + 100), (170, l3y + 100), (170, l4y + 100), (220, l4y + 100)], label="ไม่ต้องรับของ", lx=240, ly=l3y + 98))
svg.append(arrow([(520, l4y + 100), (590, l4y + 100)]))
svg.append(arrow([(910, l4y + 100), (1005, l4y + 100)]))
svg.append(arrow([(1355, l4y + 100), (1430, l4y + 100)], label="ใช่", lx=1368, ly=l4y + 98))

# Lane 5
l5y = TOP + LANE_H * 4
svg.append(rect_node(200, l5y + 40, 330, 120, "เปิดหน้าสร้างสินทรัพย์\nจากใบแจ้งหนี้\n(M)", number="5.1"))
svg.append(rect_node(620, l5y + 40, 450, 120, "กำหนดแบบสินทรัพย์\nเลือกว่าจะแยกหลายชิ้น ผูกกับสินทรัพย์เดิม\nหรือผูกเป็นสินทรัพย์แม่\n(M)", number="5.2"))
svg.append(rect_node(1160, l5y + 40, 320, 120, "ระบบสร้างสินทรัพย์\nสถานะร่าง\n(S)", fill=BLUE, number="5.3"))
svg.append(rect_node(1570, l5y + 40, 290, 120, "ตรวจสอบข้อมูลและ\nยืนยันสินทรัพย์\n(M)", number="5.4"))
svg.append(rect_node(1950, l5y + 40, 360, 120, "ระบบคำนวณตาราง\nค่าเสื่อมราคา\n(S)", fill=BLUE, number="5.5"))
svg.append(rect_node(2400, l5y + 40, 300, 120, "บันทึกรายการ\nค่าเสื่อมราคา\n(M)", number="5.6"))
svg.append(ellipse_node(2840, l5y + 100, 42, 28, "จบ"))
svg.append(arrow([(1620, l4y + 160), (1620, l5y + 20), (365, l5y + 20), (365, l5y + 40)]))
svg.append(arrow([(530, l5y + 100), (600, l5y + 100)]))
svg.append(arrow([(1070, l5y + 100), (1160, l5y + 100)]))
svg.append(arrow([(1480, l5y + 100), (1570, l5y + 100)]))
svg.append(arrow([(1860, l5y + 100), (1950, l5y + 100)]))
svg.append(arrow([(2310, l5y + 100), (2400, l5y + 100)]))
svg.append(arrow([(2700, l5y + 100), (2798, l5y + 100)]))

svg.append("</svg>")
SVG_PATH.write_text("".join(svg), encoding="utf-8")

HTML_PATH.write_text(
    """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Purchase Asset Workflow - Business Thai</title>
  <style>
    body { margin: 0; background: #fff; display: flex; justify-content: center; align-items: flex-start; }
    img { max-width: 100%; height: auto; display: block; }
  </style>
</head>
<body>
  <img src="purchase_asset_workflow_business_th.svg" alt="workflow">
</body>
</html>
""",
    encoding="utf-8",
)

print(SVG_PATH)
print(HTML_PATH)
