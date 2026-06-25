from pathlib import Path
from xml.sax.saxutils import escape

present_path = Path(r"C:\365_project\TheCool18e\Dev\output\AMS_PRESENT_CUSTOMER_TH\04_Workflow_Business_Flow_AMS.drawio")
package_path = Path(r"C:\365_project\TheCool18e\Dev\output\ams_customer_r001_compare\AMS_R001_COMPARE_PACKAGE\06_AMS_R001_Blueprint_Swimlane_TH.drawio")

PAGE_W = 1900
PAGE_H = 980

styles = {
    "title": "rounded=1;whiteSpace=wrap;html=1;fillColor=#5B1747;fontColor=#FFFFFF;strokeColor=#5B1747;fontStyle=1;fontSize=22;align=center;verticalAlign=middle;fontFamily=Arial;",
    "note": "rounded=1;whiteSpace=wrap;html=1;fillColor=#F8FAFC;fontColor=#334155;strokeColor=#CBD5E1;fontSize=13;align=left;verticalAlign=middle;spacing=12;fontFamily=Arial;",
    "start": "rounded=1;arcSize=50;whiteSpace=wrap;html=1;fillColor=#E2E8F0;strokeColor=#334155;fontColor=#111827;fontStyle=1;fontSize=13;align=center;verticalAlign=middle;fontFamily=Arial;",
    "process": "rounded=1;whiteSpace=wrap;html=1;fillColor=#DCFCE7;strokeColor=#16A34A;fontColor=#14532D;fontSize=13;align=center;verticalAlign=middle;spacing=8;fontFamily=Arial;",
    "decision": "rhombus;whiteSpace=wrap;html=1;fillColor=#FCE4D6;strokeColor=#9A3412;fontColor=#7C2D12;fontStyle=1;fontSize=13;align=center;verticalAlign=middle;spacing=8;fontFamily=Arial;",
    "custom": "rounded=1;whiteSpace=wrap;html=1;fillColor=#FFF7ED;strokeColor=#F97316;fontColor=#7C2D12;fontSize=13;align=center;verticalAlign=middle;spacing=8;fontFamily=Arial;",
    "report": "rounded=1;whiteSpace=wrap;html=1;fillColor=#EDE9FE;strokeColor=#7C3AED;fontColor=#4C1D95;fontSize=13;align=center;verticalAlign=middle;spacing=8;fontFamily=Arial;",
    "module": "rounded=1;whiteSpace=wrap;html=1;fillColor=#EEF2FF;strokeColor=#A5B4FC;fontColor=#312E81;fontSize=12;align=left;verticalAlign=middle;spacing=10;fontFamily=Arial;",
    "doc": "shape=document;whiteSpace=wrap;html=1;boundedLbl=1;fillColor=#DBEAFE;strokeColor=#2563EB;fontColor=#1E3A8A;fontSize=13;align=center;verticalAlign=middle;spacing=8;fontFamily=Arial;",
    "edge": "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#334155;strokeWidth=1.35;endArrow=block;endFill=1;fontSize=12;fontColor=#111827;labelBackgroundColor=#FFFFFF;fontFamily=Arial;",
}


def mxcell(cell_id, value, style, x, y, w, h):
    return (
        f'<mxCell id="{cell_id}" value="{escape(value)}" style="{style}" vertex="1" parent="1">'
        f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry" />'
        "</mxCell>"
    )


def edge(edge_id, source, target, label="", points=None):
    geometry = '<mxGeometry relative="1" as="geometry">'
    if points:
        geometry += "<Array as=\"points\">"
        for x, y in points:
            geometry += f'<mxPoint x="{x}" y="{y}" />'
        geometry += "</Array>"
    geometry += "</mxGeometry>"
    return (
        f'<mxCell id="{edge_id}" value="{escape(label)}" style="{styles["edge"]}" edge="1" parent="1" source="{source}" target="{target}">'
        f"{geometry}</mxCell>"
    )


