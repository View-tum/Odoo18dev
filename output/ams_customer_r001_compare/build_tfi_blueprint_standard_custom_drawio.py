import json
import math
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw, ImageFont


present_dir = Path(r"C:\365_project\TheCool18e\Dev\output\AMS_PRESENT_CUSTOMER_TH")
package_dir = Path(r"C:\365_project\TheCool18e\Dev\output\ams_customer_r001_compare\AMS_R001_COMPARE_PACKAGE")
download_dir = Path(r"C:\Users\tumsu\Downloads")

drawio_name = "04B_TFI_Blueprint_Standard_vs_Custom.drawio"
preview_name = "04B_TFI_Blueprint_Standard_vs_Custom_preview.png"
json_name = "04B_TFI_Blueprint_Standard_vs_Custom.json"


@dataclass(frozen=True)
class Block:
    no: int
    code: str
    label: str
    lane: str
    x: int
    y: int
    w: int
    h: int
    shape: str
    category: str
    module: str
    standard_support: str
    custom_reason: str
    present_note: str


lanes = [
    ("sale", "ขาย", 40, 120, 185, 850, "#DBEAFE"),
    ("purchase", "ซื้อ", 245, 120, 185, 850, "#FCE7F3"),
    ("rm", "คลังวัตถุดิบ", 450, 120, 185, 850, "#DCFCE7"),
    ("eng", "วิศวกรรมการผลิต", 655, 120, 185, 850, "#E0F2FE"),
    ("quality", "ควบคุมคุณภาพสินค้า", 860, 120, 185, 850, "#ECFCCB"),
    ("planning", "วางแผนผลิต", 1065, 120, 185, 850, "#EDE9FE"),
    ("production", "ผลิต", 1270, 120, 185, 850, "#FCE7F3"),
    ("fg", "คลังสินค้าสำเร็จรูป", 1475, 120, 185, 850, "#FFEDD5"),
    ("delivery", "จัดส่งสินค้า", 1680, 120, 185, 850, "#FEF3C7"),
    ("hr", "บุคคล", 1885, 120, 185, 850, "#F1F5F9"),
    ("account", "การเงิน / บัญชี", 2090, 120, 210, 850, "#ECFCCB"),
]

category_styles = {
    "standard": {
        "label": "Standard Odoo / Configuration",
        "fill": "#16A34A",
        "stroke": "#166534",
        "font": "#FFFFFF",
    },
    "custom": {
        "label": "Custom in Odoo / Report / Approval เพิ่ม",
        "fill": "#F97316",
        "stroke": "#C2410C",
        "font": "#FFFFFF",
    },
    "external": {
        "label": "ข้อมูลอ้างอิง / Manual / Legacy",
        "fill": "#64748B",
        "stroke": "#334155",
        "font": "#FFFFFF",
    },
}

