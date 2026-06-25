from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape


BASE = Path(r"C:\365_project\TheCool18e\Dev")
OUT = BASE / "output" / "ams_workflow"
SOURCE = BASE / "tmp" / "ams_workflow_extract_clean.json"
VERIFY = OUT / "ams_current_verification.json"


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
    "line": "#374151",
}


class Diagram:
    def __init__(self, name: str, width: int = 1900, height: int = 1300):
        self.name = name
        self.width = width
        self.height = height
        self.cells: list[str] = ['<mxCell id="0"/>', '<mxCell id="1" parent="0"/>']
        self.next_id = 2

    def _id(self) -> str:
        value = str(self.next_id)
        self.next_id += 1
        return value

    def cell(
        self,
        label: str,
        x: int,
        y: int,
        w: int,
        h: int,
        style: str,
        parent: str = "1",
        vertex: bool = True,
    ) -> str:
        cid = self._id()
        self.cells.append(
            f'<mxCell id="{cid}" value="{escape(label)}" style="{style}" '
            f'{"vertex" if vertex else "edge"}="1" parent="{parent}">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/>'
            f"</mxCell>"
        )
        return cid

    def title(self, label: str, subtitle: str = "") -> None:
        self.cell(
            label,
            30,
            20,
            self.width - 60,
            42,
            f"text;html=1;strokeColor=none;fillColor=none;fontSize=24;fontStyle=1;fontColor={PALETTE['header']};align=left;verticalAlign=middle;",
        )
        if subtitle:
            self.cell(
                subtitle,
                30,
                64,
                self.width - 60,
                34,
                "text;html=1;strokeColor=none;fillColor=none;fontSize=13;fontColor=#475569;align=left;verticalAlign=middle;",
            )

    def lane(self, label: str, x: int, y: int, w: int, h: int) -> str:
        return self.cell(
            label,
            x,
            y,
            w,
            h,
            f"swimlane;html=1;horizontal=0;startSize=34;fillColor={PALETTE['lane']};strokeColor=#CBD5E1;fontColor=#111827;fontStyle=1;",
        )

    def node(self, kind: str, label: str, x: int, y: int, w: int = 190, h: int = 72, custom_fill: str | None = None) -> str:
        fill = custom_fill or PALETTE[kind]
        common = f"whiteSpace=wrap;html=1;fillColor={fill};strokeColor=#334155;fontColor=#111827;spacing=8;"
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
        else:
            style = f"rounded=0;{common}"
        return self.cell(label, x, y, w, h, style)

    def note(self, label: str, x: int, y: int, w: int = 260, h: int = 80) -> str:
        return self.cell(
            label,
            x,
            y,
            w,
            h,
            "shape=note;whiteSpace=wrap;html=1;backgroundOutline=1;darkOpacity=0.05;fillColor=#FFF2CC;strokeColor=#D6B656;fontColor=#111827;",
        )

    def edge(self, src: str, dst: str, label: str = "") -> str:
        cid = self._id()
        self.cells.append(
            f'<mxCell id="{cid}" value="{escape(label)}" '
            f'style="edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;strokeColor={PALETTE["line"]};endArrow=block;endFill=1;fontSize=11;fontColor=#111827;" '
            f'edge="1" parent="1" source="{src}" target="{dst}">'
            '<mxGeometry relative="1" as="geometry"/></mxCell>'
        )
        return cid

    def xml(self) -> str:
        return (
            f'<mxGraphModel dx="{self.width}" dy="{self.height}" grid="1" gridSize="10" guides="1" '
            f'tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" '
            f'pageWidth="{self.width}" pageHeight="{self.height}" math="0" shadow="0"><root>'
            + "".join(self.cells)
            + "</root></mxGraphModel>"
        )


def lane_layout(diagram: Diagram, lanes: list[str], x: int = 30, y: int = 110, w: int = 260, h: int = 150) -> list[int]:
    ys: list[int] = []
    for i, lane in enumerate(lanes):
        yy = y + i * h
        diagram.lane(lane, x, yy, diagram.width - 60, h)
        ys.append(yy)
    return ys


def symbol_legend() -> Diagram:
    d = Diagram("Symbol Legend", 1500, 900)
    d.title("Flowchart Symbols Legend", "ใช้สัญลักษณ์ชุดนี้เหมือนกันทุก swimlane diagram")
    items = [
        ("start", "Start / End\nจุดเริ่มต้นหรือจบ flow", 90, 150),
        ("process", "Process\nงานที่ user หรือ Odoo ทำ", 420, 150),
        ("decision", "Decision\nเงื่อนไข Yes/No หรือเลือกทาง", 750, 140),
        ("io", "Input / Output\nข้อมูลเข้า/ผลลัพธ์ออก", 1080, 150),
        ("document", "Document\nเอกสาร Odoo เช่น SO, PO, MO, Invoice", 90, 400),
        ("database", "Database\nข้อมูล master/transaction ใน AMS", 420, 400),
        ("connector", "Connector\nจุดเชื่อม flow ข้าม lane/page", 750, 410),
        ("process", "Custom / Report Candidate\nจุดที่ standard มี data แต่ต้องทำ report/guard เพิ่ม", 1080, 400, PALETTE["custom"]),
    ]
    for item in items:
        kind, label, x, y = item[:4]
        fill = item[4] if len(item) > 4 else None
        d.node(kind, label, x, y, 240, 100, fill)
    d.edge(d.node("start", "Flowline\nลูกศรแสดงลำดับงาน", 235, 650, 220, 70), d.node("process", "Next Step", 580, 650, 180, 70), "ทิศทาง")
    d.note(
        "สีเขียว = จุดเริ่ม/จบ, ฟ้า = process มาตรฐาน, ส้มอ่อน = custom/report candidate, เหลือง = document, ม่วง = database, แดงอ่อน = decision",
        850,
        635,
        520,
        90,
    )
    return d


