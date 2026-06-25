from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape


PACKAGE = Path(r"C:\365_project\TheCool18e\Dev\output\ams_customer_r001_compare\AMS_R001_COMPARE_PACKAGE")
TARGET = PACKAGE / "06_AMS_R001_Blueprint_Swimlane_TH.drawio"
INDEX = PACKAGE / "deliverables_index.json"


PALETTE = {
    "start": "#D9EAD3",
    "process": "#DAE8FC",
    "decision": "#F4CCCC",
    "io": "#D0E0E3",
    "document": "#FFF2CC",
    "database": "#EADCF8",
    "connector": "#F8CBAD",
    "custom": "#FCE4D6",
    "report": "#E2F0D9",
    "lane": "#F8FAFC",
    "header": "#5B1747",
    "line": "#334155",
    "note": "#FFF2CC",
}


class Diagram:
    def __init__(self, name: str, width: int = 3300, height: int = 1880):
        self.name = name
        self.width = width
        self.height = height
        self.cells: list[str] = ['<mxCell id="0"/>', '<mxCell id="1" parent="0"/>']
        self.next_id = 2

    def _id(self) -> str:
        value = str(self.next_id)
        self.next_id += 1
        return value

    def cell(self, label: str, x: int, y: int, w: int, h: int, style: str) -> str:
        cid = self._id()
        self.cells.append(
            f'<mxCell id="{cid}" value="{escape(label)}" style="{style}" vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/>'
            f"</mxCell>"
        )
        return cid

    def title(self, title: str, subtitle: str = "") -> None:
        self.cell(
            title,
            44,
            26,
            self.width - 88,
            46,
            f"text;html=1;strokeColor=none;fillColor=none;fontSize=28;fontStyle=1;fontColor={PALETTE['header']};align=left;verticalAlign=middle;fontFamily=Arial;",
        )
        if subtitle:
            self.cell(
                subtitle,
                44,
                76,
                self.width - 88,
                36,
                "text;html=1;strokeColor=none;fillColor=none;fontSize=14;fontColor=#475569;align=left;verticalAlign=middle;fontFamily=Arial;",
            )

    def lanes(self, names: list[str], top: int = 132, lane_h: int = 190) -> dict[str, int]:
        result: dict[str, int] = {}
        for i, name in enumerate(names):
            y = top + i * lane_h
            result[name] = y
            self.cell(
                name,
                44,
                y,
                self.width - 88,
                lane_h,
                f"swimlane;html=1;horizontal=0;startSize=46;fillColor={PALETTE['lane']};strokeColor=#CBD5E1;fontColor=#111827;fontStyle=1;fontSize=13;fontFamily=Arial;",
            )
        return result

    def node(self, kind: str, label: str, x: int, y: int, w: int = 250, h: int = 86) -> str:
        fill = PALETTE.get(kind, PALETTE["process"])
        common = f"whiteSpace=wrap;html=1;fillColor={fill};strokeColor=#334155;fontColor=#111827;spacing=10;fontSize=12;fontFamily=Arial;"
        if kind == "start":
            style = f"rounded=1;arcSize=50;{common}"
        elif kind == "decision":
            style = f"rhombus;{common}"
        elif kind == "io":
            style = f"shape=parallelogram;perimeter=parallelogramPerimeter;{common}"
        elif kind == "document":
            style = f"shape=document;boundedLbl=1;{common}"
        elif kind == "database":
            style = f"shape=cylinder;boundedLbl=1;backgroundOutline=1;size=15;{common}"
        elif kind == "connector":
            style = f"ellipse;{common}"
        elif kind == "custom":
            style = f"rounded=0;{common}"
        elif kind == "report":
            style = f"rounded=0;{common}"
        else:
            style = f"rounded=0;{common}"
        return self.cell(label, x, y, w, h, style)

    def note(self, label: str, x: int, y: int, w: int = 660, h: int = 90) -> str:
        return self.cell(
            label,
            x,
            y,
            w,
            h,
            f"shape=note;whiteSpace=wrap;html=1;backgroundOutline=1;darkOpacity=0.05;fillColor={PALETTE['note']};strokeColor=#D6B656;fontColor=#111827;fontSize=12;fontFamily=Arial;spacing=10;",
        )

    def edge(self, src: str, dst: str, label: str = "") -> None:
        cid = self._id()
        self.cells.append(
            f'<mxCell id="{cid}" value="{escape(label)}" '
            f'style="edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;strokeColor={PALETTE["line"]};strokeWidth=1.35;endArrow=block;endFill=1;fontSize=12;fontColor=#111827;labelBackgroundColor=#FFFFFF;fontFamily=Arial;" '
            f'edge="1" parent="1" source="{src}" target="{dst}"><mxGeometry relative="1" as="geometry"/></mxCell>'
        )

    def xml(self) -> str:
        return (
            f'<mxGraphModel dx="{self.width}" dy="{self.height}" grid="1" gridSize="10" guides="1" tooltips="1" '
            f'connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{self.width}" pageHeight="{self.height}" '
            f'math="0" shadow="0"><root>{"".join(self.cells)}</root></mxGraphModel>'
        )