def page_xml(name, title, subtitle, module, nodes, edges):
    cells = ['<mxCell id="0" />', '<mxCell id="1" parent="0" />']
    cells.append(mxcell("title", title, styles["title"], 50, 30, 1780, 58))
    cells.append(mxcell("subtitle", subtitle, styles["note"], 50, 100, 1180, 54))
    cells.append(mxcell("module", f"Module: {module}", styles["module"], 1250, 100, 580, 54))
    for node in nodes:
        node_id, value, kind, x, y, w, h = node
        cells.append(mxcell(node_id, value, styles[kind], x, y, w, h))
    for item in edges:
        cells.append(edge(*item))
    graph = (
        f'<mxGraphModel dx="1800" dy="1000" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" '
        f'fold="1" page="1" pageScale="1" pageWidth="{PAGE_W}" pageHeight="{PAGE_H}" math="0" shadow="0">'
        "<root>"
        + "".join(cells)
        + "</root></mxGraphModel>"
    )
    return f'<diagram id="{escape(name)}" name="{escape(name)}">{graph}</diagram>'


def simple_page(name, title, module, start, p1, decision, yes, no, next_step, end):
    nodes = [
        ("n1", start, "start", 80, 420, 170, 62),
        ("n2", p1, "process", 310, 420, 190, 62),
        ("n3", decision, "decision", 570, 400, 150, 105),
        ("n4", yes, "process", 800, 250, 200, 62),
        ("n5", no, "custom", 800, 560, 200, 62),
        ("n6", next_step, "process", 1080, 420, 210, 62),
        ("n7", end, "doc", 1360, 420, 210, 62),
    ]
    edges = [
        ("e1", "n1", "n2", ""),
        ("e2", "n2", "n3", ""),
        ("e3", "n3", "n4", "Yes", [(645, 260)]),
        ("e4", "n3", "n5", "No", [(645, 590)]),
        ("e5", "n4", "n6", "", [(1090, 280)]),
        ("e6", "n5", "n6", "", [(1090, 590)]),
        ("e7", "n6", "n7", ""),
    ]
    subtitle = "อ่านซ้ายไปขวา: เริ่มงาน → ทำงานหลัก → ตัดสินใจ Yes/No → ไปต่อ"
    return page_xml(name, title, subtitle, module, nodes, edges)


def legend_page():
    nodes = [
        ("s1", "Start / End", "start", 90, 240, 180, 60),
        ("p1", "Process", "process", 340, 240, 180, 60),
        ("d1", "Decision?", "decision", 590, 220, 140, 100),
        ("y1", "Yes path", "process", 820, 160, 180, 60),
        ("n1", "No path", "custom", 820, 340, 180, 60),
        ("r1", "Document / Output", "doc", 1080, 240, 210, 70),
        ("m1", "Module: ใช้บอกว่าอยู่ใน Odoo app ไหน", "module", 90, 470, 540, 70),
        ("c1", "สีส้ม = ต้องทำเพิ่ม / Report / Custom", "custom", 700, 470, 430, 70),
        ("rep1", "สีม่วง = Report / KPI", "report", 1200, 470, 300, 70),
    ]
    edges = [
        ("e1", "s1", "p1", ""),
        ("e2", "p1", "d1", ""),
        ("e3", "d1", "y1", "Yes", [(660, 170)]),
        ("e4", "d1", "n1", "No", [(660, 370)]),
        ("e5", "y1", "r1", ""),
        ("e6", "n1", "r1", ""),
    ]
    return page_xml(
        "00 วิธีอ่าน R001 Blueprint Flow",
        "วิธีอ่าน Workflow",
        "ทุก Decision ต้องมี Yes/No และเส้นแยกชัดเจน ไม่ซ้อนกัน",
        "ทุก Module",
        nodes,
        edges,
    )