blocks = [
    Block(1, "SP", "สินค้าใหม่ ออกใบ (SP)", "sale", 65, 155, 135, 54, "rect", "custom", "Sales + Approvals + Documents", "Odoo ทำ quotation / product request / activity ได้", "ต้อง custom ถ้าต้องการเอกสาร SP ตามฟอร์มเดิมและเลขเอกสารเฉพาะ", "เปิดด้วยการอธิบายว่า SP ยังอยู่ใน Odoo แต่เป็น form/report เพิ่ม"),
    Block(2, "FA", "ออกใบ (FA)", "sale", 65, 235, 135, 54, "rect", "custom", "Sales + Quality + Documents", "Odoo รองรับ sample/quotation และแนบเอกสาร", "FA sample workflow/form เฉพาะต้อง custom หรือใช้ Approvals + report", "อธิบายว่า standard รองรับ process แต่ form FA เฉพาะต้องเพิ่ม"),
    Block(3, "QUO", "ออกใบ เสนอราคา", "sale", 65, 315, 135, 54, "rect", "standard", "Sales", "Quotation / Sales Order / pricelist / customer approval รองรับมาตรฐาน", "ไม่ต้อง custom ถ้าใช้ฟอร์มใบเสนอราคา Odoo ปรับ template ได้", "เป็นจุด standard ชัดเจนของ Sales"),
    Block(4, "PR_RM_SALE", "ออกใบ (PR) วัตถุดิบ", "sale", 65, 395, 135, 54, "rect", "custom", "Approvals + Purchase", "Odoo มี Approvals และ Purchase RFQ/PO", "PR ก่อนซื้อแบบฟอร์มเดิมและ approval matrix ต้อง config/custom", "แยกให้เห็นว่าไม่ใช่ PO standard โดยตรง"),
    Block(5, "IMR", "ออกใบขอรหัสสินค้า (IMR)", "sale", 65, 475, 135, 54, "rect", "custom", "Inventory + Sales + Approvals", "Odoo รองรับ Product Master และ internal reference", "ใบขอรหัสสินค้า/ขั้นตอนอนุมัติ master data เฉพาะต้อง custom/config", "ผูกกับการสร้าง Product Code ใน Odoo"),
    Block(6, "SO_PLAN", "สินค้ามี PO แล้ว ออกใบ (SO) + แผน", "sale", 65, 585, 135, 62, "rect", "standard", "Sales + MRP", "Sales Order เชื่อม MTO/MRP สร้าง MO/Procurement ได้", "ไม่ต้อง custom ถ้าใช้ route MTO + Manufacture/Buy", "ใช้เป็นจุดขายว่า SO ทำให้เกิดงานต่ออัตโนมัติ"),
    Block(7, "IV", "ใบกำกับภาษี (IV)", "sale", 65, 700, 135, 54, "rect", "standard", "Accounting", "Customer Invoice / Tax Invoice รองรับมาตรฐาน", "ปรับ print template ได้ถ้าต้องการหน้าตาเดิม", "เชื่อมไปบัญชีลูกหนี้"),
    Block(8, "BI", "วางบิล (BI)", "sale", 65, 780, 135, 54, "rect", "standard", "Accounting", "Payment terms / follow-up / statement รองรับ", "ถ้าต้องการใบวางบิล layout เดิมอาจทำ report เพิ่ม", "อยู่ใน Accounting standard เป็นหลัก"),
    Block(9, "PR_COLLECT", "รวบรวม (PR) คัดแยก", "purchase", 270, 395, 135, 54, "rect", "custom", "Approvals + Purchase", "Odoo รวม demand เป็น replenishment/RFQ ได้", "หน้ารวบรวม PR ตาม flow เดิมต้อง config/custom เพื่อคุม approval และ grouping", "เชื่อมจากหลาย request ไปเป็น PO"),
    Block(10, "PO", "ออก (PO)", "purchase", 270, 475, 135, 54, "rect", "standard", "Purchase", "RFQ / Purchase Order / vendor / approval รองรับมาตรฐาน", "ไม่ต้อง custom ถ้าใช้ PO standard", "เป็นจุด standard ของ Purchase"),
    Block(11, "RM_RECEIVE", "รับวัตถุดิบ", "rm", 475, 155, 135, 54, "rect", "standard", "Inventory + Purchase", "Receipt จาก PO, lot/serial, valuation รองรับ", "ไม่ต้อง custom", "แสดงว่าวัตถุดิบเข้า stock ได้ครบ"),
    Block(12, "TAG_IN", "พิมพ์ Tag รับ", "rm", 475, 235, 135, 54, "rect", "standard", "Inventory + Barcode", "Label/Barcode printing รองรับด้วย report/config", "custom เฉพาะกรณี tag format ซับซ้อนมาก", "ให้ระบุเป็น standard/config"),
    Block(13, "RM_ISSUE", "จ่ายวัตถุดิบ", "rm", 475, 315, 135, 54, "rect", "standard", "Inventory + MRP", "Internal transfer / component consumption / issue to production รองรับ", "ไม่ต้อง custom", "เชื่อมไป MRP/MO"),
    Block(14, "CP_RECEIVE", "รับวัตถุดิบ ลูกค้า", "rm", 475, 475, 135, 54, "rect", "standard", "Inventory", "Customer supplied material ทำได้ด้วย owner/lot/location หรือ receipt type", "อาจต้อง config location/owner และ report แยก CP", "ไม่ใช่งานนอก Odoo"),
    Block(15, "TAG_CP", "พิมพ์ Tag รับ", "rm", 475, 555, 135, 54, "rect", "standard", "Inventory + Barcode", "พิมพ์ label/tag ตาม lot ได้", "custom เฉพาะ format tag ลูกค้า", "ใช้ Barcode/label standard"),
    Block(16, "RM_PICK_DOC", "ตัวสั่งซื้อ หน้าเบิกวัตถุดิบ", "rm", 475, 635, 135, 62, "rect", "custom", "Inventory + MRP + Report", "Odoo มี picking/component availability", "หน้าจอ/เอกสารเบิกวัตถุดิบตาม format เดิมต้อง custom report/view", "แยกเป็น custom เพราะเป็นหน้าฟอร์มเฉพาะ"),
    Block(17, "CP_ISSUE", "จ่ายวัตถุดิบ CP", "rm", 475, 780, 135, 54, "rect", "standard", "Inventory + MRP", "จ่ายวัตถุดิบลูกค้าเข้า MO ได้ด้วย lot/owner/location", "custom เฉพาะรายงาน CP แยก", "รองรับใน stock move standard"),
    Block(18, "PCC_STEP", "กำหนดขั้นตอนการผลิต (PCC)", "eng", 680, 395, 135, 62, "rect", "custom", "MRP + Quality + Documents", "Odoo มี routing, work center, operation, quality point", "PCC เป็นเอกสาร/form เฉพาะ ต้อง custom report/template", "บอกว่า routing standard แต่ PCC document custom"),
    Block(19, "QC_SPEC", "ตรวจสอบสินค้าตามข้อกำหนด", "quality", 885, 395, 135, 62, "rect", "standard", "Quality", "Quality Control Points / Checks / Worksheets รองรับ", "ไม่ต้อง custom ถ้า check list พื้นฐาน", "เชื่อม quality check กับ MO/receipt/delivery"),
    Block(20, "QC_DECISION", "ผ่าน QC?", "quality", 900, 510, 105, 70, "decision", "standard", "Quality", "Pass / Fail quality check รองรับ", "ไม่ต้อง custom ยกเว้น logic rework เฉพาะ", "Decision ต้องมี Yes/No ชัดเจน"),
    Block(21, "COA", "ออกใบ COA", "quality", 885, 635, 135, 54, "rect", "custom", "Quality + Report", "Odoo เก็บผล QC และ lot traceability ได้", "Certificate of Analysis ตามฟอร์มลูกค้าต้อง custom report", "อธิบายว่า data standard แต่ใบ COA custom"),
    Block(22, "MACHINE", "กำหนดเครื่องผลิต", "planning", 1090, 155, 135, 54, "rect", "standard", "MRP", "Work Center / operation planning รองรับ", "ไม่ต้อง custom", "เชื่อมกำลังการผลิตกับ WO"),
    Block(23, "FG_TAG", "พิมพ์ Tag สินค้า", "planning", 1090, 235, 135, 54, "rect", "standard", "Inventory + Barcode", "Product/lot label printing รองรับ", "custom เฉพาะ format tag", "ให้จัดเป็น standard/config"),
    Block(24, "IS", "ออกใบเบิกวัตถุดิบ (IS)", "planning", 1090, 315, 135, 54, "rect", "custom", "Inventory + MRP + Report", "Odoo มี component picking/issue", "เอกสาร IS ตามเลขเอกสาร/format เดิมต้อง custom report", "standard ทำ movement แต่ใบ IS เฉพาะต้องเพิ่ม"),
    Block(25, "SO_CP", "SO มีวัตถุดิบลูกค้า", "planning", 1090, 395, 135, 54, "rect", "standard", "Sales + Inventory + MRP", "SO/MO ผูก customer material ได้ด้วย owner/location/lot", "อาจ config route/location เพิ่ม", "รองรับใน Odoo ด้วย config"),
    Block(26, "WI", "ออกใบกึ่งสำเร็จรูป (WI)", "planning", 1090, 555, 135, 62, "rect", "custom", "MRP + Inventory + Report", "Odoo รองรับ semi-finished product/MO/subassembly", "เอกสาร WI ตาม format เดิมต้อง custom report", "เน้นว่า process standard แต่เอกสาร custom"),
    Block(27, "MO_PLAN", "ผลิตตามแผน", "production", 1295, 155, 135, 54, "rect", "standard", "MRP", "Manufacturing Order / Work Order รองรับ", "ไม่ต้อง custom", "เข้ากับ work order/cost ที่ตั้งใน DB แล้ว"),
    Block(28, "PROD_DONE", "ผลิตเสร็จ", "production", 1295, 235, 135, 54, "rect", "standard", "MRP + Inventory", "Mark as Done สร้าง finished goods และ valuation ได้", "ไม่ต้อง custom", "แสดงต้นทุนวิ่งเข้า valuation"),
    Block(29, "REWORK", "แก้ไข", "production", 1295, 555, 135, 54, "rect", "standard", "MRP + Quality", "Rework/scrap/quality alert ทำได้ด้วย MO/Quality", "custom เฉพาะ rework policy ซับซ้อน", "เชื่อมจาก QC fail"),
    Block(30, "PI", "รับสินค้าเข้าคลัง (PI)", "fg", 1500, 475, 135, 54, "rect", "standard", "Inventory + MRP", "Finished goods receipt จาก MO รองรับ", "ไม่ต้อง custom", "เป็น stock valuation layer รับเข้า"),
    Block(31, "FG_ISSUE_SO", "จ่ายสินค้าตามใบ SO", "fg", 1500, 635, 135, 54, "rect", "standard", "Inventory + Sales", "Delivery Order จาก SO รองรับ", "ไม่ต้อง custom", "เชื่อมส่งสินค้า"),
    Block(32, "PACK_CHECK", "ตรวจสอบก่อนแพ็คขนส่งสินค้า", "delivery", 1705, 555, 135, 62, "rect", "standard", "Inventory + Quality", "Quality check ก่อน delivery / packing operation รองรับ", "custom เฉพาะ checklist/report เฉพาะ", "ใช้ quality point บน delivery ได้"),
    Block(33, "CUSTOMER_RM_DEL", "รับวัตถุดิบลูกค้า", "delivery", 1705, 635, 135, 54, "rect", "standard", "Inventory", "รับคืน/รับวัตถุดิบลูกค้าเข้า location ได้", "อาจ config owner/location CP", "ยังอยู่ใน Odoo"),
    Block(34, "PRODUCT_CODE_ACC", "สร้างรหัสสินค้า", "account", 2115, 155, 145, 54, "rect", "standard", "Inventory + Accounting", "Product master, internal reference, category/account mapping รองรับ", "custom เฉพาะ IMR approval/form", "ใช้ร่วมกับ IMR"),
    Block(35, "PD", "จ่ายวัตถุดิบ (PD)", "account", 2115, 235, 145, 54, "rect", "standard", "Inventory + Accounting", "Stock issue/valuation รองรับ", "ถ้า PD เป็นเอกสาร legacy ต้อง custom report", "ข้อมูล transaction อยู่ใน Odoo"),
    Block(36, "RR", "รับวัตถุดิบ (RR)", "account", 2115, 315, 145, 54, "rect", "standard", "Inventory + Accounting", "Receipt/valuation/vendor bill matching รองรับ", "ถ้า RR เป็นเอกสาร legacy ต้อง custom report", "รับเข้าและ valuation standard"),
    Block(37, "PS", "จ่ายหนี้ (PS)", "account", 2115, 395, 145, 54, "rect", "standard", "Accounting", "Vendor Payment รองรับ", "custom เฉพาะชื่อเอกสาร/รายงานเดิม", "อยู่ใน AP standard"),
    Block(38, "RE", "ใบเสร็จ (RE)", "account", 2115, 780, 145, 54, "rect", "standard", "Accounting", "Customer Payment/Receipt รองรับ", "custom เฉพาะรูปแบบใบเสร็จเดิม", "อยู่ใน AR/payment standard"),
]