def row_y(lanes: dict[str, int], lane: str, offset: int = 52) -> int:
    return lanes[lane] + offset


def legend_page() -> Diagram:
    d = Diagram("00 วิธีอ่าน R001 Blueprint Flow", 1800, 1120)
    d.title("วิธีอ่าน R001 Blueprint Flow", "ใช้หน้านี้เปิดก่อน present เพื่อให้ทุกคนอ่านสัญลักษณ์และสีเหมือนกัน")
    items = [
        ("start", "Start / End\nจุดเริ่มต้นหรือจบ flow", 90, 160),
        ("process", "Process\nงานที่ User หรือ Odoo ทำ", 430, 160),
        ("decision", "Decision\nจุดตัดสินใจ Yes/No", 780, 146),
        ("document", "Document\nเอกสาร เช่น SO, PO, MO, COA", 1130, 160),
        ("database", "Database\nMaster/Transaction Data", 90, 450),
        ("io", "Input / Output\nข้อมูลเข้า/ข้อมูลออก", 430, 450),
        ("custom", "Custom / Integration\nจุดที่ต้องเพิ่มจาก Standard", 780, 450),
        ("report", "Report / KPI\nDashboard, COA, DPPM, OEE/OPE", 1130, 450),
    ]
    for kind, label, x, y in items:
        d.node(kind, label, x, y, 260, 110)
    a = d.node("start", "ตัวอย่าง: Customer RFQ", 220, 775, 230, 82)
    b = d.node("process", "Odoo สร้าง Quotation", 560, 775, 250, 82)
    c = d.node("decision", "ต้อง Custom?", 920, 756, 180, 120)
    e = d.node("custom", "ทำ Import/API หรือ Report เพิ่ม", 1240, 775, 300, 82)
    d.edge(a, b)
    d.edge(b, c)
    d.edge(c, e, "Yes")
    d.note(
        "หลักการ present: อ่านซ้ายไปขวา, อ่านตาม Swimlane เพื่อหา owner, ทุกกล่องสีส้มต้องถามว่าเป็น Standard config, Report, Integration หรือ Custom จริง",
        160,
        930,
        1420,
        90,
    )
    return d