def overall_flow() -> Diagram:
    d = Diagram("00 Overall AMS to Odoo Flow", 2200, 1260)
    d.title("Overall Business Flow: Excel Requirement -> Odoo AMS Standard Flow", "ภาพใหญ่ตั้งแต่ customer demand ถึง accounting/reporting ใน DB AMS")
    lanes = ["Customer / Sales", "Planning / MRP", "Procurement", "Warehouse / Logistics", "Manufacturing / QC", "Accounting / Finance", "Management Reporting"]
    y = lane_layout(d, lanes, h=150)
    start = d.node("start", "Start\nCustomer forecast / PO / RFQ", 70, y[0] + 35, 170, 70)
    inp = d.node("io", "Input demand\nForecast, RFQ, customer PO", 300, y[0] + 35, 190, 70)
    quote = d.node("document", "Quotation / SO\nSales + Margin", 560, y[0] + 35, 190, 70)
    won = d.node("decision", "Won?", 810, y[0] + 22, 120, 95)
    mrp = d.node("process", "Run MRP / Replenishment\nSO demand + forecast + min/max", 1020, y[1] + 35, 230, 70)
    stock = d.node("decision", "Stock / material enough?", 1320, y[1] + 20, 150, 105)
    buy = d.node("document", "RFQ / PO / Blanket\nApproval if needed", 1550, y[2] + 35, 220, 70)
    receive = d.node("process", "Receive + Barcode\nLot, shelf/location", 1550, y[3] + 35, 220, 70)
    mo = d.node("document", "MO / Work Orders\nBOM + Routing", 1020, y[4] + 35, 230, 70)
    qc = d.node("decision", "QC pass?", 1320, y[4] + 20, 150, 105)
    fg = d.node("database", "FG stock / WIP data\nstock.move + valuation", 1550, y[4] + 30, 220, 80)
    deliver = d.node("process", "Delivery\nRoute + delivery cost + fleet", 1810, y[3] + 35, 230, 70)
    invoice = d.node("document", "Invoice / Bill / Payment\nMulti-currency", 1810, y[5] + 35, 230, 70)
    report = d.node("process", "Dashboard / Reports\nBU, Branch, GP, KPI", 1810, y[6] + 35, 230, 70, PALETTE["report"])
    end = d.node("start", "End\nManagement decision", 2045, y[6] + 35, 120, 70)
    lost = d.node("start", "End\nLost quotation", 1030, y[0] + 35, 150, 70)
    custom = d.note("Custom/report candidates: budget hard lock, supplier score, DPPM, cash forecast PR/PO/AP/AR, cost variance allocation, automotive forecast import", 70, y[6] + 30, 580, 80)
    for a, b, label in [
        (start, inp, ""),
        (inp, quote, ""),
        (quote, won, ""),
        (won, mrp, "Yes"),
        (won, lost, "No"),
        (mrp, stock, ""),
        (stock, mo, "Need manufacture"),
        (stock, buy, "Need buy"),
        (buy, receive, "Vendor delivery"),
        (receive, mo, "Components ready"),
        (mo, qc, "Operation checks"),
        (qc, fg, "Pass"),
        (qc, mo, "Fail: rework/scrap"),
        (fg, deliver, ""),
        (deliver, invoice, ""),
        (invoice, report, ""),
        (report, end, ""),
    ]:
        d.edge(a, b, label)
    d.edge(custom, report, "KPI gap")
    return d