edges = [
    ("SP", "FA", ""),
    ("FA", "QUO", ""),
    ("QUO", "SO_PLAN", "ชนะงาน"),
    ("PR_RM_SALE", "PR_COLLECT", ""),
    ("PR_COLLECT", "PO", ""),
    ("PO", "RM_RECEIVE", ""),
    ("RM_RECEIVE", "TAG_IN", ""),
    ("TAG_IN", "RM_ISSUE", ""),
    ("RM_ISSUE", "PCC_STEP", ""),
    ("CP_RECEIVE", "TAG_CP", ""),
    ("TAG_CP", "RM_PICK_DOC", ""),
    ("RM_PICK_DOC", "CP_ISSUE", ""),
    ("PCC_STEP", "QC_SPEC", ""),
    ("QC_SPEC", "QC_DECISION", ""),
    ("QC_DECISION", "COA", "Yes"),
    ("QC_DECISION", "REWORK", "No"),
    ("PCC_STEP", "MACHINE", ""),
    ("MACHINE", "FG_TAG", ""),
    ("FG_TAG", "IS", ""),
    ("SO_PLAN", "SO_CP", ""),
    ("SO_CP", "WI", ""),
    ("IS", "MO_PLAN", ""),
    ("WI", "MO_PLAN", ""),
    ("MO_PLAN", "PROD_DONE", ""),
    ("PROD_DONE", "PI", ""),
    ("REWORK", "PROD_DONE", "Rework OK"),
    ("PI", "FG_ISSUE_SO", ""),
    ("FG_ISSUE_SO", "PACK_CHECK", ""),
    ("PACK_CHECK", "CUSTOMER_RM_DEL", ""),
    ("FG_ISSUE_SO", "IV", ""),
    ("IV", "BI", ""),
    ("IMR", "PRODUCT_CODE_ACC", ""),
    ("PRODUCT_CODE_ACC", "PCC_STEP", ""),
    ("RM_RECEIVE", "RR", ""),
    ("RM_ISSUE", "PD", ""),
    ("PO", "PS", ""),
    ("BI", "RE", ""),
]

