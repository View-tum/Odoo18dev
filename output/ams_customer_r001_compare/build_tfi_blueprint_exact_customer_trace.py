from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw, ImageFont


present_dir = Path(r"C:\365_project\TheCool18e\Dev\output\AMS_PRESENT_CUSTOMER_TH")
package_dir = Path(r"C:\365_project\TheCool18e\Dev\output\ams_customer_r001_compare\AMS_R001_COMPARE_PACKAGE")
download_dir = Path(r"C:\Users\tumsu\Downloads")

drawio_name = "04B_TFI_Blueprint_Standard_vs_Custom.drawio"
preview_name = "04B_TFI_Blueprint_Standard_vs_Custom_preview.png"

PAGE_W = 1945
PAGE_H = 565


@dataclass(frozen=True)
class Lane:
    code: str
    label: str
    x: int
    y: int
    w: int
    h: int
    fill: str


@dataclass(frozen=True)
class Block:
    code: str
    label: str
    x: int
    y: int
    w: int
    h: int
    category: str
    shape: str = "rect"


lanes = [
    Lane("sale", "ขาย", 13, 68, 103, 26, "#DBEAFE"),
    Lane("purchase", "ซื้อ", 193, 68, 103, 26, "#FCE7F3"),
    Lane("rm", "คลังวัตถุดิบ", 373, 68, 103, 26, "#DCFCE7"),
    Lane("eng", "วิศวกรรมการผลิต", 552, 68, 105, 26, "#0EA5E9"),
    Lane("quality", "ควบคุมคุณภาพสินค้า", 731, 68, 103, 26, "#84CC16"),
    Lane("planning", "วางแผนผลิต", 912, 68, 103, 26, "#7C3AED"),
    Lane("production", "ผลิต", 1091, 68, 103, 26, "#DB2777"),
    Lane("fg", "คลังสินค้าสำเร็จรูป", 1270, 68, 103, 26, "#F97316"),
    Lane("delivery", "จัดส่งสินค้า", 1449, 68, 103, 26, "#F59E0B"),
    Lane("hr", "บุคคล", 1629, 68, 103, 26, "#6D5A87"),
    Lane("account", "การเงิน / บัญชี", 1809, 68, 103, 26, "#BEEB7A"),
]

category_styles = {
    "standard": {"fill": "#16A34A", "stroke": "#166534", "font": "#FFFFFF"},
    "custom": {"fill": "#F97316", "stroke": "#C2410C", "font": "#FFFFFF"},
    "manual": {"fill": "#64748B", "stroke": "#334155", "font": "#FFFFFF"},
    "note": {"fill": "#FFFFFF", "stroke": "#94A3B8", "font": "#111827"},
    "connector": {"fill": "#FFFFFF", "stroke": "#475569", "font": "#111827"},
}