def sales_flow() -> Diagram:
    d = Diagram("01 Sales CRM Flow", 2100, 1120)
    d.title("Sales / CRM Swimlane", "Quotation, win rate, SO, customer PO, margin, branch/BU reporting")
    lanes = ["Customer", "Sales / CRM", "Product / Engineering", "Inventory / MRP", "Accounting", "Management"]
    y = lane_layout(d, lanes, h=150)
    n1 = d.node("start", "Start\nCustomer inquiry / RFQ", 70, y[0] + 35)
    n2 = d.node("io", "Customer requirement\nSpec, MOQ, delivery date", 320, y[0] + 35)
    n3 = d.node("process", "Create lead / opportunity\nCRM customer profile", 570, y[1] + 35)
    n4 = d.node("decision", "Need BOM-based costing?", 830, y[1] + 20, 150, 105)
    n5 = d.node("process", "Use product, BoM, cost and pricelist\nStandard data source", 1070, y[2] + 35, 240, 70)
    n6 = d.node("process", "Custom quotation BOM / PPAP costing template", 1070, y[2] + 120, 240, 70, PALETTE["custom"])
    n7 = d.node("document", "Quotation\nsale.order draft", 1360, y[1] + 35)
    n8 = d.node("decision", "Customer accepts?", 1600, y[1] + 20, 140, 105)
    n9 = d.node("document", "Sales Order\nCustomer PO ref", 1810, y[1] + 35)
    n10 = d.node("process", "Check forecasted stock\nMTO/MTS/MRP", 1810, y[3] + 35)
    n11 = d.node("document", "Invoice\nAR multi-currency", 1810, y[4] + 35)
    n12 = d.node("process", "Sales analysis\nBU/Branch/GP/win rate", 1810, y[5] + 35, 210, 70, PALETTE["report"])
    n13 = d.node("start", "End\nLost / revise quotation", 1360, y[0] + 35, 190, 70)
    for a, b, label in [
        (n1, n2, ""),
        (n2, n3, ""),
        (n3, n4, ""),
        (n4, n5, "No / standard product"),
        (n4, n6, "Yes / special costing"),
        (n5, n7, ""),
        (n6, n7, "Custom option"),
        (n7, n8, ""),
        (n8, n9, "Yes"),
        (n8, n13, "No"),
        (n9, n10, "Demand"),
        (n10, n11, "Deliver / invoice"),
        (n11, n12, "posted data"),
    ]:
        d.edge(a, b, label)
    d.note("Odoo AMS evidence: S00001 quotation, sale_margin/sale_stock_margin/sale_mrp_margin installed, analytic BU/Branch configured.", 70, y[5] + 35, 560, 80)
    return d


def procurement_flow() -> Diagram:
    d = Diagram("02 Procurement Flow", 2200, 1220)
    d.title("Procurement Swimlane", "RFQ, PR/Approval, supplier evaluation, Blanket Agreement, PO, receipt and vendor bill")
    lanes = ["Requester / MRP", "Purchasing", "Approver / Budget", "Vendor", "Warehouse", "Accounting"]
    y = lane_layout(d, lanes, h=165)
    n1 = d.node("start", "Start\nNeed material / service", 70, y[0] + 45)
    n2 = d.node("io", "Input\nMRP shortage, min/max, manual PR", 330, y[0] + 45)
    n3 = d.node("decision", "Budget / approval required?", 600, y[2] + 25, 160, 110)
    n4 = d.node("process", "Approval Request\nAMS Purchase Request Approval", 850, y[2] + 45, 230, 70)
    n5 = d.node("decision", "Approved?", 1130, y[2] + 25, 140, 110)
    n6 = d.node("document", "RFQ\npurchase.order draft", 1340, y[1] + 45)
    n7 = d.node("io", "Vendor quotation\nprice, lead time, MOQ, credit term", 1580, y[3] + 45, 230, 70)
    n8 = d.node("decision", "Best supplier?", 1840, y[1] + 25, 140, 110)
    n9 = d.node("document", "PO / Blanket Agreement\nP00002 / BO00001", 2030, y[1] + 45, 230, 70)
    n10 = d.node("process", "Receive goods\nlot/barcode/location", 2030, y[4] + 45)
    n11 = d.node("document", "Vendor Bill\nAP due / CNY", 2030, y[5] + 45)
    n12 = d.node("process", "Supplier scorecard\nprice, OTD, credit", 1580, y[5] + 45, 230, 70, PALETTE["custom"])
    n13 = d.node("start", "End / Reject", 850, y[0] + 45, 150, 70)
    for a, b, label in [
        (n1, n2, ""),
        (n2, n3, ""),
        (n3, n4, "Yes"),
        (n3, n6, "No"),
        (n4, n5, ""),
        (n5, n6, "Yes"),
        (n5, n13, "No"),
        (n6, n7, "Send RFQ"),
        (n7, n8, ""),
        (n8, n9, "Yes"),
        (n8, n12, "No / analyze"),
        (n9, n10, "Vendor ships"),
        (n10, n11, "3-way match"),
        (n11, n12, "history"),
    ]:
        d.edge(a, b, label)
    d.note("Standard fit: Purchase, Purchase Agreements, Approvals, Inventory, Accounting. Custom candidate: weighted supplier evaluation and purchasing suggestion.", 70, y[5] + 45, 620, 90)
    return d