X_ORIGIN = 40
Y_ORIGIN = 120
X_SCALE = 1.42
Y_SCALE = 1.12
BLOCK_W_SCALE = 1.12
BLOCK_H_SCALE = 1.08
LANE_W_SCALE = 1.30
LANE_H_SCALE = 1.14

LONG_EDGE_TRACKS = {
    ("RM_RECEIVE", "RR"): 104,
    ("RM_ISSUE", "PD"): 1030,
    ("PO", "PS"): 1080,
    ("BI", "RE"): 1130,
    ("IMR", "PRODUCT_CODE_ACC"): 1180,
    ("PRODUCT_CODE_ACC", "PCC_STEP"): 1230,
    ("FG_ISSUE_SO", "IV"): 1280,
    ("SO_PLAN", "SO_CP"): 970,
    ("PCC_STEP", "MACHINE"): 112,
    ("PCC_STEP", "QC_SPEC"): 365,
    ("QC_SPEC", "QC_DECISION"): 470,
    ("QC_DECISION", "REWORK"): 635,
    ("QC_DECISION", "COA"): 620,
}


def tx(value):
    return int(round(X_ORIGIN + (value - X_ORIGIN) * X_SCALE))


def ty(value):
    return int(round(Y_ORIGIN + (value - Y_ORIGIN) * Y_SCALE))


