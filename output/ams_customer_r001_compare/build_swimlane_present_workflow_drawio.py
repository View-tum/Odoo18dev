from pathlib import Path
from xml.sax.saxutils import escape
import shutil

present_path = Path(r"C:\365_project\TheCool18e\Dev\output\AMS_PRESENT_CUSTOMER_TH\04_Workflow_Business_Flow_AMS.drawio")
package_path = Path(r"C:\365_project\TheCool18e\Dev\output\ams_customer_r001_compare\AMS_R001_COMPARE_PACKAGE\06_AMS_R001_Blueprint_Swimlane_TH.drawio")
download_path = Path(r"C:\Users\tumsu\Downloads\06_AMS_R001_Blueprint_Swimlane_TH_fixed_swimlane.drawio")
detailed_download_path = Path(r"C:\Users\tumsu\Downloads\06_AMS_R001_Blueprint_Swimlane_TH_detailed_no_overlap.drawio")

PAGE_W = 3400
X0 = 280
Y0 = 220
LANE_H = 170
LANE_W = 2980

styles = {
    "title": "rounded=1;whiteSpace=wrap;html=1;fillColor=#5B1747;fontColor=#FFFFFF;strokeColor=#5B1747;fontStyle=1;fontSize=22;align=center;verticalAlign=middle;fontFamily=Arial;",
    "note": "rounded=1;whiteSpace=wrap;html=1;fillColor=#F8FAFC;fontColor=#334155;strokeColor=#CBD5E1;fontSize=13;align=left;verticalAlign=middle;spacing=12;fontFamily=Arial;",
    "lane": "rounded=0;whiteSpace=wrap;html=1;fillColor=#F8FAFC;strokeColor=#CBD5E1;fontColor=#475569;fontStyle=1;fontSize=13;align=center;verticalAlign=middle;fontFamily=Arial;",
    "lane_label": "rounded=0;whiteSpace=wrap;html=1;fillColor=#334155;strokeColor=#334155;fontColor=#FFFFFF;fontStyle=1;fontSize=13;align=center;verticalAlign=middle;fontFamily=Arial;",
    "start": "rounded=1;arcSize=50;whiteSpace=wrap;html=1;fillColor=#E2E8F0;strokeColor=#334155;fontColor=#111827;fontStyle=1;fontSize=12;align=center;verticalAlign=middle;fontFamily=Arial;",
    "user": "rounded=1;whiteSpace=wrap;html=1;fillColor=#E0F2FE;strokeColor=#0284C7;fontColor=#0C4A6E;fontSize=12;align=center;verticalAlign=middle;spacing=7;fontFamily=Arial;",
    "auto": "rounded=1;whiteSpace=wrap;html=1;fillColor=#DCFCE7;strokeColor=#16A34A;fontColor=#14532D;fontSize=12;align=center;verticalAlign=middle;spacing=7;fontFamily=Arial;",
    "approval": "rounded=1;whiteSpace=wrap;html=1;fillColor=#EDE9FE;strokeColor=#7C3AED;fontColor=#4C1D95;fontStyle=1;fontSize=12;align=center;verticalAlign=middle;spacing=7;fontFamily=Arial;",
    "decision": "rhombus;whiteSpace=wrap;html=1;fillColor=#FCE4D6;strokeColor=#9A3412;fontColor=#7C2D12;fontStyle=1;fontSize=12;align=center;verticalAlign=middle;spacing=7;fontFamily=Arial;",
    "custom": "rounded=1;whiteSpace=wrap;html=1;fillColor=#FFF7ED;strokeColor=#F97316;fontColor=#7C2D12;fontSize=12;align=center;verticalAlign=middle;spacing=7;fontFamily=Arial;",
    "doc": "shape=document;whiteSpace=wrap;html=1;boundedLbl=1;fillColor=#DBEAFE;strokeColor=#2563EB;fontColor=#1E3A8A;fontSize=12;align=center;verticalAlign=middle;spacing=7;fontFamily=Arial;",
    "edge": "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#334155;strokeWidth=1.25;endArrow=block;endFill=1;fontSize=12;fontColor=#111827;labelBackgroundColor=#FFFFFF;fontFamily=Arial;",
}


def lane_y(index):
    return Y0 + index * LANE_H


def y_mid(lane):
    return lane_y(lane) + LANE_H / 2


def y_top(lane):
    return lane_y(lane) + 18


def y_bottom(lane):
    return lane_y(lane) + LANE_H - 18