def overall_page():
    nodes = [
        ("n1", "RFQ / Forecast", "start", 70, 420, 165, 62),
        ("n2", "Quotation / SO", "process", 285, 420, 170, 62),
        ("n3", "Product + BOM", "process", 505, 420, 170, 62),
        ("n4", "MRP Plan", "process", 725, 420, 165, 62),
        ("n5", "Buy?", "decision", 945, 400, 140, 105),
        ("n6", "PR / PO", "process", 1160, 250, 170, 62),
        ("n7", "MO / Work Order", "process", 1160, 560, 170, 62),
        ("n8", "QC?", "decision", 1400, 400, 140, 105),
        ("n9", "COA + Delivery", "doc", 1600, 270, 190, 70),
        ("n10", "Rework / Hold", "custom", 1600, 540, 190, 70),
        ("n11", "Invoice + Payment", "doc", 1600, 420, 190, 70),
    ]
    edges = [
        ("e1", "n1", "n2", ""),
        ("e2", "n2", "n3", ""),
        ("e3", "n3", "n4", ""),
        ("e4", "n4", "n5", ""),
        ("e5", "n5", "n6", "Yes / Buy", [(1015, 280)]),
        ("e6", "n5", "n7", "No / Make", [(1015, 590)]),
        ("e7", "n6", "n8", "", [(1380, 280)]),
        ("e8", "n7", "n8", "", [(1380, 590)]),
        ("e9", "n8", "n9", "Yes / Pass", [(1470, 300)]),
        ("e10", "n8", "n10", "No / Fail", [(1470, 570)]),
        ("e11", "n9", "n11", ""),
    ]
    return page_xml(
        "01 Overall R001 Blueprint End-to-End",
        "Overall End-to-End Flow",
        "ภาพรวมตั้งแต่ลูกค้าส่ง demand จนถึงส่งของและออก invoice",
        "Sales, Purchase, Inventory, Manufacturing, Quality, Accounting",
        nodes,
        edges,
    )


pages = [
    legend_page(),
    overall_page(),
    simple_page("02 Sales + Customer Forecast API", "Sales + Customer Forecast", "Sales, CRM, Invoicing, MRP/MPS", "RFQ / Forecast", "Quotation", "New item?", "Create IMR / Product", "Use existing item", "SO + Customer PO", "Demand to MRP"),
    simple_page("03 Procurement + PR PO Approval", "Procurement + PR/PO", "Purchase, Approvals, Inventory", "Shortage / PR", "RFQ", "Need approval?", "Approval", "Direct RFQ", "PO / Blanket", "Vendor delivery"),
    simple_page("04 RM Warehouse + Customer Supplied Material", "RM Warehouse", "Inventory, Barcode, Purchase", "Receive RM", "Lot / Shelf", "Customer owner?", "Owner stock", "Company stock", "Issue RM", "To production"),
    simple_page("05 Engineering + PCC BOM Routing", "Engineering + PCC", "Manufacturing, PLM, Inventory", "New product", "Product master", "Need PCC?", "PCC form", "Use BOM", "BOM / Routing", "Ready for MRP"),
    simple_page("06 Quality + COA", "Quality + COA", "Quality, Manufacturing, Inventory", "Inspection", "Quality check", "Pass?", "COA", "NCR / Rework", "Quality result", "Release / Hold"),
    simple_page("07 Planning + IS WI MRP", "Planning + MRP", "Manufacturing, MPS/MRP, Inventory", "SO / Forecast", "MPS / MRP", "Buy?", "RFQ / PO", "MO / Issue", "Plan confirm", "Execute"),
    simple_page("08 Production + MO WO Rework", "Production + Work Order", "Manufacturing, Shop Floor, Quality", "MO", "Work order", "QC pass?", "FG / WIP", "Rework / Scrap", "Cost / WIP", "FG done"),
    simple_page("09 FG Warehouse + Delivery", "FG Warehouse + Delivery", "Inventory, Barcode, Sales, Fleet", "FG receipt", "Pick / Pack", "Customer accepts?", "Delivery done", "Return / Rework", "Invoice trigger", "Close delivery"),
    simple_page("10 Accounting + Thai Tax Legacy Docs", "Accounting + Thai Tax", "Accounting, Thai Localization, Spreadsheet", "Invoice / Bill", "Payment / Bank", "Standard enough?", "Standard reports", "Custom report", "Tax / QR / BI", "Close period"),
]

mxfile = (
    '<mxfile host="app.diagrams.net" modified="2026-06-18T00:00:00.000Z" agent="Codex" version="24.7.17">'
    + "".join(pages)
    + "</mxfile>"
)

present_path.write_text(mxfile, encoding="utf-8")
package_path.write_text(mxfile, encoding="utf-8")
print({"present": str(present_path), "package": str(package_path), "pages": len(pages)})