def warehouse_flow() -> Diagram:
    d = Diagram("03 Warehouse Logistics Flow", 2200, 1220)
    d.title("Warehouse / Logistic Swimlane", "Lot control, shelf/location, barcode, min/max, route, delivery cost and fleet")
    lanes = ["Purchase / Sales / MRP", "Warehouse", "Barcode Device", "Logistics / Fleet", "Accounting", "Management"]
    y = lane_layout(d, lanes, h=165)
    n1 = d.node("start", "Start\nReceipt / delivery / production movement", 70, y[0] + 45)
    n2 = d.node("document", "Operation\nReceipt, Delivery, MO move", 330, y[0] + 45)
    n3 = d.node("process", "Scan barcode\nproduct, lot, location", 600, y[2] + 45)
    n4 = d.node("decision", "Lot / serial required?", 850, y[1] + 25, 150, 110)
    n5 = d.node("database", "Stock Lot + Quant\nShelf/location", 1080, y[1] + 40, 220, 85)
    n6 = d.node("decision", "Below min stock?", 1370, y[0] + 25, 150, 110)
    n7 = d.node("document", "Reordering Rule\nGenerate RFQ/MO", 1580, y[0] + 45)
    n8 = d.node("process", "Pick / Pack / Ship\nDelivery order", 1580, y[1] + 45)
    n9 = d.node("process", "Delivery Method\ncost + carrier route", 1830, y[3] + 45)
    n10 = d.node("process", "Fleet / driver\nvehicle tracking", 1830, y[3] + 130, 190, 70)
    n11 = d.node("database", "Stock valuation\nFIFO / AVCO / COGS", 1830, y[4] + 45)
    n12 = d.node("process", "Slow/dead stock\nturnover dashboard", 1830, y[5] + 45, 220, 70, PALETTE["custom"])
    for a, b, label in [
        (n1, n2, ""),
        (n2, n3, ""),
        (n3, n4, ""),
        (n4, n5, "Yes / capture lot"),
        (n4, n5, "No / qty only"),
        (n5, n6, "stock update"),
        (n6, n7, "Yes"),
        (n6, n8, "No / fulfill"),
        (n7, n8, "after replenish"),
        (n8, n9, "delivery"),
        (n9, n10, "fleet context"),
        (n8, n11, "valuation"),
        (n11, n12, "report data"),
    ]:
        d.edge(a, b, label)
    d.note("AMS evidence: shelf/QC/WIP locations, RM1 min/max reordering rule, stock_barcode, delivery and fleet installed.", 70, y[5] + 45, 620, 90)
    return d


def manufacturing_flow() -> Diagram:
    d = Diagram("04 Manufacturing Quality Flow", 2300, 1360)
    d.title("Manufacturing / Quality Swimlane", "BOM, routing, MRP, MO, work orders, barcode, QC, WIP/FG and OEE/OPE")
    lanes = ["Planning / MRP", "Engineering / Master Data", "Production / Shop Floor", "Quality", "Warehouse", "Accounting / Costing", "Management"]
    y = lane_layout(d, lanes, h=165)
    n1 = d.node("start", "Start\nSO/forecast/min-max demand", 70, y[0] + 45)
    n2 = d.node("database", "BOM AMS.400 REV 00\n18 components", 330, y[1] + 40, 220, 85)
    n3 = d.node("database", "Routing\n21 operations / 7 work centers", 600, y[1] + 40, 240, 85)
    n4 = d.node("process", "Run MRP\nplan buy/manufacture", 900, y[0] + 45)
    n5 = d.node("decision", "Components available?", 1130, y[0] + 25, 150, 110)
    n6 = d.node("document", "Manufacturing Order\nWH/MO/00001", 1350, y[2] + 45)
    n7 = d.node("process", "Work Orders\nSLIT/LAMINATE/PUNCH/CUT/ASSEMBLY/PACK", 1600, y[2] + 45, 260, 70)
    n8 = d.node("io", "Barcode input\nstart/finish, qty, waste, time", 1600, y[2] + 130, 260, 70)
    n9 = d.node("decision", "QC pass at operation?", 1900, y[3] + 25, 160, 110)
    n10 = d.node("process", "Rework / Scrap / Alert", 1900, y[3] + 150, 210, 70, PALETTE["custom"])
    n11 = d.node("database", "FG stock\nLot + WIP/stock moves", 1900, y[4] + 45, 220, 85)
    n12 = d.node("process", "Costing\nWIP, FG, variance source", 1900, y[5] + 45, 220, 70)
    n13 = d.node("process", "OEE/OPE, DPPM,\nCost variance dashboard", 1900, y[6] + 45, 240, 70, PALETTE["custom"])
    n14 = d.node("connector", "Procurement flow", 1130, y[0] + 150, 150, 60)
    for a, b, label in [
        (n1, n2, ""),
        (n2, n3, ""),
        (n3, n4, ""),
        (n4, n5, ""),
        (n5, n6, "Yes"),
        (n5, n14, "No / buy"),
        (n6, n7, ""),
        (n7, n8, ""),
        (n8, n9, "quality point"),
        (n9, n11, "Pass"),
        (n9, n10, "Fail"),
        (n10, n7, "rework"),
        (n11, n12, "valuation"),
        (n12, n13, "report"),
    ]:
        d.edge(a, b, label)
    d.note("Standard fit: MRP, Work Orders, Quality, Barcode MRP, Stock Accounting. Custom candidates: OPE formula, DPPM, WIP value by process without locations, variance allocation.", 70, y[6] + 45, 720, 90)
    return d