def html_label(value):
    return escape(value).replace("\n", "&lt;br&gt;")


def mxcell(cell_id, value, style, x, y, w, h):
    return (
        f'<mxCell id="{cell_id}" value="{html_label(value)}" style="{style}" vertex="1" parent="1">'
        f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry" />'
        "</mxCell>"
    )


def edge(edge_id, source, target, value="", points=None):
    geometry = '<mxGeometry relative="1" as="geometry">'
    if points:
        geometry += '<Array as="points">'
        for x, y in points:
            geometry += f'<mxPoint x="{x}" y="{y}" />'
        geometry += "</Array>"
    geometry += "</mxGeometry>"
    return (
        f'<mxCell id="{edge_id}" value="{escape(value)}" style="{styles["edge"]}" edge="1" parent="1" source="{source}" target="{target}">'
        f"{geometry}</mxCell>"
    )


def node_xy(x, lane, kind):
    return x, lane_y(lane) + (14 if kind == "decision" else 34)


def build_page(name, title, subtitle, lanes, nodes, edges):
    page_h = max(980, Y0 + len(lanes) * LANE_H + 110)
    cells = ['<mxCell id="0" />', '<mxCell id="1" parent="0" />']
    cells.append(mxcell("title", title, styles["title"], 60, 30, 3180, 58))
    cells.append(mxcell("subtitle", subtitle, styles["note"], 60, 100, 3180, 56))
    for index, lane in enumerate(lanes):
        fill = "#F8FAFC" if index % 2 == 0 else "#FFFFFF"
        lane_style = styles["lane"].replace("fillColor=#F8FAFC", f"fillColor={fill}")
        cells.append(mxcell(f"lane_bg_{index}", "", lane_style, X0, lane_y(index), LANE_W, LANE_H))
        cells.append(mxcell(f"lane_label_{index}", lane, styles["lane_label"], 60, lane_y(index), 200, LANE_H))
    for item in nodes:
        node_id, value, kind, x, lane, w, h = item
        nx, ny = node_xy(x, lane, kind)
        cells.append(mxcell(node_id, value, styles[kind], nx, ny, w, h))
    for item in edges:
        cells.append(edge(*item))
    graph = (
        f'<mxGraphModel dx="2300" dy="1200" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" '
        f'fold="1" page="1" pageScale="1" pageWidth="{PAGE_W}" pageHeight="{page_h}" math="0" shadow="0">'
        "<root>"
        + "".join(cells)
        + "</root></mxGraphModel>"
    )
    return f'<diagram id="{escape(name)}" name="{escape(name)}">{graph}</diagram>'


def legend_page():
    lanes = ["วิธีอ่าน", "สัญลักษณ์", "Decision", "สีและความหมาย", "หลักการนำเสนอ"]
    nodes = [
        ("n1", "Start / End", "start", 330, 0, 160, 58),
        ("n2", "Process", "auto", 570, 0, 160, 58),
        ("n3", "Decision?", "decision", 820, 0, 120, 100),
        ("n4", "Yes path", "auto", 1080, 0, 150, 58),
        ("n5", "No path", "custom", 1300, 0, 150, 58),
        ("n6", "Odoo Auto\nระบบทำให้", "auto", 330, 1, 170, 58),
        ("n7", "User Manual\nผู้ใช้ทำ", "user", 570, 1, 170, 58),
        ("n8", "Confirm / Approve\nตรวจและอนุมัติ", "approval", 810, 1, 180, 58),
        ("n9", "Document\nเอกสารออกจากระบบ", "doc", 1060, 1, 180, 62),
        ("n10", "Custom / Report\nต้องทำเพิ่ม", "custom", 1320, 1, 180, 58),
        ("n11", "ทุก Decision ต้องมี\nYes / No", "decision", 330, 2, 140, 100),
        ("n12", "Yes = ใช้ flow ต่อ", "auto", 590, 2, 180, 58),
        ("n13", "No = แก้ไข / ทำเพิ่ม", "custom", 850, 2, 190, 58),
        ("n14", "อ่านตาม lane ว่า\nใครเป็น owner", "user", 330, 4, 190, 58),
        ("n15", "ดูสีเพื่อแยก\nStandard / Manual / Custom", "doc", 590, 4, 260, 62),
    ]
    edges = [
        ("e1", "n1", "n2", ""),
        ("e2", "n2", "n3", ""),
        ("e3", "n3", "n4", "Yes"),
        ("e4", "n3", "n5", "No", [(900, y_bottom(0)), (1370, y_bottom(0))]),
        ("e5", "n11", "n12", "Yes"),
        ("e6", "n11", "n13", "No", [(410, y_bottom(2)), (940, y_bottom(2))]),
        ("e7", "n14", "n15", ""),
    ]
    return build_page(
        "00 วิธีอ่าน R001 Blueprint Flow",
        "วิธีอ่าน Detailed Swimlane Workflow",
        "อ่านจากซ้ายไปขวา แถวแนวนอนคือทีม/module ที่รับผิดชอบ สีบอกว่า Odoo ทำให้ ผู้ใช้ทำ หรือต้อง custom เพิ่ม",
        lanes,
        nodes,
        edges,
    )