def tw_block(value):
    return int(round(value * BLOCK_W_SCALE))


def th_block(value):
    return int(round(value * BLOCK_H_SCALE))


def tw_lane(value):
    return int(round(value * LANE_W_SCALE))


def th_lane(value):
    return int(round(value * LANE_H_SCALE))


def transformed_lane(lane):
    lane_id, lane_name, x, y, w, h, fill = lane
    return lane_id, lane_name, tx(x), ty(y), tw_lane(w), th_lane(h), fill


def transformed_block(block):
    return tx(block.x), ty(block.y), tw_block(block.w), th_block(block.h)


def block_center(block):
    x, y, w, h = transformed_block(block)
    return x + w / 2, y + h / 2


block_by_code = {block.code: block for block in blocks}


def edge_waypoints(source, target):
    source_block = block_by_code[source]
    target_block = block_by_code[target]
    sx, sy = block_center(source_block)
    tx2, ty2 = block_center(target_block)
    if (source, target) in LONG_EDGE_TRACKS:
        track_y = ty(LONG_EDGE_TRACKS[(source, target)])
        return [(int(round(sx)), track_y), (int(round(tx2)), track_y)]
    if abs(tx2 - sx) > 520:
        track_y = int(round((sy + ty2) / 2))
        return [(int(round(sx)), track_y), (int(round(tx2)), track_y)]
    return []