blocks = [
    Block("SP", "สินค้าใหม่ ออกใบ (SP)", 14, 119, 103, 26, "custom"),
    Block("FA", "ออกใบ (FA)", 14, 169, 103, 26, "custom"),
    Block("QUO", "ออกใบ เสนอราคา", 14, 219, 103, 26, "standard"),
    Block("PR_SALE", "ออกใบ (PR) วัตถุดิบ", 14, 269, 103, 26, "custom"),
    Block("IMR", "ออกใบขอ\nรหัสสินค้า (IMR)", 14, 318, 103, 28, "custom"),
    Block("NOTE_MAIL", "อ่านในแผนผลิตทุกครั้งที่ได้รับจาก Mail, กระดาษ", 14, 348, 132, 26, "note"),
    Block("SO_PLAN", "สินค้ามี PO แล้ว\nออกใบ (SO) + แผน", 14, 398, 103, 33, "standard"),
    Block("IV", "ใบกำกับภาษี (IV)", 14, 468, 103, 26, "standard"),
    Block("BI", "วางบิล (BI)", 14, 511, 103, 26, "standard"),
    Block("PR_COLLECT", "รวบรวม (PR) คัดแยก", 193, 269, 103, 26, "custom"),
    Block("PO", "ออก (PO)", 193, 319, 103, 26, "standard"),
    Block("RM_RECEIVE", "รับวัตถุดิบ", 373, 119, 103, 26, "standard"),
    Block("TAG_IN", "พิมพ์ Tag รับ", 373, 169, 103, 26, "standard"),
    Block("RM_ISSUE", "จ่ายวัตถุดิบ", 373, 219, 103, 26, "standard"),
    Block("CP_RECEIVE", "รับวัตถุดิบ ลูกค้า", 373, 318, 103, 28, "standard"),
    Block("TAG_CP", "พิมพ์ Tag รับ", 373, 368, 103, 26, "standard"),
    Block("RM_PICK_DOC", "ตัวสั่งซื้อ หน้าวัตถุดิบ", 373, 418, 103, 26, "custom"),
    Block("CP_ISSUE", "จ่ายวัตถุดิบ CP", 373, 468, 103, 26, "standard"),
    Block("PCC_STEP", "กำหนดขั้นตอนการผลิต\n(PCC)", 552, 269, 103, 31, "custom"),
    Block("QC_SPEC", "ตรวจสอบสินค้าตามข้อ\nกำหนด", 731, 293, 103, 32, "standard"),
    Block("QC_DECISION", "ผ่าน?", 772, 340, 32, 32, "standard", "decision"),
    Block("COA", "ออกใบ COA", 731, 417, 103, 26, "custom"),
    Block("MACHINE", "กำหนดเครื่องผลิต", 912, 119, 103, 26, "standard"),
    Block("FG_TAG", "พิมพ์ Tag สินค้า", 912, 169, 103, 26, "standard"),
    Block("IS", "ออกใบเบิกวัตถุดิบ (IS)", 912, 219, 103, 26, "custom"),
    Block("SO_CP", "SO มีวัตถุดิบลูกค้า", 912, 269, 103, 26, "standard"),
    Block("WI", "ออกใบกึ่งสำเร็จรูป (WI)", 912, 319, 103, 28, "custom"),
    Block("MO_PLAN", "ผลิตตามแผน", 1091, 119, 103, 26, "standard"),
    Block("PROD_DONE", "ผลิตเสร็จ", 1091, 169, 103, 26, "standard"),
    Block("JOIN_PROD", "", 1132, 294, 20, 20, "connector", "ellipse"),
    Block("REWORK", "แก้ไข", 1091, 337, 103, 26, "standard"),
    Block("PI", "รับสินค้าเข้าคลัง (PI)", 1270, 367, 103, 26, "standard"),
    Block("ISSUE_SO", "จ่ายสินค้าตามใบ SO", 1270, 417, 103, 26, "standard"),
    Block("PACK_CHECK", "ตรวจสอบก่อนแพ็ค\nขนส่งสินค้า", 1449, 417, 103, 31, "standard"),
    Block("CUSTOMER_RM", "รับวัตถุดิบลูกค้า", 1449, 467, 103, 26, "standard"),
    Block("PRODUCT_CODE", "สร้างรหัสสินค้า", 1809, 119, 103, 26, "standard"),
    Block("PD", "จ่ายวัตถุดิบ (PD)", 1809, 169, 103, 26, "standard"),
    Block("RR", "รับวัตถุดิบ (RR)", 1809, 219, 103, 26, "standard"),
    Block("PS", "จ่ายหนี้ (PS)", 1809, 269, 103, 26, "standard"),
    Block("RE", "ใบเสร็จ (RE)", 1809, 468, 103, 26, "standard"),
    Block("JOIN_QC", "", 772, 259, 20, 20, "connector", "ellipse"),
]


def c(code, side="center"):
    b = next(block for block in blocks if block.code == code)
    if side == "left":
        return b.x, b.y + b.h / 2
    if side == "right":
        return b.x + b.w, b.y + b.h / 2
    if side == "top":
        return b.x + b.w / 2, b.y
    if side == "bottom":
        return b.x + b.w / 2, b.y + b.h
    return b.x + b.w / 2, b.y + b.h / 2