def overall_page() -> Diagram:
    lanes_names = [
        "Sales / Customer",
        "Procurement",
        "RM Warehouse",
        "Engineering / PCC",
        "Quality / COA",
        "Planning / MRP",
        "Production",
        "FG Warehouse / Delivery",
        "Accounting / Finance",
    ]
    d = Diagram("01 Overall R001 Blueprint End-to-End", 3500, 1910)
    d.title("Overall R001 Blueprint End-to-End", "ภาพรวมจาก Customer RFQ/Forecast จนถึง Delivery, Invoice, Payment และ Thai Tax")
    lanes = d.lanes(lanes_names, lane_h=190)
    n1 = d.node("start", "Start\nCustomer RFQ / PO / Forecast", 210, row_y(lanes, "Sales / Customer"))
    n2 = d.node("io", "FA / Customer Forecast\nAutomotive file/API?", 520, row_y(lanes, "Sales / Customer"))
    n3 = d.node("document", "Quotation / SO\nCustomer PO Ref", 860, row_y(lanes, "Sales / Customer"))
    n4 = d.node("decision", "New product?", 1180, row_y(lanes, "Sales / Customer") - 18, 180, 120)
    n5 = d.node("document", "IMR / Product Code\nMaster setup", 1460, row_y(lanes, "Engineering / PCC"))
    n6 = d.node("process", "PCC\nBOM / Routing / Work Centers", 1800, row_y(lanes, "Engineering / PCC"), 290)
    n7 = d.node("process", "MPS / MRP Run\nSO + Forecast + Stock", 2140, row_y(lanes, "Planning / MRP"), 300)
    n8 = d.node("decision", "Buy / Make?", 2480, row_y(lanes, "Planning / MRP") - 18, 180, 120)
    n9 = d.node("document", "PR / RFQ / PO\nBlanket + Approval", 2760, row_y(lanes, "Procurement"), 280)
    n10 = d.node("process", "Receive RM / CP\nPrint Tag + Lot/Shelf", 2760, row_y(lanes, "RM Warehouse"), 300)
    n11 = d.node("document", "MO / Work Orders\nIS / WI material issue", 2760, row_y(lanes, "Production"), 300)
    n12 = d.node("decision", "QC Pass?", 3100, row_y(lanes, "Quality / COA") - 18, 180, 120)
    n13 = d.node("report", "COA / DPPM\nQuality output", 3100, row_y(lanes, "Quality / COA") + 104, 260, 82)
    n14 = d.node("process", "PI FG Receipt\nPick / Pack / Ship", 3100, row_y(lanes, "FG Warehouse / Delivery"), 260)
    n15 = d.node("document", "Invoice / BI / Payment\nPD/RR/PS/RE + Thai Tax", 3100, row_y(lanes, "Accounting / Finance"), 300)
    n16 = d.node("custom", "Custom / Integration Scope\nForecast API, COA format, Netting, Multi Ledger, legacy doc sequence", 700, row_y(lanes, "Accounting / Finance"), 740, 92)
    for a, b, label in [
        (n1, n2, ""),
        (n2, n3, ""),
        (n3, n4, ""),
        (n4, n5, "Yes"),
        (n5, n6, ""),
        (n4, n7, "No / Existing product"),
        (n6, n7, "Released master"),
        (n7, n8, ""),
        (n8, n9, "Buy"),
        (n9, n10, "Vendor ships"),
        (n10, n11, "RM ready"),
        (n8, n11, "Make"),
        (n11, n12, "Operation check"),
        (n12, n13, "Pass"),
        (n13, n14, "Release"),
        (n14, n15, "Delivered"),
        (n16, n15, "Finance gaps"),
    ]:
        d.edge(a, b, label)
    d.note("จุดสำคัญ: Flow นี้ไม่แทน flow baseline เดิม แต่เพิ่ม detail จาก R001/blueprint เช่น legacy document code, customer supplied material, COA, IS/WI, Thai Tax และ integration/API", 180, 1745, 1460, 90)
    return d


def sales_page() -> Diagram:
    lane_names = ["Customer", "Sales / CRM", "Engineering / Product Master", "Planning / MRP", "Accounting"]
    d = Diagram("02 Sales + Customer Forecast API", 3100, 1260)
    d.title("Sales + Customer Forecast / API", "Map SP, FA, IMR, SO, IV, BI เข้ากับ Odoo Sales/CRM/MRP/Accounting")
    lanes = d.lanes(lane_names, lane_h=205)
    n1 = d.node("start", "Start\nCustomer Inquiry / RFQ", 210, row_y(lanes, "Customer"))
    n2 = d.node("io", "FA / Forecast / Customer PO\nAutomotive source", 520, row_y(lanes, "Customer"), 300)
    n3 = d.node("process", "CRM Lead / Opportunity\nCustomer profile", 880, row_y(lanes, "Sales / CRM"), 300)
    n4 = d.node("decision", "New item / SP?", 1240, row_y(lanes, "Sales / CRM") - 18, 180, 120)
    n5 = d.node("document", "IMR\nขอรหัสสินค้า / Product Master", 1510, row_y(lanes, "Engineering / Product Master"), 310)
    n6 = d.node("process", "BOM cost / PPAP\nQuotation costing", 1870, row_y(lanes, "Engineering / Product Master"), 310)
    n7 = d.node("document", "Quotation / SO\nCustomer PO Ref", 2230, row_y(lanes, "Sales / CRM"), 290)
    n8 = d.node("process", "Send Demand to MPS/MRP\nSO + Forecast", 2570, row_y(lanes, "Planning / MRP"), 300)
    n9 = d.node("document", "IV / BI\nInvoice / Billing Statement", 2570, row_y(lanes, "Accounting"), 300)
    n10 = d.node("custom", "Custom candidate\nCustomer Forecast/API import, BI form, Quotation BOM/PPAP template", 1250, row_y(lanes, "Accounting"), 760, 92)
    for a, b, label in [(n1, n2, ""), (n2, n3, ""), (n3, n4, ""), (n4, n5, "Yes"), (n5, n6, ""), (n4, n7, "No"), (n6, n7, ""), (n7, n8, "Won"), (n8, n9, "After delivery"), (n10, n9, "Form/report")]:
        d.edge(a, b, label)
    d.note("Standard: CRM, Sales Order, pricelist, margin, MPS/MRP demand. เพิ่มที่ต้องถาม: format forecast/API, BI format, quotation costing/PPAP.", 150, 1120, 1380)
    return d