def overall_page():
    lanes = ["Sales", "Engineering", "Planning / MRP", "Purchase", "RM Warehouse", "Manufacturing", "Quality", "FG Warehouse", "Accounting"]
    nodes = [
        ("n1", "User Manual\nRFQ / Forecast", "user", 330, 0, 160, 58),
        ("n2", "Odoo Auto\nQuotation / SO", "auto", 610, 0, 165, 58),
        ("n3", "User Manual\nConfirm / Approve SO", "approval", 890, 0, 185, 58),
        ("n4", "Odoo Auto\nProduct + BOM", "auto", 1170, 1, 170, 58),
        ("n5", "Odoo Auto\nMRP Plan", "auto", 1450, 2, 150, 58),
        ("n6", "Buy?", "decision", 1700, 2, 120, 96),
        ("n7", "Odoo Auto\nRFQ / PO", "auto", 1960, 3, 150, 58),
        ("n8", "User Manual\nConfirm PO", "approval", 2220, 3, 150, 58),
        ("n9", "Odoo Auto\nReceive RM", "auto", 2480, 4, 150, 58),
        ("n10", "Odoo Auto\nMO / WO", "auto", 1960, 5, 150, 58),
        ("n11", "User Manual\nConfirm MO", "approval", 2220, 5, 150, 58),
        ("n12", "QC Pass?", "decision", 2480, 6, 120, 96),
        ("n13", "Odoo Output\nCOA / Release", "doc", 2760, 6, 150, 62),
        ("n14", "Odoo Auto\nFG / Delivery", "auto", 3020, 7, 150, 58),
        ("n15", "Odoo Auto\nInvoice / Journal", "doc", 3020, 8, 150, 62),
        ("n16", "User Manual\nRework / Hold", "user", 2760, 5, 150, 58),
    ]
    edges = [
        ("e1", "n1", "n2", ""),
        ("e2", "n2", "n3", ""),
        ("e3", "n3", "n4", "", [(980, y_mid(1))]),
        ("e4", "n4", "n5", ""),
        ("e5", "n5", "n6", ""),
        ("e6", "n6", "n7", "Yes / Buy", [(1760, y_mid(3))]),
        ("e7", "n7", "n8", ""),
        ("e8", "n8", "n9", "", [(2300, y_mid(4))]),
        ("e9", "n9", "n10", "", [(2560, y_bottom(4)), (2035, y_bottom(4)), (2035, y_mid(5))]),
        ("e10", "n6", "n10", "No / Make", [(1760, y_mid(5))]),
        ("e11", "n10", "n11", ""),
        ("e12", "n11", "n12", "", [(2300, y_mid(6))]),
        ("e13", "n12", "n13", "Yes"),
        ("e14", "n12", "n16", "No / Rework", [(2540, y_top(6)), (2840, y_top(6)), (2840, y_mid(5))]),
        ("e15", "n13", "n14", "", [(2840, y_mid(7))]),
        ("e16", "n14", "n15", "", [(3100, y_mid(8))]),
        ("e17", "n16", "n11", "", [(2840, y_top(5)), (2300, y_top(5)), (2300, y_mid(5))]),
    ]
    return build_page(
        "01 Overall R001 Blueprint End-to-End",
        "Overall AMS End-to-End Detailed",
        "ภาพรวมละเอียดตั้งแต่รับ demand ออกแบบสินค้า วางแผน ซื้อ/ผลิต ตรวจคุณภาพ รับ-ส่งสินค้า และบันทึกบัญชี",
        lanes,
        nodes,
        edges,
    )