lines = [
    [c("SP", "bottom"), c("FA", "top")],
    [c("FA", "bottom"), c("QUO", "top")],
    [c("QUO", "bottom"), c("PR_SALE", "top")],
    [c("PR_SALE", "bottom"), c("IMR", "top")],
    [c("IMR", "bottom"), c("NOTE_MAIL", "top")],
    [c("NOTE_MAIL", "bottom"), c("SO_PLAN", "top")],
    [c("SO_PLAN", "bottom"), c("IV", "top")],
    [c("IV", "bottom"), c("BI", "top")],
    [c("PR_SALE", "right"), c("PR_COLLECT", "left")],
    [c("PR_COLLECT", "bottom"), c("PO", "top")],
    [c("PO", "right"), (333, 332), (333, 180), c("TAG_IN", "left")],
    [c("RM_RECEIVE", "bottom"), c("TAG_IN", "top")],
    [c("TAG_IN", "bottom"), c("RM_ISSUE", "top")],
    [c("CP_RECEIVE", "bottom"), c("TAG_CP", "top")],
    [c("TAG_CP", "bottom"), c("RM_PICK_DOC", "top")],
    [c("RM_PICK_DOC", "bottom"), c("CP_ISSUE", "top")],
    [c("RM_ISSUE", "right"), (514, 232), (514, 269), c("PCC_STEP", "left")],
    [c("PR_COLLECT", "right"), (333, 282), (333, 269), c("PCC_STEP", "left")],
    [c("PCC_STEP", "right"), (694, 284), c("JOIN_QC", "left")],
    [c("JOIN_QC", "right"), c("QC_SPEC", "left")],
    [c("QC_SPEC", "bottom"), c("QC_DECISION", "top")],
    [c("QC_DECISION", "bottom"), (788, 389), c("COA", "top")],
    [c("QC_DECISION", "right"), (874, 356), c("WI", "left")],
    [c("QC_DECISION", "right"), (874, 389), (1270, 389), c("PI", "left")],
    [c("COA", "right"), (874, 430), (874, 389)],
    [c("MACHINE", "right"), c("MO_PLAN", "left")],
    [c("FG_TAG", "right"), c("PROD_DONE", "left")],
    [c("IS", "right"), (1053, 232), (1053, 305), c("JOIN_PROD", "left")],
    [c("SO_CP", "right"), c("JOIN_PROD", "left")],
    [c("WI", "right"), (1053, 333), c("REWORK", "left")],
    [c("MO_PLAN", "bottom"), c("PROD_DONE", "top")],
    [c("PROD_DONE", "bottom"), (1142, 294), c("JOIN_PROD", "top")],
    [c("JOIN_PROD", "bottom"), c("REWORK", "top")],
    [c("REWORK", "left"), (1053, 350), (1053, 305), c("JOIN_PROD", "left")],
    [c("JOIN_PROD", "right"), (1233, 305), (1233, 380), c("PI", "left")],
    [c("PI", "bottom"), c("ISSUE_SO", "top")],
    [c("ISSUE_SO", "right"), c("PACK_CHECK", "left")],
    [c("PACK_CHECK", "bottom"), c("CUSTOMER_RM", "top")],
    [c("IMR", "right"), (153, 333), (153, 398), c("SO_PLAN", "left")],
    [c("SO_PLAN", "right"), (513, 414), (513, 232), c("RM_ISSUE", "right")],
    [c("IV", "right"), (1773, 481), c("RE", "left")],
    [c("RM_RECEIVE", "right"), (1773, 132), c("PRODUCT_CODE", "left")],
    [c("RM_ISSUE", "right"), (1773, 232), c("RR", "left")],
    [c("PO", "right"), (1773, 282), c("PS", "left")],
]

labels = [
    ("ไม่ผ่าน", 820, 352),
    ("ผ่าน", 823, 389),
]

separators = [
    (153, "#22C55E"), (333, "#2563EB"), (513, "#C026D3"), (693, "#06B6D4"),
    (873, "#EF4444"), (1053, "#06B6D4"), (1233, "#7C3AED"), (1413, "#EF4444"),
    (1593, "#EF4444"), (1773, "#7C3AED"),
]


def mx_cell(cell_id, value, style, x, y, w, h):
    return (
        f'<mxCell id="{cell_id}" value="{escape(value)}" style="{style}" vertex="1" parent="1">'
        f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry" /></mxCell>'
    )