def procurement_page() -> Diagram:
    lane_names = ["Requester / MRP", "Purchasing", "Approver / Budget", "Vendor", "RM Warehouse", "Accounting"]
    d = Diagram("03 Procurement + PR PO Approval", 3300, 1430)
    d.title("Procurement + PR/PO Approval", "Map PR, RFQ, PO, Blanket, Supplier Evaluation, 3-way match")
    lanes = d.lanes(lane_names, lane_h=200)
    n1 = d.node("start", "Start\nMRP shortage / Manual PR", 210, row_y(lanes, "Requester / MRP"))
    n2 = d.node("decision", "Budget / Approval required?", 560, row_y(lanes, "Approver / Budget") - 18, 210, 125)
    n3 = d.node("process", "Approval Request\nBudget / policy check", 900, row_y(lanes, "Approver / Budget"), 300)
    n4 = d.node("document", "RFQ\npurchase.order draft", 1260, row_y(lanes, "Purchasing"))
    n5 = d.node("io", "Vendor Quotation\nPrice / lead time / MOQ", 1580, row_y(lanes, "Vendor"), 300)
    n6 = d.node("decision", "Best supplier?", 1940, row_y(lanes, "Purchasing") - 18, 180, 120)
    n7 = d.node("document", "PO / Blanket Agreement\nContract framework", 2230, row_y(lanes, "Purchasing"), 310)
    n8 = d.node("process", "Vendor ships\nReceive RM", 2580, row_y(lanes, "RM Warehouse"), 280)
    n9 = d.node("document", "Vendor Bill\n3-way match", 2920, row_y(lanes, "Accounting"), 250)
    n10 = d.node("custom", "Custom candidate\nWeighted supplier score, approval suggestion, over-budget hard lock", 1180, row_y(lanes, "Accounting"), 800, 92)
    for a, b, label in [(n1, n2, ""), (n2, n3, "Yes"), (n2, n4, "No"), (n3, n4, "Approved"), (n4, n5, ""), (n5, n6, ""), (n6, n7, "Yes"), (n7, n8, ""), (n8, n9, ""), (n10, n7, "Guard/KPI")]:
        d.edge(a, b, label)
    d.note("Standard: Purchase, Purchase Agreement, Approvals, Receipt, Vendor Bill. Custom เฉพาะ supplier score/auto suggestion/hard lock ที่ standard ไม่ทำครบ.", 150, 1280, 1500)
    return d