def sales_page():
    lanes = ["Customer", "Sales / CRM", "Engineering", "Planning / MRP", "Custom / Integration"]
    nodes = [
        ("n1", "User Manual\nRFQ / Forecast", "user", 330, 0, 160, 58),
        ("n2", "Odoo Auto\nLead / Opportunity", "auto", 560, 1, 170, 58),
        ("n3", "Odoo Auto\nQuotation", "auto", 800, 1, 150, 58),
        ("n4", "New Item?", "decision", 1010, 1, 120, 96),
        ("n5", "User Manual\nRequest Product/BOM", "user", 1210, 2, 185, 58),
        ("n6", "Odoo Auto\nUse Existing Item", "auto", 1210, 1, 175, 58),
        ("n7", "Odoo Auto\nSO Draft", "auto", 1450, 1, 150, 58),
        ("n8", "User Manual\nConfirm / Approve SO", "approval", 1660, 1, 185, 58),
        ("n9", "Custom\nForecast API", "custom", 1450, 4, 165, 58),
        ("n10", "Odoo Output\nDemand to MRP", "doc", 1900, 3, 175, 62),
    ]
    edges = [
        ("e1", "n1", "n2", ""),
        ("e2", "n2", "n3", ""),
        ("e3", "n3", "n4", ""),
        ("e4", "n4", "n5", "Yes", [(1070, y_mid(2))]),
        ("e5", "n4", "n6", "No", [(1070, y_bottom(1)), (1290, y_bottom(1))]),
        ("e6", "n5", "n7", "", [(1300, y_top(2)), (1520, y_top(2)), (1520, y_mid(1))]),
        ("e7", "n6", "n7", ""),
        ("e8", "n7", "n8", ""),
        ("e9", "n1", "n9", "API", [(410, y_bottom(0)), (1160, y_bottom(0)), (1160, y_mid(4))]),
        ("e10", "n8", "n10", "", [(1750, y_mid(3))]),
        ("e11", "n9", "n10", "", [(1530, y_bottom(4)), (1980, y_bottom(4)), (1980, y_mid(3))]),
    ]
    return build_page(
        "02 Sales + Customer Forecast API",
        "Sales + Customer Forecast API",
        "ลงรายละเอียดฝ่ายขาย: รับ RFQ/Forecast, เช็คสินค้าใหม่, confirm SO และส่ง demand เข้า MRP",
        lanes,
        nodes,
        edges,
    )


def procurement_page():
    lanes = ["Planning / MRP", "Purchase", "Approval", "Vendor", "RM Warehouse"]
    nodes = [
        ("n1", "Odoo Auto\nDemand / Reorder", "auto", 330, 0, 170, 58),
        ("n2", "Odoo Auto\nRFQ / PR Draft", "auto", 570, 1, 165, 58),
        ("n3", "Approval Need?", "decision", 800, 1, 120, 96),
        ("n4", "User Manual\nApprove PR", "approval", 1010, 2, 150, 58),
        ("n5", "Odoo Auto\nSkip Approval", "auto", 1010, 1, 150, 58),
        ("n6", "User Manual\nSelect Vendor", "user", 1220, 3, 160, 58),
        ("n7", "Price OK?", "decision", 1440, 3, 120, 96),
        ("n8", "User Manual\nRevise RFQ", "user", 1640, 3, 150, 58),
        ("n9", "Odoo Auto\nPO Draft", "auto", 1640, 1, 150, 58),
        ("n10", "User Manual\nConfirm / Approve PO", "approval", 1850, 1, 185, 58),
        ("n11", "Odoo Output\nReceive Plan", "doc", 2100, 4, 160, 62),
    ]
    edges = [
        ("e1", "n1", "n2", ""),
        ("e2", "n2", "n3", ""),
        ("e3", "n3", "n4", "Yes", [(860, y_mid(2))]),
        ("e4", "n3", "n5", "No", [(860, y_bottom(1)), (1080, y_bottom(1))]),
        ("e5", "n4", "n6", "", [(1090, y_mid(3))]),
        ("e6", "n5", "n6", "", [(1090, y_bottom(1)), (1300, y_bottom(1)), (1300, y_mid(3))]),
        ("e7", "n6", "n7", ""),
        ("e8", "n7", "n9", "Yes", [(1500, y_mid(1))]),
        ("e9", "n7", "n8", "No"),
        ("e10", "n8", "n6", "Recheck", [(1710, y_bottom(3)), (1300, y_bottom(3))]),
        ("e11", "n9", "n10", ""),
        ("e12", "n10", "n11", "", [(1940, y_mid(4))]),
    ]
    return build_page(
        "03 Procurement + PR PO Approval",
        "Procurement + PR/PO Approval",
        "ลงรายละเอียดจัดซื้อ: จาก demand เป็น RFQ/PR, อนุมัติ, เลือก vendor, confirm PO และส่งแผนรับเข้า warehouse",
        lanes,
        nodes,
        edges,
    )