def mx_line(cell_id, pts):
    source = pts[0]
    target = pts[-1]
    middle = pts[1:-1]
    points = "".join(f'<mxPoint x="{round(x, 1)}" y="{round(y, 1)}" />' for x, y in middle)
    style = "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#374151;strokeWidth=1.3;endArrow=block;endFill=1;"
    return (
        f'<mxCell id="{cell_id}" value="" style="{style}" edge="1" parent="1">'
        f'<mxGeometry relative="1" as="geometry">'
        f'<mxPoint x="{round(source[0], 1)}" y="{round(source[1], 1)}" as="sourcePoint" />'
        f'<mxPoint x="{round(target[0], 1)}" y="{round(target[1], 1)}" as="targetPoint" />'
        f'<Array as="points">{points}</Array>'
        f'</mxGeometry></mxCell>'
    )


def mx_block(block):
    meta = category_styles[block.category]
    if block.shape == "decision":
        base = "rhombus;whiteSpace=wrap;html=1;"
    elif block.shape == "ellipse":
        base = "ellipse;whiteSpace=wrap;html=1;"
    else:
        base = "rounded=1;arcSize=8;whiteSpace=wrap;html=1;"
    style = (
        base
        + f"fillColor={meta['fill']};strokeColor={meta['stroke']};fontColor={meta['font']};"
        + "strokeWidth=2;fillOpacity=92;fontStyle=1;fontSize=8;align=center;verticalAlign=middle;spacing=2;"
    )
    return mx_cell("b_" + block.code.lower(), block.label.replace("\n", "<br>"), style, block.x, block.y, block.w, block.h)


def build_drawio():
    cells = ['<mxCell id="0" />', '<mxCell id="1" parent="0" />']
    title_style = "rounded=1;arcSize=25;whiteSpace=wrap;html=1;fillColor=#FFF3BF;strokeColor=#4B5563;fontColor=#111827;fontStyle=1;fontSize=28;align=center;verticalAlign=middle;"
    cells.append(mx_cell("title", "TFI business blueprint 22/04/2024", title_style, 630, 8, 665, 44))
    legend = [
        ("legend_std", "Standard Odoo / Configuration", "#16A34A", 1320, 14),
        ("legend_custom", "Custom เพิ่มใน Odoo", "#F97316", 1320, 50),
    ]
    for cid, text, fill, x, y in legend:
        cells.append(mx_cell(cid, text, f"rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor=#334155;fontColor=#FFFFFF;fontStyle=1;fontSize=10;align=center;verticalAlign=middle;", x, y, 230, 24))
    for lane in lanes:
        style = f"rounded=1;arcSize=8;whiteSpace=wrap;html=1;fillColor={lane.fill};strokeColor=#94A3B8;fontColor=#111827;fontStyle=1;fontSize=12;align=center;verticalAlign=middle;"
        cells.append(mx_cell("lane_" + lane.code, lane.label, style, lane.x, lane.y, lane.w, lane.h))
    for index, (x, color) in enumerate(separators, start=1):
        style = f"shape=line;html=1;strokeColor={color};strokeWidth=1.5;dashed=1;dashPattern=4 4;"
        cells.append(mx_cell(f"sep_{index}", "", style, x, 68, 1, 470))
    for index, pts in enumerate(lines, start=1):
        cells.append(mx_line(f"line_{index:03d}", pts))
    for index, (text, x, y) in enumerate(labels, start=1):
        cells.append(mx_cell(f"label_{index}", text, "rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=none;fontColor=#DC2626;fontSize=8;align=center;verticalAlign=middle;", x, y, 38, 16))
    for block in blocks:
        cells.append(mx_block(block))
    graph = (
        f'<mxGraphModel dx="1500" dy="700" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{PAGE_W}" pageHeight="{PAGE_H}" math="0" shadow="0">'
        "<root>" + "".join(cells) + "</root></mxGraphModel>"
    )
    mxfile = f'<mxfile host="app.diagrams.net" modified="2026-06-22T00:00:00.000Z" agent="Codex" version="24.7.17"><diagram id="tfi-exact-customer-blueprint" name="TFI Blueprint Exact Trace">{graph}</diagram></mxfile>'
    for directory in [present_dir, package_dir, download_dir]:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / drawio_name).write_text(mxfile, encoding="utf-8")


def draw_wrapped(draw, box, text, font, fill):
    x, y, w, h = box
    lines_out = []
    for raw in text.split("\n"):
        line = ""
        for ch in raw:
            line += ch
            if len(line) >= 12:
                lines_out.append(line)
                line = ""
        if line:
            lines_out.append(line)
    text2 = "\n".join(lines_out)
    bbox = draw.multiline_textbbox((0, 0), text2, font=font, spacing=1, align="center")
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.multiline_text((x + (w - tw) / 2, y + (h - th) / 2), text2, font=font, fill=fill, spacing=1, align="center")