def rm_warehouse_page() -> Diagram:
    lane_names = ["Vendor / Customer", "RM Warehouse", "Barcode Device", "Production", "Accounting / Stock Valuation", "Management"]
    d = Diagram("04 RM Warehouse + Customer Supplied Material", 3300, 1430)
    d.title("RM Warehouse + Customer Supplied Material", "Map รับ RM, CP, Tag, Lot/Shelf, Issue Material (IS)")
    lanes = d.lanes(lane_names, lane_h=200)
    n1 = d.node("start", "Start\nVendor RM / Customer CP material", 210, row_y(lanes, "Vendor / Customer"), 300)
    n2 = d.node("document", "Receipt\nรับวัตถุดิบ / รับวัตถุดิบลูกค้า", 570, row_y(lanes, "RM Warehouse"), 320)
    n3 = d.node("decision", "Customer owner / Lot required?", 960, row_y(lanes, "RM Warehouse") - 18, 210, 125)
    n4 = d.node("database", "Stock Lot / Owner / Quant\nShelf + QC hold + WIP", 1320, row_y(lanes, "RM Warehouse"), 320)
    n5 = d.node("process", "Print Tag / Barcode Scan\nรับเข้า / ย้าย / จ่าย", 1710, row_y(lanes, "Barcode Device"), 320)
    n6 = d.node("document", "IS\nIssue RM to Production", 2100, row_y(lanes, "Production"), 300)
    n7 = d.node("database", "Stock Valuation\nFIFO / AVCO / Owner stock rule", 2470, row_y(lanes, "Accounting / Stock Valuation"), 330)
    n8 = d.node("report", "Slow / Dead stock\nRM aging / turnover", 2870, row_y(lanes, "Management"), 270)
    n9 = d.node("custom", "Custom/Design point\nCustomer supplied material valuation/off-balance and CP report ต้องยืนยันกับ Finance", 960, row_y(lanes, "Accounting / Stock Valuation"), 900, 90)
    for a, b, label in [(n1, n2, ""), (n2, n3, ""), (n3, n4, "Yes / capture"), (n3, n5, "No / standard"), (n4, n5, ""), (n5, n6, ""), (n6, n7, "stock move"), (n7, n8, "report"), (n9, n7, "accounting rule")]:
        d.edge(a, b, label)
    d.note("Standard: Inventory, Lots/Serial, Locations, Owner stock, Barcode. ต้อง design เพิ่มเมื่อ material เป็นของลูกค้าและไม่ต้องการ valuation แบบสินค้าบริษัท.", 150, 1280, 1500)
    return d


def engineering_page() -> Diagram:
    lane_names = ["Sales / IMR", "Engineering", "Production Engineering", "Quality", "Planning / MRP", "Master Data"]
    d = Diagram("05 Engineering + PCC BOM Routing", 3300, 1430)
    d.title("Engineering + PCC / BOM / Routing", "Map IMR, Product Master, PCC, BOM, Routing, Work Centers, Revision")
    lanes = d.lanes(lane_names, lane_h=200)
    n1 = d.node("start", "Start\nIMR ขอรหัสสินค้า / New product", 210, row_y(lanes, "Sales / IMR"), 300)
    n2 = d.node("database", "Product Master\nUoM / MOQ / Route / Lead time", 590, row_y(lanes, "Master Data"), 330)
    n3 = d.node("process", "PCC\nกำหนดขั้นตอนการผลิต", 990, row_y(lanes, "Production Engineering"), 310)
    n4 = d.node("database", "BOM / Routing\nMulti-layer + Revision", 1370, row_y(lanes, "Engineering"), 320)
    n5 = d.node("database", "Work Centers\nCapacity / cost / operation", 1760, row_y(lanes, "Production Engineering"), 320)
    n6 = d.node("process", "Quality Specification\nQuality Point template", 2140, row_y(lanes, "Quality"), 320)
    n7 = d.node("document", "Release to MRP\nพร้อมใช้ใน SO/MO", 2530, row_y(lanes, "Planning / MRP"), 300)
    n8 = d.node("custom", "Custom/Report candidate\nPCC form, PPAP/quotation BOM version, approval/revision control", 980, row_y(lanes, "Master Data"), 920, 92)
    for a, b, label in [(n1, n2, ""), (n2, n3, ""), (n3, n4, ""), (n4, n5, ""), (n5, n6, ""), (n6, n7, ""), (n8, n4, "revision/form")]:
        d.edge(a, b, label)
    d.note("Standard: Product, BOM, Routing/Operations, Work Centers, PLM/ECO. เพิ่มที่ต้องคุย: PCC document format, PPAP, quotation BOM และ revision approval.", 150, 1280, 1500)
    return d