def rm_warehouse_page():
    lanes = ["Purchase / Vendor", "RM Warehouse", "Quality", "Manufacturing", "Accounting"]
    nodes = [
        ("n1", "User Manual\nVendor Delivery", "user", 330, 0, 160, 58),
        ("n2", "Odoo Auto\nReceipt Draft", "auto", 560, 1, 160, 58),
        ("n3", "Customer RM?", "decision", 790, 1, 120, 96),
        ("n4", "Odoo Auto\nOwner + Lot", "auto", 1000, 1, 155, 58),
        ("n5", "Odoo Auto\nStandard Lot", "auto", 1210, 1, 155, 58),
        ("n6", "QC Required?", "decision", 1220, 2, 120, 96),
        ("n7", "User Manual\nInspect RM", "user", 1430, 2, 150, 58),
        ("n8", "Pass?", "decision", 1640, 2, 120, 96),
        ("n9", "User Manual\nApprove Release", "approval", 1850, 1, 170, 58),
        ("n10", "User Manual\nHold / Return", "user", 1850, 2, 155, 58),
        ("n11", "Odoo Output\nIssue RM", "doc", 2100, 3, 150, 62),
        ("n12", "Odoo Auto\nStock Valuation", "auto", 2100, 4, 165, 58),
    ]
    edges = [
        ("e1", "n1", "n2", ""),
        ("e2", "n2", "n3", ""),
        ("e3", "n3", "n4", "Yes"),
        ("e4", "n3", "n5", "No", [(850, y_bottom(1)), (1290, y_bottom(1))]),
        ("e5", "n4", "n6", "", [(1080, y_mid(2))]),
        ("e6", "n5", "n6", "", [(1290, y_top(1)), (1280, y_top(1)), (1280, y_mid(2))]),
        ("e7", "n6", "n7", "Yes"),
        ("e8", "n6", "n9", "No", [(1400, y_top(1)), (1930, y_top(1)), (1930, y_mid(1))]),
        ("e9", "n7", "n8", ""),
        ("e10", "n8", "n9", "Yes", [(1700, y_mid(1))]),
        ("e11", "n8", "n10", "No"),
        ("e12", "n10", "n7", "Recheck", [(1930, y_bottom(2)), (1510, y_bottom(2))]),
        ("e13", "n9", "n11", "", [(1930, y_mid(3))]),
        ("e14", "n9", "n12", "", [(1930, y_mid(4))]),
    ]
    return build_page(
        "04 RM Warehouse + Customer Supplied Material",
        "RM Warehouse + Customer Supplied Material",
        "ลงรายละเอียดคลังวัตถุดิบ: รับ RM, แยก customer supplied material, lot/owner, QC, release และ issue เข้า production",
        lanes,
        nodes,
        edges,
    )