def accounting_flow() -> Diagram:
    d = Diagram("05 Accounting Finance Flow", 2200, 1220)
    d.title("Accounting / Finance Swimlane", "Financial reports, BU/Branch, reconciliation, budget, cash forecast, multicurrency, valuation")
    lanes = ["Source Documents", "Accounting", "Bank / Cash", "Budget / Project", "Stock / MRP Cost", "Management"]
    y = lane_layout(d, lanes, h=165)
    n1 = d.node("start", "Start\nSO, PO, MO, Delivery, Receipt", 70, y[0] + 45)
    n2 = d.node("document", "Invoices / Bills\nAR/AP multi-currency", 330, y[1] + 45)
    n3 = d.node("decision", "Budget applicable?", 600, y[3] + 25, 150, 110)
    n4 = d.node("process", "Analytic Budget\nBU/Branch/Project", 850, y[3] + 45)
    n5 = d.node("process", "Budget alert / hard lock", 1090, y[3] + 45, 210, 70, PALETTE["custom"])
    n6 = d.node("io", "Bank statement import\nCSV/CAMT/OFX/QIF", 850, y[2] + 45)
    n7 = d.node("process", "Bank reconciliation\nmatch payments", 1090, y[2] + 45)
    n8 = d.node("database", "Stock valuation\nFIFO/AVCO/standard cost", 850, y[4] + 40, 230, 85)
    n9 = d.node("process", "WIP / COGS / FG cost\naccounting entries", 1090, y[4] + 45, 230, 70)
    n10 = d.node("process", "Cash forecast\nPR/PO/AP/AR combined", 1360, y[5] + 45, 240, 70, PALETTE["custom"])
    n11 = d.node("process", "Financial dashboards\nRatio, EBITDA, BU/Branch", 1630, y[5] + 45, 240, 70, PALETTE["report"])
    n12 = d.node("process", "Consolidation / elimination", 1900, y[5] + 45, 230, 70, PALETTE["custom"])
    for a, b, label in [
        (n1, n2, ""),
        (n2, n3, ""),
        (n3, n4, "Yes"),
        (n4, n5, "control"),
        (n2, n6, "payment"),
        (n6, n7, ""),
        (n1, n8, "stock/MO data"),
        (n8, n9, ""),
        (n7, n10, "cash data"),
        (n5, n10, "commitment"),
        (n9, n11, "cost data"),
        (n10, n11, ""),
        (n11, n12, "group reporting"),
    ]:
        d.edge(a, b, label)
    d.note("Accounting integrity: do not manipulate valuation/accounting via SQL. Design accounts, valuation method, WIP and COGS rules before custom allocation.", 70, y[5] + 45, 700, 90)
    return d


def planning_flow() -> Diagram:
    d = Diagram("06 Planning MRP Master Data Flow", 2200, 1220)
    d.title("Planning / MRP / Master Data Swimlane", "Forecast, MPS/MRP, multi-level BOM, MOQ, lead time, replenishment and reporting dimensions")
    lanes = ["Sales Forecast", "Master Data", "MRP Scheduler", "Procurement", "Manufacturing", "Reporting"]
    y = lane_layout(d, lanes, h=165)
    n1 = d.node("start", "Start\nCustomer forecast / SO demand", 70, y[0] + 45)
    n2 = d.node("io", "Input\nforecast qty, date, customer PO", 330, y[0] + 45)
    n3 = d.node("database", "Product master\nUoM, MOQ, routes, lead time", 600, y[1] + 40, 240, 85)
    n4 = d.node("database", "BOM / Routing\nmulti-layer + revisions", 890, y[1] + 40, 240, 85)
    n5 = d.node("process", "MRP / Replenishment run\ncompare demand vs supply", 1180, y[2] + 45, 250, 70)
    n6 = d.node("decision", "Buy or Make?", 1480, y[2] + 25, 150, 110)
    n7 = d.node("document", "RFQ / PO\nsupplier lead time", 1710, y[3] + 45)
    n8 = d.node("document", "MO / Work Orders\ncapacity and routing", 1710, y[4] + 45)
    n9 = d.node("process", "Forecast accuracy\nsales vs invoice / delivery", 1710, y[5] + 45, 250, 70, PALETTE["custom"])
    n10 = d.node("database", "Analytic dimensions\nBusiness Unit / Branch", 1180, y[5] + 45, 250, 70)
    for a, b, label in [
        (n1, n2, ""),
        (n2, n3, ""),
        (n3, n4, ""),
        (n4, n5, ""),
        (n5, n6, ""),
        (n6, n7, "Buy"),
        (n6, n8, "Make"),
        (n7, n9, "supply data"),
        (n8, n9, "production data"),
        (n10, n9, "BU/Branch"),
    ]:
        d.edge(a, b, label)
    d.note("Standard fit: routes, vendor lead time, min/max, MRP, BOM/routing. Custom candidate: automotive rolling forecast import and forecast-to-invoice KPI.", 70, y[5] + 45, 700, 90)
    return d