def qc_page() -> Diagram:
    lane_names = ["Production / Warehouse", "Quality", "Customer", "Accounting / Cost", "Management"]
    d = Diagram("06 Quality + COA", 3100, 1260)
    d.title("Quality + COA", "Map ตรวจตามข้อกำหนด, QC Pass/Fail, COA, DPPM")
    lanes = d.lanes(lane_names, lane_h=205)
    n1 = d.node("start", "Start\nOperation / Receipt / Delivery QC", 210, row_y(lanes, "Production / Warehouse"), 310)
    n2 = d.node("process", "Quality Check\nตาม Quality Point", 580, row_y(lanes, "Quality"), 300)
    n3 = d.node("decision", "Pass?", 950, row_y(lanes, "Quality") - 18, 180, 120)
    n4 = d.node("report", "COA\nCertificate of Analysis", 1240, row_y(lanes, "Customer"), 300)
    n5 = d.node("process", "Release Stock\nส่ง FG / Delivery", 1590, row_y(lanes, "Production / Warehouse"), 300)
    n6 = d.node("custom", "Fail path\nNCR / Rework / Scrap / Quality Alert", 1240, row_y(lanes, "Quality") + 116, 330, 88)
    n7 = d.node("database", "Cost impact\nScrap / Rework / WIP", 1940, row_y(lanes, "Accounting / Cost"), 300)
    n8 = d.node("report", "DPPM / Customer Return\nQuality KPI", 2290, row_y(lanes, "Management"), 310)
    n9 = d.node("custom", "Custom candidate\nCOA PDF by customer/spec + DPPM formula/dashboard", 630, row_y(lanes, "Management"), 780, 88)
    for a, b, label in [(n1, n2, ""), (n2, n3, ""), (n3, n4, "Pass"), (n4, n5, ""), (n3, n6, "Fail"), (n6, n7, "cost"), (n5, n8, "quality data"), (n9, n4, "report format")]:
        d.edge(a, b, label)
    d.note("Standard: Quality Point/Check/Alert. Custom มักอยู่ที่ COA format และสูตร DPPM/RMA ที่ลูกค้าต้องการ.", 150, 1120, 1320)
    return d


def planning_page() -> Diagram:
    lane_names = ["Sales Forecast", "Planning / MRP", "Procurement", "Warehouse", "Production", "Management"]
    d = Diagram("07 Planning + IS WI MRP", 3300, 1430)
    d.title("Planning + IS / WI / MRP", "Map MPS/MRP, Buy/Make, IS material issue, WI semi-finished/work instruction")
    lanes = d.lanes(lane_names, lane_h=200)
    n1 = d.node("start", "Start\nSO / FA Forecast / Customer PO", 210, row_y(lanes, "Sales Forecast"), 310)
    n2 = d.node("custom", "Forecast Import/API\nAutomotive rolling forecast", 570, row_y(lanes, "Sales Forecast"), 320)
    n3 = d.node("process", "MPS / MRP Run\nDemand vs Supply", 960, row_y(lanes, "Planning / MRP"), 300)
    n4 = d.node("decision", "Buy / Make / Stock?", 1320, row_y(lanes, "Planning / MRP") - 18, 210, 125)
    n5 = d.node("document", "RFQ / PO\nBuy route", 1680, row_y(lanes, "Procurement"), 280)
    n6 = d.node("document", "IS\nIssue material from RM", 1680, row_y(lanes, "Warehouse"), 300)
    n7 = d.node("document", "WI\nSemi-finished / Work Instruction", 2050, row_y(lanes, "Production"), 330)
    n8 = d.node("process", "Schedule Machine\nWork center load", 2430, row_y(lanes, "Production"), 300)
    n9 = d.node("report", "Planning KPI\nForecast vs Invoice / Delivery", 2800, row_y(lanes, "Management"), 310)
    for a, b, label in [(n1, n2, "if file/API"), (n2, n3, ""), (n1, n3, "manual"), (n3, n4, ""), (n4, n5, "Buy"), (n4, n6, "Make"), (n6, n7, ""), (n7, n8, ""), (n8, n9, "")]:
        d.edge(a, b, label)
    d.note("Standard: MPS/MRP, routes, reorder rules, MO creation. เพิ่มที่ต้องถาม: format forecast/API, IS/WI legacy form, forecast accuracy KPI.", 150, 1280, 1500)
    return d