def engineering_page():
    lanes = ["Sales", "Engineering", "Planning / MRP", "Approval", "Custom / Document"]
    nodes = [
        ("n1", "Odoo Auto\nConfirmed SO", "auto", 330, 0, 160, 58),
        ("n2", "User Manual\nCreate Product", "user", 560, 1, 160, 58),
        ("n3", "Need PCC?", "decision", 790, 1, 120, 96),
        ("n4", "Custom\nPCC / Spec Sheet", "custom", 1000, 4, 170, 58),
        ("n5", "Odoo Auto\nBOM / Routing", "auto", 1000, 2, 170, 58),
        ("n6", "User Manual\nReview BOM", "user", 1230, 1, 150, 58),
        ("n7", "Approve?", "decision", 1440, 3, 120, 96),
        ("n8", "User Manual\nConfirm / Approve BOM", "approval", 1640, 3, 185, 58),
        ("n9", "User Manual\nRevise", "user", 1640, 1, 150, 58),
        ("n10", "Odoo Output\nRelease BOM", "doc", 1880, 2, 160, 62),
        ("n11", "Odoo Auto\nMRP Ready", "auto", 2100, 2, 150, 58),
    ]
    edges = [
        ("e1", "n1", "n2", ""),
        ("e2", "n2", "n3", ""),
        ("e3", "n3", "n4", "Yes", [(850, y_mid(4))]),
        ("e4", "n3", "n5", "No", [(850, y_mid(2))]),
        ("e5", "n4", "n6", "", [(1080, y_bottom(4)), (1300, y_bottom(4)), (1300, y_mid(1))]),
        ("e6", "n5", "n6", "", [(1080, y_top(2)), (1300, y_top(2)), (1300, y_mid(1))]),
        ("e7", "n6", "n7", "", [(1300, y_mid(3))]),
        ("e8", "n7", "n8", "Yes"),
        ("e9", "n7", "n9", "No", [(1500, y_top(3)), (1710, y_top(3)), (1710, y_mid(1))]),
        ("e10", "n9", "n6", "Recheck", [(1710, y_bottom(1)), (1300, y_bottom(1))]),
        ("e11", "n8", "n10", "", [(1730, y_mid(2))]),
        ("e12", "n10", "n11", ""),
    ]
    return build_page(
        "05 Engineering + PCC BOM Routing",
        "Engineering + PCC / BOM Routing",
        "ลงรายละเอียดงาน engineering: สร้างสินค้า, PCC/spec, BOM/routing, review และ approve ก่อนปล่อยให้ MRP ใช้",
        lanes,
        nodes,
        edges,
    )


def quality_page():
    lanes = ["Production / Warehouse", "Quality", "Inventory", "Customer", "Custom / Report"]
    nodes = [
        ("n1", "Odoo Auto\nInspection Need", "auto", 330, 0, 170, 58),
        ("n2", "User Manual\nQuality Check", "user", 570, 1, 160, 58),
        ("n3", "Pass?", "decision", 800, 1, 120, 96),
        ("n4", "User Manual\nNCR / Rework", "user", 1010, 1, 160, 58),
        ("n5", "Odoo Output\nCOA Draft", "doc", 1010, 3, 150, 62),
        ("n6", "User Manual\nApprove COA", "approval", 1230, 1, 155, 58),
        ("n7", "Odoo Auto\nRelease Lot", "auto", 1450, 2, 150, 58),
        ("n8", "Custom\nDPPM Report", "custom", 1670, 4, 160, 58),
        ("n9", "Odoo Output\nCustomer COA", "doc", 1890, 3, 160, 62),
    ]
    edges = [
        ("e1", "n1", "n2", ""),
        ("e2", "n2", "n3", ""),
        ("e3", "n3", "n5", "Yes", [(860, y_mid(3))]),
        ("e4", "n3", "n4", "No"),
        ("e5", "n4", "n2", "Recheck", [(1090, y_bottom(1)), (650, y_bottom(1))]),
        ("e6", "n5", "n6", "", [(1090, y_top(3)), (1310, y_top(3)), (1310, y_mid(1))]),
        ("e7", "n6", "n7", "", [(1310, y_mid(2))]),
        ("e8", "n7", "n8", "", [(1530, y_mid(4))]),
        ("e9", "n8", "n9", "", [(1750, y_bottom(4)), (1970, y_bottom(4)), (1970, y_mid(3))]),
    ]
    return build_page(
        "06 Quality + COA",
        "Quality + COA",
        "ลงรายละเอียด quality: ตรวจคุณภาพ, NCR/rework, ออก COA, approve COA และ release lot",
        lanes,
        nodes,
        edges,
    )