def build_preview():
    img = Image.new("RGB", (PAGE_W, PAGE_H), "#FFFFFF")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(r"C:\Windows\Fonts\tahoma.ttf", 9)
        lane_font = ImageFont.truetype(r"C:\Windows\Fonts\tahomabd.ttf", 12)
        title_font = ImageFont.truetype(r"C:\Windows\Fonts\tahomabd.ttf", 28)
        small_font = ImageFont.truetype(r"C:\Windows\Fonts\tahoma.ttf", 8)
    except OSError:
        font = ImageFont.load_default()
        lane_font = font
        title_font = font
        small_font = font
    draw.rounded_rectangle((630, 8, 1295, 52), radius=20, fill="#FFF3BF", outline="#4B5563", width=1)
    draw.text((962, 30), "TFI business blueprint 22/04/2024", font=title_font, fill="#111827", anchor="mm")
    draw.rounded_rectangle((1320, 14, 1550, 38), radius=3, fill="#16A34A", outline="#334155")
    draw.text((1435, 26), "Standard Odoo / Configuration", font=small_font, fill="#FFFFFF", anchor="mm")
    draw.rounded_rectangle((1320, 50, 1550, 74), radius=3, fill="#F97316", outline="#334155")
    draw.text((1435, 62), "Custom เพิ่มใน Odoo", font=small_font, fill="#FFFFFF", anchor="mm")
    for lane in lanes:
        draw.rounded_rectangle((lane.x, lane.y, lane.x + lane.w, lane.y + lane.h), radius=4, fill=lane.fill, outline="#94A3B8")
        draw.text((lane.x + lane.w / 2, lane.y + lane.h / 2), lane.label, font=lane_font, fill="#111827", anchor="mm")
    for x, color in separators:
        y = 68
        while y < 538:
            draw.line((x, y, x, min(y + 5, 538)), fill=color, width=1)
            y += 10
    for pts in lines:
        draw.line(pts, fill="#374151", width=1)
        x2, y2 = pts[-1]
        x1, y1 = pts[-2]
        if abs(x2 - x1) >= abs(y2 - y1):
            d = 1 if x2 >= x1 else -1
            arrow = [(x2, y2), (x2 - d * 8, y2 - 4), (x2 - d * 8, y2 + 4)]
        else:
            d = 1 if y2 >= y1 else -1
            arrow = [(x2, y2), (x2 - 4, y2 - d * 8), (x2 + 4, y2 - d * 8)]
        draw.polygon(arrow, fill="#374151")
    for text, x, y in labels:
        draw.rectangle((x, y, x + 38, y + 16), fill="#FFFFFF")
        draw.text((x + 19, y + 8), text, font=small_font, fill="#DC2626", anchor="mm")
    for block in blocks:
        meta = category_styles[block.category]
        if block.shape == "decision":
            cx = block.x + block.w / 2
            cy = block.y + block.h / 2
            poly = [(cx, block.y), (block.x + block.w, cy), (cx, block.y + block.h), (block.x, cy)]
            draw.polygon(poly, fill=meta["fill"], outline=meta["stroke"])
            draw.line(poly + [poly[0]], fill=meta["stroke"], width=2)
        elif block.shape == "ellipse":
            draw.ellipse((block.x, block.y, block.x + block.w, block.y + block.h), fill=meta["fill"], outline=meta["stroke"], width=2)
        else:
            draw.rounded_rectangle((block.x, block.y, block.x + block.w, block.y + block.h), radius=4, fill=meta["fill"], outline=meta["stroke"], width=2)
        if block.label:
            draw_wrapped(draw, (block.x, block.y, block.w, block.h), block.label, font, meta["font"])
    for directory in [present_dir, package_dir, download_dir]:
        directory.mkdir(parents=True, exist_ok=True)
        img.save(directory / preview_name, quality=95)


build_drawio()
build_preview()
print({
    "drawio": str(present_dir / drawio_name),
    "preview": str(present_dir / preview_name),
    "mode": "exact_customer_trace",
})