def production_page() -> Diagram:
    lane_names = ["Planning", "Production", "Barcode Device", "Quality", "Warehouse / WIP FG", "Costing / Maintenance"]
    d = Diagram("08 Production + MO WO Rework", 3300, 1430)
    d.title("Production + MO / WO / Rework", "Map MO, Work Orders, input/output/waste/time, rework/scrap, OEE/OPE")
    lanes = d.lanes(lane_names, lane_h=200)
    n1 = d.node("start", "Start\nMO from MRP / Sales demand", 210, row_y(lanes, "Planning"), 300)
    n2 = d.node("document", "Manufacturing Order\nBOM + Routing", 570, row_y(lanes, "Production"), 300)
    n3 = d.node("process", "Work Orders\nSLIT / LAMINATE / PUNCH / CUT", 930, row_y(lanes, "Production"), 340)
    n4 = d.node("process", "Barcode Input\nStart/Finish, Qty, Waste, Time", 1340, row_y(lanes, "Barcode Device"), 340)
    n5 = d.node("decision", "QC pass at operation?", 1740, row_y(lanes, "Quality") - 18, 220, 125)
    n6 = d.node("custom", "Rework / Scrap\nQuality Alert", 2070, row_y(lanes, "Quality"), 300)
    n7 = d.node("database", "WIP / FG Stock\nstock.move + valuation", 2070, row_y(lanes, "Warehouse / WIP FG"), 330)
    n8 = d.node("report", "OEE / OPE\nAvailability, Performance, Quality", 2470, row_y(lanes, "Costing / Maintenance"), 340)
    n9 = d.node("custom", "Custom candidate\nOEE/OPE formula, cost variance allocation, WIP by process without location", 980, row_y(lanes, "Costing / Maintenance"), 980, 90)
    for a, b, label in [(n1, n2, ""), (n2, n3, ""), (n3, n4, ""), (n4, n5, ""), (n5, n7, "Pass"), (n5, n6, "Fail"), (n6, n3, "Rework"), (n7, n8, "production data"), (n9, n8, "KPI/cost")]:
        d.edge(a, b, label)
    d.note("Standard: MRP, Work Orders, Barcode MRP, Quality, Maintenance. Custom ควรจำกัดเฉพาะสูตร KPI/variance/WIP ที่ standard ไม่ตอบโจทย์.", 150, 1280, 1500)
    return d


def fg_delivery_page() -> Diagram:
    lane_names = ["Production", "FG Warehouse", "Sales", "Logistics / Fleet", "Customer", "Accounting"]
    d = Diagram("09 FG Warehouse + Delivery", 3300, 1430)
    d.title("Finished Goods Warehouse + Delivery", "Map PI รับเข้าสินค้าสำเร็จรูป, จัดส่งตาม SO, route/cost/fleet")
    lanes = d.lanes(lane_names, lane_h=200)
    n1 = d.node("start", "Start\nProduction done / FG ready", 210, row_y(lanes, "Production"), 300)
    n2 = d.node("document", "PI\nรับสินค้าเข้าคลัง FG", 580, row_y(lanes, "FG Warehouse"), 280)
    n3 = d.node("database", "FG Lot / Location\nAvailable stock", 930, row_y(lanes, "FG Warehouse"), 300)
    n4 = d.node("document", "SO Delivery Demand\nจัดส่งตาม SO", 1290, row_y(lanes, "Sales"), 300)
    n5 = d.node("process", "Pick / Pack / Ship\nDelivery Order", 1660, row_y(lanes, "FG Warehouse"), 310)
    n6 = d.node("process", "Delivery Method / Route\nTransport cost + Fleet", 2040, row_y(lanes, "Logistics / Fleet"), 330)
    n7 = d.node("decision", "Customer accepted?", 2440, row_y(lanes, "Customer") - 18, 210, 125)
    n8 = d.node("document", "Invoice / BI\nBilling after delivery", 2790, row_y(lanes, "Accounting"), 300)
    n9 = d.node("custom", "Custom candidate\nDelivery ticket, driver evaluation, BI form, non-fulfillment KPI", 920, row_y(lanes, "Accounting"), 900, 90)
    for a, b, label in [(n1, n2, ""), (n2, n3, ""), (n3, n4, "allocate"), (n4, n5, ""), (n5, n6, ""), (n6, n7, ""), (n7, n8, "Yes"), (n7, n5, "No / return"), (n9, n6, "logistics report")]:
        d.edge(a, b, label)
    d.note("Standard: Inventory delivery, delivery carrier, fleet. เพิ่มที่ต้องคุย: ticket issuing, driver evaluation, BI billing statement และ customer return trigger.", 150, 1280, 1500)
    return d