def edge_polyline(source, target):
    return [block_center(block_by_code[source])] + edge_waypoints(source, target) + [block_center(block_by_code[target])]


def page_width():
    max_x = max(tx(x) + tw_lane(w) for _, _, x, _, w, _, _ in lanes)
    return max_x + 90


def page_height():
    return ty(1320) + 70


def block_id(code):
    return "b_" + code.lower()


def shape_style(block):
    meta = category_styles[block.category]
    base = {
        "rect": "rounded=1;arcSize=8;whiteSpace=wrap;html=1;",
        "decision": "rhombus;whiteSpace=wrap;html=1;",
    }[block.shape]
    return (
        base
        + f"fillColor={meta['fill']};strokeColor={meta['stroke']};fontColor={meta['font']};"
        + "fillOpacity=88;strokeWidth=3;fontStyle=1;fontSize=10;align=center;verticalAlign=middle;spacing=5;"
    )


def cell(cell_id, value, style, x, y, w, h):
    return (
        f'<mxCell id="{cell_id}" value="{escape(value)}" style="{style}" vertex="1" parent="1">'
        f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry" /></mxCell>'
    )


def edge(cell_id, source, target, value):
    style = (
        "edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;"
        "strokeColor=#0284C7;strokeWidth=2;endArrow=block;endFill=1;"
        "fontColor=#0F172A;fontSize=10;labelBackgroundColor=#FFFFFF;"
    )
    points = edge_waypoints(source, target)
    if points:
        points_xml = "".join(f'<mxPoint x="{x}" y="{y}" />' for x, y in points)
        geometry = f'<mxGeometry relative="1" as="geometry"><Array as="points">{points_xml}</Array></mxGeometry>'
    else:
        geometry = '<mxGeometry relative="1" as="geometry" />'
    return (
        f'<mxCell id="{cell_id}" value="{escape(value)}" style="{style}" edge="1" parent="1" '
        f'source="{block_id(source)}" target="{block_id(target)}">{geometry}</mxCell>'
    )