def planning_page():
    lanes = ["Sales", "Planning / MRP", "Purchase", "Manufacturing", "Inventory"]
    nodes = [
        ("n1", "Odoo Auto\nSO / Forecast", "auto", 330, 0, 160, 58),
        ("n2", "Odoo Auto\nMPS / MRP", "auto", 570, 1, 160, 58),
        ("n3", "User Manual\nReview Shortage", "user", 800, 1, 170, 58),
        ("n4", "Buy or Make?", "decision", 1030, 1, 120, 96),
        ("n5", "Odoo Auto\nRFQ / PO", "auto", 1240, 2, 150, 58),
        ("n6", "Odoo Auto\nMO Draft", "auto", 1240, 3, 150, 58),
        ("n7", "User Manual\nConfirm Plan", "approval", 1460, 1, 160, 58),
        ("n8", "Odoo Output\nIssue Slip", "doc", 1690, 4, 150, 62),
        ("n9", "Odoo Output\nWork Plan", "doc", 1900, 3, 150, 62),
    ]
    edges = [
        ("e1", "n1", "n2", ""),
        ("e2", "n2", "n3", ""),
        ("e3", "n3", "n4", ""),
        ("e4", "n4", "n5", "Yes / Buy", [(1090, y_mid(2))]),
        ("e5", "n4", "n6", "No / Make", [(1090, y_mid(3))]),
        ("e6", "n5", "n7", "", [(1320, y_top(2)), (1540, y_top(2)), (1540, y_mid(1))]),
        ("e7", "n6", "n7", "", [(1320, y_top(3)), (1540, y_top(3)), (1540, y_mid(1))]),
        ("e8", "n7", "n8", "", [(1540, y_mid(4))]),
        ("e9", "n8", "n9", "", [(1770, y_bottom(4)), (1980, y_bottom(4)), (1980, y_mid(3))]),
    ]
    return build_page(
        "07 Planning + IS WI MRP",
        "Planning + MRP / IS / WI",
        "ลงรายละเอียด planning: รวม SO/forecast เข้า MRP, review shortage, ตัดสินใจซื้อหรือผลิต และ confirm plan",
        lanes,
        nodes,
        edges,
    )


def production_page():
    lanes = ["Planning", "Production", "Quality", "Inventory", "Accounting"]
    nodes = [
        ("n1", "Odoo Auto\nMO Draft", "auto", 330, 0, 150, 58),
        ("n2", "User Manual\nConfirm MO", "approval", 560, 1, 150, 58),
        ("n3", "User Manual\nWork Order", "user", 780, 1, 150, 58),
        ("n4", "Odoo Auto\nConsume RM", "auto", 1000, 3, 150, 58),
        ("n5", "User Manual\nProduction Result", "user", 1220, 1, 170, 58),
        ("n6", "QC Pass?", "decision", 1450, 2, 120, 96),
        ("n7", "User Manual\nRework / Scrap", "user", 1660, 1, 160, 58),
        ("n8", "User Manual\nApprove FG", "approval", 1660, 2, 150, 58),
        ("n9", "Odoo Auto\nFG Receipt", "auto", 1880, 3, 150, 58),
        ("n10", "Odoo Auto\nWIP / Cost", "auto", 2100, 4, 150, 58),
    ]
    edges = [
        ("e1", "n1", "n2", "", [(410, y_mid(1))]),
        ("e2", "n2", "n3", ""),
        ("e3", "n3", "n4", "", [(860, y_mid(3))]),
        ("e4", "n4", "n5", "", [(1080, y_mid(1))]),
        ("e5", "n5", "n6", "", [(1300, y_mid(2))]),
        ("e6", "n6", "n8", "Yes"),
        ("e7", "n6", "n7", "No", [(1510, y_top(2)), (1740, y_top(2)), (1740, y_mid(1))]),
        ("e8", "n7", "n3", "Rework", [(1740, y_bottom(1)), (860, y_bottom(1))]),
        ("e9", "n8", "n9", "", [(1740, y_mid(3))]),
        ("e10", "n9", "n10", "", [(1960, y_mid(4))]),
    ]
    return build_page(
        "08 Production + MO WO Rework",
        "Production + MO / WO / Rework",
        "ลงรายละเอียดผลิต: confirm MO, work order, consume RM, บันทึกผลผลิต, QC, rework/scrap และรับ FG",
        lanes,
        nodes,
        edges,
    )