def accounting_page() -> Diagram:
    lane_names = ["Source Documents", "Accounting", "Bank / Cash", "Tax / Compliance", "Management", "Custom Controls"]
    d = Diagram("10 Accounting + Thai Tax Legacy Docs", 3400, 1430)
    d.title("Accounting + Thai Tax / Legacy Documents", "Map IV, BI, PD, RR, PS, RE, Thai Tax, QR, Netting, Multi Ledger")
    lanes = d.lanes(lane_names, lane_h=200)
    n1 = d.node("start", "Start\nSO / PO / MO / Receipt / Delivery", 210, row_y(lanes, "Source Documents"), 330)
    n2 = d.node("document", "IV / Vendor Bill\nAR/AP invoice", 600, row_y(lanes, "Accounting"), 300)
    n3 = d.node("document", "BI\nBilling Statement", 960, row_y(lanes, "Accounting"), 280)
    n4 = d.node("process", "PD / PS / RR / RE\nPayment, receipt, return entries", 1300, row_y(lanes, "Bank / Cash"), 340)
    n5 = d.node("process", "Bank Reconciliation\nMulti-currency", 1700, row_y(lanes, "Bank / Cash"), 300)
    n6 = d.node("process", "Thai Tax Report + QR\nl10n_th / l10n_th_reports", 2060, row_y(lanes, "Tax / Compliance"), 340)
    n7 = d.node("report", "Executive Report\nBU/Branch, ratio, cash forecast", 2470, row_y(lanes, "Management"), 340)
    n8 = d.node("custom", "Netting Payment\nMulti Ledger\nConsolidation", 2870, row_y(lanes, "Custom Controls"), 300)
    n9 = d.node("decision", "Standard enough?", 2480, row_y(lanes, "Custom Controls") - 18, 210, 125)
    n10 = d.node("custom", "Custom candidate\nLegacy sequence/report format, cash forecast PR/PO/AP/AR, hard lock budget, consolidation/elimination", 720, row_y(lanes, "Custom Controls"), 980, 92)
    for a, b, label in [(n1, n2, ""), (n2, n3, "billing"), (n3, n4, "payment"), (n4, n5, ""), (n5, n6, ""), (n6, n7, ""), (n7, n9, "management need"), (n9, n8, "No"), (n10, n8, "custom scope")]:
        d.edge(a, b, label)
    d.note("Standard: Accounting, bank reconciliation, Thai localization l10n_th/l10n_th_reports, QR base. Custom เฉพาะ legacy form/sequence, netting workflow, multi ledger/consolidation ที่ standard ไม่พอ.", 150, 1280, 1600)
    return d


def build_pages() -> list[Diagram]:
    return [
        legend_page(),
        overall_page(),
        sales_page(),
        procurement_page(),
        rm_warehouse_page(),
        engineering_page(),
        qc_page(),
        planning_page(),
        production_page(),
        fg_delivery_page(),
        accounting_page(),
    ]


def main() -> None:
    PACKAGE.mkdir(parents=True, exist_ok=True)
    modified = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    pages = build_pages()
    mxfile = [f'<mxfile host="app.diagrams.net" modified="{modified}" agent="Codex R001 Blueprint" version="24.7.17" type="device">']
    for i, page in enumerate(pages):
        mxfile.append(f'<diagram id="r001-blueprint-{i:02d}" name="{escape(page.name)}">{page.xml()}</diagram>')
    mxfile.append("</mxfile>")
    TARGET.write_text("\n".join(mxfile), encoding="utf-8")
    index = json.loads(INDEX.read_text(encoding="utf-8")) if INDEX.exists() else {}
    index["r001_blueprint_swimlane_drawio"] = str(TARGET)
    index["r001_blueprint_swimlane_pages"] = [p.name for p in pages]
    INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"drawio": str(TARGET), "pages": [p.name for p in pages], "page_count": len(pages)}, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