def build_drawio():
    cells = ['<mxCell id="0" />', '<mxCell id="1" parent="0" />']
    cells.append(cell("title", "TFI Business Blueprint 22/04/2024 - Odoo Standard vs Custom Mapping", "rounded=1;whiteSpace=wrap;html=1;fillColor=#5B1747;strokeColor=#5B1747;fontColor=#FFFFFF;fontStyle=1;fontSize=22;align=center;verticalAlign=middle;", 40, 35, 1700, 52))
    legend_x = 1810
    for index, key in enumerate(["standard", "custom", "external"]):
        meta = category_styles[key]
        cells.append(cell(f"legend_{key}", meta["label"], f"rounded=1;whiteSpace=wrap;html=1;fillColor={meta['fill']};strokeColor={meta['stroke']};fillOpacity=60;strokeWidth=2;fontColor=#111827;fontStyle=1;fontSize=12;align=center;verticalAlign=middle;", legend_x, 30 + index * 40, 345, 32))
    for lane in lanes:
        lane_id, lane_name, x, y, w, h, fill = transformed_lane(lane)
        lane_style = (
            f"rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor=#94A3B8;"
            "fillOpacity=25;dashed=1;dashPattern=8 5;strokeWidth=2;"
            "fontColor=#334155;fontStyle=1;fontSize=16;align=center;verticalAlign=top;spacing=10;"
        )
        cells.append(cell(f"lane_{lane_id}", lane_name, lane_style, x, y, w, h))
    for block in blocks:
        label = f"{block.label}<br><font style=&quot;font-size:8px&quot;>{block.module}</font>"
        x, y, w, h = transformed_block(block)
        cells.append(cell(block_id(block.code), label, shape_style(block), x, y, w, h))
    for index, (source, target, label) in enumerate(edges, start=1):
        cells.append(edge(f"e_{index:03d}", source, target, label))
    graph = (
        '<mxGraphModel dx="1800" dy="1100" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" '
        f'fold="1" page="1" pageScale="1" pageWidth="{page_width()}" pageHeight="{page_height()}" math="0" shadow="0">'
        "<root>" + "".join(cells) + "</root></mxGraphModel>"
    )
    mxfile = f'<mxfile host="app.diagrams.net" modified="2026-06-22T00:00:00.000Z" agent="Codex" version="24.7.17"><diagram id="tfi-blueprint-standard-custom" name="TFI Blueprint Odoo Mapping">{graph}</diagram></mxfile>'
    for directory in [present_dir, package_dir, download_dir]:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / drawio_name).write_text(mxfile, encoding="utf-8")


def write_json():
    rows = []
    for block in blocks:
        rows.append({
            "no": block.no,
            "code": block.code,
            "label": block.label,
            "lane": next((lane_name for lane_id, lane_name, *_ in lanes if lane_id == block.lane), block.lane),
            "category": block.category,
            "category_label": category_styles[block.category]["label"],
            "module": block.module,
            "standard_support": block.standard_support,
            "custom_reason": block.custom_reason,
            "present_note": block.present_note,
        })
    summary = {
        "total": len(rows),
        "standard": sum(1 for row in rows if row["category"] == "standard"),
        "custom": sum(1 for row in rows if row["category"] == "custom"),
        "external": sum(1 for row in rows if row["category"] == "external"),
        "message": "ทุกจุดสามารถเอาเข้า Odoo ได้: ถ้าเป็น standard ให้ทำด้วย configuration/app มาตรฐาน; ถ้าเป็น custom ให้ทำเป็นรายงาน ฟอร์ม หรือ approval เพิ่มใน Odoo",
    }
    payload = {"summary": summary, "rows": rows, "edges": edges}
    for directory in [present_dir, package_dir, download_dir]:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / json_name).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def wrapped(text, width):
    lines = []
    for raw in text.split("\n"):
        line = ""
        for ch in raw:
            line += ch
            if len(line) >= width:
                lines.append(line)
                line = ""
        if line:
            lines.append(line)
    return "\n".join(lines)