def delivery_page():
    lanes = ["Production", "FG Warehouse", "Sales", "Customer", "Accounting"]
    nodes = [
        ("n1", "Odoo Auto\nFG Available", "auto", 330, 0, 160, 58),
        ("n2", "Odoo Auto\nDelivery Order", "auto", 560, 2, 160, 58),
        ("n3", "User Manual\nPick / Pack", "user", 790, 1, 150, 58),
        ("n4", "Customer Accept?", "decision", 1010, 3, 120, 96),
        ("n5", "User Manual\nReturn / Hold", "user", 1220, 1, 160, 58),
        ("n6", "User Manual\nConfirm Delivery", "approval", 1220, 3, 170, 58),
        ("n7", "Odoo Output\nDelivery Slip", "doc", 1450, 2, 160, 62),
        ("n8", "Odoo Auto\nInvoice Trigger", "auto", 1670, 4, 160, 58),
        ("n9", "Odoo Output\nClose Delivery", "doc", 1890, 2, 160, 62),
    ]
    edges = [
        ("e1", "n1", "n2", "", [(410, y_mid(2))]),
        ("e2", "n2", "n3", "", [(640, y_mid(1))]),
        ("e3", "n3", "n4", "", [(860, y_mid(3))]),
        ("e4", "n4", "n6", "Yes"),
        ("e5", "n4", "n5", "No", [(1070, y_top(3)), (1300, y_top(3)), (1300, y_mid(1))]),
        ("e6", "n5", "n3", "Recheck", [(1300, y_bottom(1)), (860, y_bottom(1))]),
        ("e7", "n6", "n7", "", [(1300, y_mid(2))]),
        ("e8", "n7", "n8", "", [(1530, y_mid(4))]),
        ("e9", "n8", "n9", "", [(1750, y_bottom(4)), (1970, y_bottom(4)), (1970, y_mid(2))]),
    ]
    return build_page(
        "09 FG Warehouse + Delivery",
        "FG Warehouse + Delivery",
        "ลงรายละเอียดคลังสินค้าสำเร็จรูป: available FG, delivery order, pick/pack, confirm delivery และ trigger invoice",
        lanes,
        nodes,
        edges,
    )


def accounting_page():
    lanes = ["Source Docs", "Accounting", "Bank", "Tax", "Management Report", "Custom / Legacy"]
    nodes = [
        ("n1", "Odoo Auto\nCustomer Invoice", "doc", 330, 0, 165, 62),
        ("n2", "Odoo Auto\nVendor Bill", "doc", 570, 0, 165, 62),
        ("n3", "Odoo Auto\nJournal Entry", "auto", 800, 1, 160, 58),
        ("n4", "User Manual\nPayment / Receipt", "user", 800, 2, 165, 58),
        ("n5", "Odoo Auto\nTax / WHT", "auto", 1030, 3, 150, 58),
        ("n6", "Report OK?", "decision", 1250, 3, 120, 96),
        ("n7", "Odoo Output\nStd Report", "doc", 1460, 4, 150, 62),
        ("n8", "Custom\nLegacy Thai Forms", "custom", 1460, 5, 170, 58),
        ("n9", "User Manual\nApprove Close", "approval", 1700, 1, 160, 58),
        ("n10", "Odoo Output\nClose Period", "doc", 1920, 1, 150, 62),
    ]
    edges = [
        ("e1", "n1", "n3", "", [(410, y_mid(1))]),
        ("e2", "n2", "n3", "", [(650, y_bottom(0)), (880, y_bottom(0)), (880, y_mid(1))]),
        ("e3", "n3", "n4", "", [(650, y_mid(2))]),
        ("e4", "n4", "n5", "", [(880, y_mid(3))]),
        ("e5", "n5", "n6", ""),
        ("e6", "n6", "n7", "Yes", [(1310, y_mid(4))]),
        ("e7", "n6", "n8", "No", [(1310, y_mid(5))]),
        ("e8", "n7", "n9", "", [(1530, y_top(4)), (1780, y_top(4)), (1780, y_mid(1))]),
        ("e9", "n8", "n9", "", [(1540, y_bottom(5)), (1780, y_bottom(5)), (1780, y_mid(1))]),
        ("e10", "n9", "n10", ""),
    ]
    return build_page(
        "10 Accounting + Thai Tax Legacy Docs",
        "Accounting + Thai Tax / Legacy Docs",
        "ลงรายละเอียดบัญชี: invoice/bill, journal, payment, tax, standard report, legacy forms และ approve close period",
        lanes,
        nodes,
        edges,
    )


pages = [
    legend_page(),
    overall_page(),
    sales_page(),
    procurement_page(),
    rm_warehouse_page(),
    engineering_page(),
    quality_page(),
    planning_page(),
    production_page(),
    delivery_page(),
    accounting_page(),
]

mxfile = (
    '<mxfile host="app.diagrams.net" modified="2026-06-18T00:00:00.000Z" agent="Codex" version="24.7.17">'
    + "".join(pages)
    + "</mxfile>"
)

present_path.write_text(mxfile, encoding="utf-8")
package_path.write_text(mxfile, encoding="utf-8")
shutil.copyfile(present_path, download_path)
shutil.copyfile(present_path, detailed_download_path)
print(
    {
        "present": str(present_path),
        "package": str(package_path),
        "download": str(download_path),
        "detailed_download": str(detailed_download_path),
        "pages": len(pages),
    }
)