def build_report(diagrams: list[Diagram], verification: dict) -> None:
    workflow_details = {
        "00 Overall AMS to Odoo Flow": [
            ("Customer / Sales", "Receive forecast, RFQ or customer PO", "CRM Lead / Sales Quotation", "Customer demand exists", "Standard"),
            ("Sales / CRM", "Create quotation, track win/lost and convert to SO", "sale.order, crm.lead", "Won?", "Standard; BOM-temp costing may be custom"),
            ("Planning / MRP", "Run MRP from SO, forecast and min/max", "mrp, stock.warehouse.orderpoint", "Stock/material enough?", "Standard"),
            ("Procurement", "Create RFQ/PO or Blanket Agreement with approval", "purchase.order, purchase.requisition, approval.request", "Approval required?", "Budget guard may be custom"),
            ("Warehouse", "Receive, scan barcode, assign lot and shelf", "stock.picking, stock.lot, stock.location", "Lot required?", "Standard"),
            ("Manufacturing / QC", "Execute MO, WO, quality checks and rework/scrap if needed", "mrp.production, mrp.workorder, quality.point", "QC pass?", "Standard; DPPM dashboard custom"),
            ("Accounting / Finance", "Post invoice/bill/payment and valuation", "account.move, account.payment, stock.valuation.layer", "Multi-currency / reconciliation", "Standard with configuration"),
            ("Management Reporting", "Report BU/Branch, GP, cost variance, cash forecast", "account.report, spreadsheet dashboard", "KPI definition?", "Several custom reports"),
        ],
        "01 Sales CRM Flow": [
            ("Customer", "Send inquiry, RFQ, forecast or PO reference", "Input data", "Complete spec?", "Standard input"),
            ("Sales / CRM", "Create lead/opportunity and maintain customer profile", "crm.lead, res.partner", "New customer?", "Standard"),
            ("Sales / CRM", "Prepare quotation and track win rate", "sale.order", "Customer accepts?", "Standard"),
            ("Product / Engineering", "Use product/BOM/cost/pricelist for quotation basis", "product.template, mrp.bom, product.pricelist", "Need BOM-based costing?", "Custom if quotation BOM is separate from production BOM"),
            ("Inventory / MRP", "Check forecasted stock and trigger demand", "stock.quant, stock.rule, mrp.production", "Stock enough?", "Standard"),
            ("Accounting", "Invoice AR and recognize margin/reporting data", "account.move, sale_margin", "Invoiceable?", "Standard"),
            ("Management", "Review sales by BU/Branch/GP and win rate", "sale.report, analytic account", "Management KPI?", "Config/report"),
        ],
        "02 Procurement Flow": [
            ("Requester / MRP", "Create demand from shortage, reorder rule or manual request", "stock.warehouse.orderpoint, mrp", "Need buy?", "Standard"),
            ("Approver / Budget", "Review budget/approval category", "approval.category, account_budget", "Approved?", "Hard budget lock custom"),
            ("Purchasing", "Send RFQ and compare supplier quotes", "purchase.order", "Best supplier?", "Standard data, scorecard custom"),
            ("Vendor", "Submit price, lead time, MOQ and credit term", "vendor pricelist / RFQ response", "Meets target?", "Report/custom score"),
            ("Purchasing", "Confirm PO or Blanket Agreement", "purchase.order, purchase.requisition", "Agreement needed?", "Standard"),
            ("Warehouse", "Receive and validate lot/barcode", "stock.picking", "Quantity/quality ok?", "Standard"),
            ("Accounting", "Create vendor bill and payment schedule", "account.move", "3-way match?", "Standard/config"),
        ],
        "03 Warehouse Logistics Flow": [
            ("Warehouse", "Receive, store, pick, pack and deliver", "stock.picking, stock.move", "Operation type?", "Standard"),
            ("Barcode Device", "Scan product, lot, shelf and quantity", "stock_barcode", "Barcode available?", "Standard"),
            ("Warehouse", "Control shelf/location, QC hold and WIP staging", "stock.location", "Putaway/removal rule?", "Config"),
            ("Purchase / Sales / MRP", "Use min/max and forecasted inventory to replenish", "stock.warehouse.orderpoint", "Below min?", "Standard"),
            ("Logistics / Fleet", "Assign delivery method, cost, route and vehicle context", "delivery.carrier, fleet.vehicle", "Driver/ticket evaluation?", "Custom workflow candidate"),
            ("Accounting", "Update stock valuation and COGS", "stock.valuation.layer, account.move", "Valuation method?", "Standard with accounting setup"),
            ("Management", "Review slow/dead stock and delivery KPI", "inventory reports", "KPI threshold?", "Custom dashboard"),
        ],
        "04 Manufacturing Quality Flow": [
            ("Planning / MRP", "Convert demand to MO/procurement", "mrp.production, stock.rule", "Components available?", "Standard"),
            ("Engineering / Master Data", "Maintain product, multi-level BOM, routing and revisions", "product.template, mrp.bom, mrp.routing.workcenter, mrp.eco", "BOM revision needed?", "PLM standard; PPAP workflow custom"),
            ("Production / Shop Floor", "Execute work orders by work center", "mrp.workorder, mrp.workcenter", "Operation complete?", "Standard"),
            ("Production / Shop Floor", "Capture input, output, waste and time", "workorder productivity, stock.scrap", "Waste reason needed?", "Extra reporting/custom field possible"),
            ("Quality", "Run quality points and quality alerts", "quality.point, quality.check, quality.alert", "QC pass?", "Standard"),
            ("Warehouse", "Move FG/WIP and assign lot", "stock.move, stock.lot", "FG ready?", "Standard"),
            ("Accounting / Costing", "Calculate production cost and valuation", "mrp_account, stock_account", "Variance allocation needed?", "Custom accounting design"),
            ("Management", "Review OEE/OPE/DPPM/cost variance", "mrp reports + spreadsheet", "Formula defined?", "Custom KPI dashboard"),
        ],
        "05 Accounting Finance Flow": [
            ("Source Documents", "SO, PO, MO, receipt, delivery feed accounting", "sale.order, purchase.order, mrp.production, stock.picking", "Source posted?", "Standard"),
            ("Accounting", "Create invoices, bills, payments and journal entries", "account.move, account.payment", "Multi-currency?", "Standard"),
            ("Bank / Cash", "Import bank statement and reconcile", "account.bank.statement, reconciliation widget", "Bank format supported?", "Custom import if bank file is non-standard"),
            ("Budget / Project", "Track analytic budget by BU/Branch/Project", "account_budget, account.analytic.account, project.project", "Over budget?", "Alert/lock custom"),
            ("Stock / MRP Cost", "Post stock valuation, WIP, FG and COGS", "stock.valuation.layer, account.move", "FIFO/AVCO policy?", "Standard with setup"),
            ("Management", "Review ratios, EBITDA, consolidation and cash forecast", "account.report, spreadsheet dashboard", "Need statutory consolidation?", "Gap/custom/external"),
        ],
        "06 Planning MRP Master Data Flow": [
            ("Sales Forecast", "Collect customer forecast and SO demand", "sale.order, forecast input", "Forecast format standard?", "Custom import if automotive file"),
            ("Master Data", "Maintain product, UoM, MOQ, lead time, routes", "product.template, product.supplierinfo, stock.route", "Master complete?", "Config"),
            ("Master Data", "Maintain multi-layer BOM/routing/revision", "mrp.bom, mrp.routing.workcenter, mrp_plm", "Revision controlled?", "PLM standard"),
            ("MRP Scheduler", "Run MRP and replenish by buy/make rule", "mrp, stock.warehouse.orderpoint", "Buy or make?", "Standard"),
            ("Procurement", "Create RFQ from buy demand", "purchase.order", "Supplier lead time ok?", "Standard"),
            ("Manufacturing", "Create MO/WO from make demand", "mrp.production", "Capacity ok?", "Planning/capacity may need deeper setup"),
            ("Reporting", "Compare forecast vs SO vs delivery vs invoice", "sale/reporting data", "KPI definition?", "Custom dashboard"),
        ],
    }
    md = [
        "# AMS Detailed Swimlane Workflow",
        "",
        "## Standard vs Pain Point",
        "- Standard Odoo covers the core transaction flow with Sales, CRM, Purchase, Inventory, Barcode, MRP, Quality, Accounting, Budget, Project, Delivery and Fleet.",
        "- Pain points that remain custom candidates: budget hard lock, supplier scorecard, cash forecast from PR/PO/AP/AR, DPPM, cost variance allocation, slow/dead stock KPI, automotive forecast/PO import.",
        "- Accounting/stock integrity: no SQL posting or manual valuation manipulation. Any custom allocation must be designed through Odoo models and accounting rules.",
        "",
        "## DB Evidence",
        f"- Database: {verification.get('database', 'AMS')}",
        f"- URL: {verification.get('url', '')}",
        f"- Installed standard modules: {verification.get('installed_modules', '')}",
        f"- Custom modules installed: {verification.get('custom_modules_installed', '')}",
        f"- BOM/routing/quality points: {verification.get('bom_count', '')}/{verification.get('routing_operations', '')}/{verification.get('quality_points', '')}",
        "",
        "## Draw.io Pages",
    ]
    for idx, diagram in enumerate(diagrams, start=1):
        md.append(f"{idx}. {diagram.name}")
    md.append("")
    md.append("## Symbol Meaning")
    symbols = [
        ("Terminator / rounded rectangle", "Start or End of a process"),
        ("Rectangle", "Process or Odoo action"),
        ("Diamond", "Decision branch such as approved, QC pass, stock enough"),
        ("Parallelogram", "Input or output data"),
        ("Document", "Odoo document such as SO, PO, MO, Invoice"),
        ("Cylinder", "Database/master/transaction data in AMS"),
        ("Circle", "Connector to another flow/page"),
        ("Arrow", "Flowline showing direction and handoff"),
    ]
    for name, meaning in symbols:
        md.append(f"- **{name}:** {meaning}")
    md.append("")
    md.append("## Detailed Swimlane Steps")
    for flow_name, rows in workflow_details.items():
        md.append("")
        md.append(f"### {flow_name}")
        md.append("| Lane | Step | Odoo Standard Function / Model | Decision / Gate | Fit |")
        md.append("|---|---|---|---|---|")
        for lane, step, odoo, decision, fit in rows:
            md.append(f"| {lane} | {step} | {odoo} | {decision} | {fit} |")
    (OUT / "AMS_Detailed_Swimlane_Workflow_Report.md").write_text("\n".join(md), encoding="utf-8")

    html = [
        '<!doctype html><html><head><meta charset="utf-8"><title>AMS Detailed Swimlane Workflow</title>',
        "<style>body{font-family:Arial,'Noto Sans Thai',sans-serif;margin:24px;line-height:1.45;color:#17202a}table{border-collapse:collapse;width:100%}td,th{border:1px solid #d8dee9;padding:8px;vertical-align:top}th{background:#5B1747;color:white}.pill{display:inline-block;background:#eef2ff;border:1px solid #c7d2fe;border-radius:14px;padding:4px 10px;margin:3px}</style>",
        "</head><body>",
        "<h1>AMS Detailed Swimlane Workflow</h1>",
        "<h2>Standard vs Pain Point</h2>",
        "<p>Standard Odoo covers the core transaction flow. Custom candidates are only the company-specific controls, KPIs and integrations that standard Odoo does not provide directly.</p>",
        "<h2>DB Evidence</h2>",
        "<table><tr><th>Item</th><th>Value</th></tr>",
        f"<tr><td>Database</td><td>{escape(str(verification.get('database', 'AMS')))}</td></tr>",
        f"<tr><td>URL</td><td>{escape(str(verification.get('url', '')))}</td></tr>",
        f"<tr><td>Installed standard modules</td><td>{verification.get('installed_modules', '')}</td></tr>",
        f"<tr><td>Custom modules installed</td><td>{verification.get('custom_modules_installed', '')}</td></tr>",
        "</table><h2>Draw.io Pages</h2>",
    ]
    for diagram in diagrams:
        html.append(f'<span class="pill">{escape(diagram.name)}</span>')
    html.append("<h2>Symbol Meaning</h2><table><tr><th>Symbol</th><th>Meaning</th></tr>")
    for name, meaning in symbols:
        html.append(f"<tr><td>{escape(name)}</td><td>{escape(meaning)}</td></tr>")
    html.append("</table><h2>Detailed Swimlane Steps</h2>")
    for flow_name, rows in workflow_details.items():
        html.append(f"<h3>{escape(flow_name)}</h3><table><tr><th>Lane</th><th>Step</th><th>Odoo Standard Function / Model</th><th>Decision / Gate</th><th>Fit</th></tr>")
        for lane, step, odoo, decision, fit in rows:
            html.append(f"<tr><td>{escape(lane)}</td><td>{escape(step)}</td><td>{escape(odoo)}</td><td>{escape(decision)}</td><td>{escape(fit)}</td></tr>")
        html.append("</table>")
    html.append("</body></html>")
    (OUT / "AMS_Detailed_Swimlane_Workflow_Report.html").write_text("".join(html), encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    verification = json.loads(VERIFY.read_text(encoding="utf-8"))
    diagrams = [
        symbol_legend(),
        overall_flow(),
        sales_flow(),
        procurement_flow(),
        warehouse_flow(),
        manufacturing_flow(),
        accounting_flow(),
        planning_flow(),
    ]
    modified = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    mxfile = [
        f'<mxfile host="app.diagrams.net" modified="{modified}" agent="Codex" version="24.7.17" type="device">'
    ]
    for diagram in diagrams:
        mxfile.append(f'<diagram id="{escape(diagram.name.lower().replace(" ", "-"))}" name="{escape(diagram.name)}">{diagram.xml()}</diagram>')
    mxfile.append("</mxfile>")
    target = OUT / "AMS_Detailed_Swimlane_Workflows.drawio"
    target.write_text("\n".join(mxfile), encoding="utf-8")
    build_report(diagrams, verification)
    index_path = OUT / "deliverables_index.json"
    index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {}
    index["detailed_swimlane_drawio"] = str(target)
    index["detailed_swimlane_report_md"] = str(OUT / "AMS_Detailed_Swimlane_Workflow_Report.md")
    index["detailed_swimlane_report_html"] = str(OUT / "AMS_Detailed_Swimlane_Workflow_Report.html")
    index["detailed_swimlane_pages"] = [d.name for d in diagrams]
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"drawio": str(target), "pages": [d.name for d in diagrams], "source_sheets": [s["sheet"] for s in source]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