def preview():
    image = Image.new("RGBA", (page_width(), page_height()), (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype(r"C:\Windows\Fonts\tahoma.ttf", 11)
        small_font = ImageFont.truetype(r"C:\Windows\Fonts\tahoma.ttf", 9)
        title_font = ImageFont.truetype(r"C:\Windows\Fonts\tahomabd.ttf", 24)
        lane_font = ImageFont.truetype(r"C:\Windows\Fonts\tahomabd.ttf", 15)
    except OSError:
        font = ImageFont.load_default()
        small_font = font
        title_font = font
        lane_font = font
    draw.rounded_rectangle((40, 35, 1740, 87), radius=8, fill="#5B1747", outline="#5B1747")
    draw.text((890, 61), "TFI Business Blueprint 22/04/2024 - Odoo Standard vs Custom Mapping", font=title_font, fill="#FFFFFF", anchor="mm")
    legend_x = 1810
    for index, key in enumerate(["standard", "custom", "external"]):
        meta = category_styles[key]
        y = 30 + index * 40
        draw.rounded_rectangle((legend_x, y, legend_x + 345, y + 32), radius=5, fill=meta["fill"], outline=meta["stroke"], width=2)
        draw.text((legend_x + 172, y + 16), meta["label"], font=small_font, fill="#FFFFFF", anchor="mm")
    for lane in lanes:
        lane_id, lane_name, x, y, w, h, fill = transformed_lane(lane)
        draw.rounded_rectangle((x, y, x + w, y + h), radius=8, fill=fill, outline="#94A3B8", width=2)
        draw.text((x + w / 2, y + 20), lane_name, font=lane_font, fill="#334155", anchor="mm")
    by_code = {block.code: block for block in blocks}
    for source, target, label in edges:
        if source not in by_code or target not in by_code:
            continue
        points = edge_polyline(source, target)
        draw.line(points, fill="#0284C7", width=2)
        x2, y2 = points[-1]
        px, py = points[-2]
        direction = 1 if x2 >= px else -1
        if abs(y2 - py) > abs(x2 - px):
            arrow = [(x2, y2), (x2 - 5, y2 - direction * 10), (x2 + 5, y2 - direction * 10)]
        else:
            arrow = [(x2, y2), (x2 - direction * 10, y2 - 5), (x2 - direction * 10, y2 + 5)]
        draw.polygon(arrow, fill="#0284C7")
        if label:
            mid_index = len(points) // 2
            lx = (points[mid_index - 1][0] + points[mid_index][0]) / 2
            ly = (points[mid_index - 1][1] + points[mid_index][1]) / 2
            draw.rounded_rectangle((lx - 22, ly - 10, lx + 42, ly + 10), radius=3, fill="#FFFFFF", outline="#CBD5E1")
            draw.text((lx + 10, ly), label, font=small_font, fill="#0F172A", anchor="mm")
    for block in blocks:
        meta = category_styles[block.category]
        x, y, w, h = transformed_block(block)
        box = (x, y, x + w, y + h)
        if block.shape == "decision":
            cx = x + w / 2
            cy = y + h / 2
            poly = [(cx, y), (x + w, cy), (cx, y + h), (x, cy)]
            draw.polygon(poly, fill=meta["fill"], outline=meta["stroke"])
            draw.line(poly + [poly[0]], fill=meta["stroke"], width=3)
        else:
            draw.rounded_rectangle(box, radius=6, fill=meta["fill"], outline=meta["stroke"], width=3)
        text = wrapped(block.label, 13)
        bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=2, align="center")
        text_x = x + (w - (bbox[2] - bbox[0])) / 2
        text_y = y + (h - (bbox[3] - bbox[1])) / 2 - 4
        draw.multiline_text((text_x, text_y), text, font=font, fill="#FFFFFF", spacing=2, align="center")
    out = image.convert("RGB")
    for directory in [present_dir, package_dir, download_dir]:
        out.save(directory / preview_name, quality=95)


build_drawio()
write_json()
preview()
print(json.dumps({
    "drawio": str(present_dir / drawio_name),
    "json": str(present_dir / json_name),
    "preview": str(present_dir / preview_name),
    "blocks": len(blocks),
}, ensure_ascii=False))
