from __future__ import annotations

import html
import json
import math
import textwrap
from pathlib import Path


OUT = Path(r"C:\365_project\TheCool18e\Dev\output\ams_workflow")
SVG_DIR = OUT / "flow_svgs"


COLORS = {
    "start": "#d9ead3",
    "process": "#dae8fc",
    "decision": "#f4cccc",
    "io": "#d0e0e3",
    "document": "#fff2cc",
    "database": "#eadcf8",
    "connector": "#f8cbad",
    "custom": "#fce4d6",
    "report": "#e2f0d9",
    "lane": "#f8fafc",
    "lane_head": "#e2e8f0",
    "stroke": "#334155",
    "header": "#5b1747",
}


def wrap_text(text: str, width: int = 24) -> list[str]:
    lines: list[str] = []
    for part in str(text).split("\n"):
        wrapped = textwrap.wrap(part, width=width, break_long_words=False) or [""]
        lines.extend(wrapped)
    return lines[:6]


def text_svg(text: str, x: float, y: float, w: float, h: float, size: int = 13, bold: bool = False) -> str:
    lines = wrap_text(text, max(12, int(w / 8)))
    line_h = size + 3
    start_y = y + (h - len(lines) * line_h) / 2 + size
    weight = "700" if bold else "400"
    spans = []
    for i, line in enumerate(lines):
        spans.append(
            f'<tspan x="{x + w / 2:.1f}" y="{start_y + i * line_h:.1f}">{html.escape(line)}</tspan>'
        )
    return f'<text text-anchor="middle" font-family="Arial, sans-serif" font-size="{size}" font-weight="{weight}" fill="#111827">{"".join(spans)}</text>'


class SvgDiagram:
    def __init__(self, title: str, width: int = 1800, height: int = 1050):
        self.title = title
        self.width = width
        self.height = height
        self.parts: list[str] = []
        self.nodes: dict[str, tuple[float, float, float, float]] = {}

    def add_title(self, subtitle: str = "") -> None:
        self.parts.append(f'<text x="32" y="44" font-family="Arial, sans-serif" font-size="28" font-weight="700" fill="{COLORS["header"]}">{html.escape(self.title)}</text>')
        if subtitle:
            self.parts.append(f'<text x="32" y="74" font-family="Arial, sans-serif" font-size="14" fill="#475569">{html.escape(subtitle)}</text>')

    def lanes(self, labels: list[str], x: int = 30, y: int = 105, lane_h: int = 135) -> list[int]:
        ys = []
        for i, label in enumerate(labels):
            yy = y + i * lane_h
            ys.append(yy)
            self.parts.append(f'<rect x="{x}" y="{yy}" width="{self.width - 60}" height="{lane_h}" fill="{COLORS["lane"]}" stroke="#cbd5e1"/>')
            self.parts.append(f'<rect x="{x}" y="{yy}" width="180" height="{lane_h}" fill="{COLORS["lane_head"]}" stroke="#cbd5e1"/>')
            self.parts.append(
                f'<text x="{x + 90}" y="{yy + lane_h / 2}" transform="rotate(-90 {x + 90} {yy + lane_h / 2})" text-anchor="middle" font-family="Arial, sans-serif" font-size="13" font-weight="700" fill="#111827">{html.escape(label)}</text>'
            )
        return ys

    def node(self, node_id: str, kind: str, label: str, x: int, y: int, w: int = 180, h: int = 64) -> None:
        fill = COLORS.get(kind, COLORS["process"])
        stroke = COLORS["stroke"]
        self.nodes[node_id] = (x, y, w, h)
        if kind == "start":
            self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h/2}" ry="{h/2}" fill="{fill}" stroke="{stroke}" stroke-width="1.4"/>')
        elif kind == "decision":
            cx, cy = x + w / 2, y + h / 2
            points = f"{cx},{y} {x+w},{cy} {cx},{y+h} {x},{cy}"
            self.parts.append(f'<polygon points="{points}" fill="{fill}" stroke="{stroke}" stroke-width="1.4"/>')
        elif kind == "io":
            points = f"{x+22},{y} {x+w},{y} {x+w-22},{y+h} {x},{y+h}"
            self.parts.append(f'<polygon points="{points}" fill="{fill}" stroke="{stroke}" stroke-width="1.4"/>')
        elif kind == "document":
            wave = y + h - 12
            path = f"M{x},{y} H{x+w} V{wave} Q{x+w*0.75},{y+h+8} {x+w*0.5},{wave} Q{x+w*0.25},{wave-8} {x},{wave} Z"
            self.parts.append(f'<path d="{path}" fill="{fill}" stroke="{stroke}" stroke-width="1.4"/>')
        elif kind == "database":
            self.parts.append(f'<rect x="{x}" y="{y+12}" width="{w}" height="{h-24}" fill="{fill}" stroke="{stroke}" stroke-width="1.4"/>')
            self.parts.append(f'<ellipse cx="{x+w/2}" cy="{y+12}" rx="{w/2}" ry="12" fill="{fill}" stroke="{stroke}" stroke-width="1.4"/>')
            self.parts.append(f'<ellipse cx="{x+w/2}" cy="{y+h-12}" rx="{w/2}" ry="12" fill="{fill}" stroke="{stroke}" stroke-width="1.4"/>')
        elif kind == "connector":
            self.parts.append(f'<circle cx="{x+w/2}" cy="{y+h/2}" r="{min(w,h)/2}" fill="{fill}" stroke="{stroke}" stroke-width="1.4"/>')
        else:
            self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="1.4"/>')
        self.parts.append(text_svg(label, x, y, w, h, size=12 if w < 170 else 13, bold=False))

    def note(self, label: str, x: int, y: int, w: int = 430, h: int = 74) -> None:
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="#fff7ed" stroke="#f59e0b" stroke-dasharray="5 4"/>')
        self.parts.append(text_svg(label, x + 8, y + 8, w - 16, h - 16, size=12))

    def edge(self, src: str, dst: str, label: str = "") -> None:
        x1, y1, w1, h1 = self.nodes[src]
        x2, y2, w2, h2 = self.nodes[dst]
        sx, sy = x1 + w1, y1 + h1 / 2
        tx, ty = x2, y2 + h2 / 2
        if tx < sx:
            sx, sy = x1 + w1 / 2, y1 + h1
            tx, ty = x2 + w2 / 2, y2
        mid = (sx + tx) / 2
        points = f"{sx:.1f},{sy:.1f} {mid:.1f},{sy:.1f} {mid:.1f},{ty:.1f} {tx:.1f},{ty:.1f}"
        self.parts.append(f'<polyline points="{points}" fill="none" stroke="#374151" stroke-width="1.6" marker-end="url(#arrow)"/>')
        if label:
            lx, ly = (sx + tx) / 2, (sy + ty) / 2 - 6
            self.parts.append(f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="11" fill="#334155">{html.escape(label)}</text>')

    def svg(self) -> str:
        defs = '<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L0,6 L9,3 z" fill="#374151"/></marker></defs>'
        bg = f'<rect width="100%" height="100%" fill="#ffffff"/>'
        return f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{self.height}" viewBox="0 0 {self.width} {self.height}">{defs}{bg}{"".join(self.parts)}</svg>'


def symbol_legend() -> SvgDiagram:
    d = SvgDiagram("Flowchart Symbol Legend", 1500, 780)
    d.add_title("Same symbols are used across all module swimlane flows")
    items = [
        ("start", "Start / End", 100, 140),
        ("process", "Process", 420, 140),
        ("decision", "Decision", 740, 125),
        ("io", "Input / Output", 1060, 140),
        ("document", "Document", 100, 380),
        ("database", "Database", 420, 380),
        ("connector", "Connector", 740, 380),
        ("custom", "Custom / Report Candidate", 1060, 380),
    ]
    for kind, label, x, y in items:
        d.node(kind, kind, label, x, y, 220, 90)
    d.note("Flowline arrows show handoff direction. Diamond nodes show decisions such as approved, stock enough, QC pass, or customer accepts.", 140, 610, 1180, 70)
    return d


def overall() -> SvgDiagram:
    d = SvgDiagram("Overall AMS -> Odoo Business Flow", 2200, 1180)
    d.add_title("End-to-end flow from Excel business requirement mapped to Odoo AMS")
    y = d.lanes(["Customer / Sales", "Planning / MRP", "Procurement", "Warehouse / Logistics", "Manufacturing / QC", "Accounting / Finance", "Management"], lane_h=145)
    d.node("s", "start", "Customer forecast / RFQ / PO", 230, y[0] + 40)
    d.node("q", "document", "Quotation / SO", 500, y[0] + 40)
    d.node("won", "decision", "Won?", 760, y[0] + 22, 120, 100)
    d.node("mrp", "process", "Run MRP / Replenishment", 1010, y[1] + 40, 220)
    d.node("stock", "decision", "Stock enough?", 1290, y[1] + 22, 140, 100)
    d.node("buy", "document", "RFQ / PO / Blanket", 1530, y[2] + 40, 210)
    d.node("recv", "process", "Receive + Barcode + Lot", 1530, y[3] + 40, 210)
    d.node("mo", "document", "MO / Work Orders", 1010, y[4] + 40, 220)
    d.node("qc", "decision", "QC pass?", 1290, y[4] + 22, 140, 100)
    d.node("fg", "database", "FG/WIP Stock + Valuation", 1530, y[4] + 35, 220, 75)
    d.node("del", "process", "Delivery + Fleet", 1790, y[3] + 40, 190)
    d.node("inv", "document", "Invoice / Bill / Payment", 1790, y[5] + 40, 210)
    d.node("rep", "report", "BU/Branch/GP/KPI Reports", 1790, y[6] + 40, 230)
    d.node("end", "start", "Management decision", 2040, y[6] + 40, 140)
    for a, b, label in [("s", "q", ""), ("q", "won", ""), ("won", "mrp", "Yes"), ("mrp", "stock", ""), ("stock", "buy", "Buy"), ("buy", "recv", ""), ("recv", "mo", ""), ("stock", "mo", "Make"), ("mo", "qc", ""), ("qc", "fg", "Pass"), ("qc", "mo", "Rework"), ("fg", "del", ""), ("del", "inv", ""), ("inv", "rep", ""), ("rep", "end", "")]:
        d.edge(a, b, label)
    d.note("Custom/report candidates: budget hard lock, supplier scorecard, DPPM, cost variance allocation, forecast import, cash forecast PR/PO/AP/AR.", 230, y[6] + 40, 600, 80)
    return d


def module_flow(name: str, lanes: list[str], nodes: list[tuple], edges: list[tuple], note: str) -> SvgDiagram:
    d = SvgDiagram(name, 2200, 1120)
    d.add_title("Detailed swimlane diagram with flowchart symbols")
    y = d.lanes(lanes, lane_h=145)
    lane_index = {lane: yy for lane, yy in zip(lanes, y)}
    for node_id, kind, label, lane, x, w in nodes:
        d.node(node_id, kind, label, x, lane_index[lane] + (22 if kind == "decision" else 40), w, 100 if kind == "decision" else 64)
    for src, dst, label in edges:
        d.edge(src, dst, label)
    d.note(note, 230, y[-1] + 42, 720, 80)
    return d


def build_diagrams() -> list[SvgDiagram]:
    diagrams = [symbol_legend(), overall()]
    diagrams.append(module_flow(
        "Sales / CRM Swimlane",
        ["Customer", "Sales / CRM", "Engineering / Product", "Inventory / MRP", "Accounting", "Management"],
        [
            ("a", "start", "Customer inquiry / RFQ", "Customer", 230, 180),
            ("b", "io", "Spec, MOQ, delivery date", "Customer", 490, 190),
            ("c", "process", "Create lead / opportunity", "Sales / CRM", 740, 210),
            ("d", "decision", "Need BOM costing?", "Sales / CRM", 1010, 150),
            ("e", "process", "Use product/BOM/pricelist", "Engineering / Product", 1240, 220),
            ("f", "custom", "Custom quotation BOM / PPAP costing", "Engineering / Product", 1240, 250),
            ("g", "document", "Quotation / SO", "Sales / CRM", 1530, 190),
            ("h", "decision", "Customer accepts?", "Sales / CRM", 1770, 150),
            ("i", "document", "Invoice + margin", "Accounting", 1980, 180),
            ("j", "report", "Win rate / GP by BU", "Management", 1980, 190),
        ],
        [("a", "b", ""), ("b", "c", ""), ("c", "d", ""), ("d", "e", "No"), ("d", "f", "Yes"), ("e", "g", ""), ("f", "g", ""), ("g", "h", ""), ("h", "i", "Yes"), ("i", "j", "")],
        "Standard: CRM, Sales, margin, analytic BU/Branch. Custom: BOM-temp costing and automotive forecast import if required.",
    ))
    diagrams.append(module_flow(
        "Procurement Swimlane",
        ["Requester / MRP", "Purchasing", "Approver / Budget", "Vendor", "Warehouse", "Accounting"],
        [
            ("a", "start", "Need material / service", "Requester / MRP", 230, 190),
            ("b", "io", "MRP shortage / min-max / PR", "Requester / MRP", 500, 210),
            ("c", "decision", "Approval required?", "Approver / Budget", 780, 150),
            ("d", "process", "Approval request", "Approver / Budget", 1040, 190),
            ("e", "document", "RFQ", "Purchasing", 1290, 160),
            ("f", "io", "Vendor quotation", "Vendor", 1510, 180),
            ("g", "decision", "Best supplier?", "Purchasing", 1740, 140),
            ("h", "document", "PO / Blanket Agreement", "Purchasing", 1960, 200),
            ("i", "process", "Receive goods", "Warehouse", 1960, 170),
            ("j", "document", "Vendor bill / AP", "Accounting", 1960, 180),
        ],
        [("a", "b", ""), ("b", "c", ""), ("c", "d", "Yes"), ("c", "e", "No"), ("d", "e", "Approved"), ("e", "f", ""), ("f", "g", ""), ("g", "h", "Yes"), ("h", "i", ""), ("i", "j", "")],
        "Standard: Purchase, Approvals, Blanket Agreement, receipt, bill. Custom: weighted supplier score and budget hard lock.",
    ))
    diagrams.append(module_flow(
        "Warehouse / Logistics Swimlane",
        ["Purchase / Sales / MRP", "Warehouse", "Barcode Device", "Logistics / Fleet", "Accounting", "Management"],
        [
            ("a", "start", "Receipt / delivery / MO movement", "Purchase / Sales / MRP", 230, 230),
            ("b", "document", "Receipt / Delivery / MO move", "Purchase / Sales / MRP", 530, 220),
            ("c", "process", "Scan product, lot, location", "Barcode Device", 830, 220),
            ("d", "decision", "Lot required?", "Warehouse", 1120, 140),
            ("e", "database", "Stock lot / quant / shelf", "Warehouse", 1360, 210),
            ("f", "decision", "Below min stock?", "Purchase / Sales / MRP", 1620, 150),
            ("g", "document", "Reordering rule -> RFQ/MO", "Purchase / Sales / MRP", 1840, 220),
            ("h", "process", "Delivery cost / route / fleet", "Logistics / Fleet", 1840, 220),
            ("i", "database", "Stock valuation", "Accounting", 1840, 180),
            ("j", "custom", "Slow/dead stock KPI", "Management", 1840, 190),
        ],
        [("a", "b", ""), ("b", "c", ""), ("c", "d", ""), ("d", "e", "Yes/No"), ("e", "f", ""), ("f", "g", "Yes"), ("f", "h", "Ship"), ("h", "i", ""), ("i", "j", "")],
        "Standard: Inventory, locations, barcode, min/max, delivery and fleet. Custom: driver evaluation and slow/dead stock KPI.",
    ))
    diagrams.append(module_flow(
        "Manufacturing / Quality Swimlane",
        ["Planning / MRP", "Engineering / Master Data", "Production / Shop Floor", "Quality", "Warehouse", "Accounting / Costing", "Management"],
        [
            ("a", "start", "SO / forecast / min-max demand", "Planning / MRP", 230, 230),
            ("b", "database", "BOM AMS.400 + routing", "Engineering / Master Data", 530, 220),
            ("c", "process", "Run MRP", "Planning / MRP", 820, 170),
            ("d", "decision", "Components available?", "Planning / MRP", 1050, 150),
            ("e", "document", "Manufacturing Order", "Production / Shop Floor", 1300, 190),
            ("f", "process", "Work orders + barcode", "Production / Shop Floor", 1550, 210),
            ("g", "decision", "QC pass?", "Quality", 1820, 140),
            ("h", "process", "Rework / scrap / alert", "Quality", 2030, 190),
            ("i", "database", "FG/WIP stock moves", "Warehouse", 2030, 190),
            ("j", "custom", "OEE/OPE/DPPM dashboard", "Management", 2030, 210),
        ],
        [("a", "b", ""), ("b", "c", ""), ("c", "d", ""), ("d", "e", "Yes"), ("e", "f", ""), ("f", "g", ""), ("g", "i", "Pass"), ("g", "h", "Fail"), ("h", "f", "Rework"), ("i", "j", "")],
        "Standard: MRP, work orders, quality points, barcode MRP, stock accounting. Custom: OPE formula, DPPM, variance allocation.",
    ))
    diagrams.append(module_flow(
        "Accounting / Finance Swimlane",
        ["Source Documents", "Accounting", "Bank / Cash", "Budget / Project", "Stock / MRP Cost", "Management"],
        [
            ("a", "start", "SO / PO / MO / stock document", "Source Documents", 230, 230),
            ("b", "document", "Invoices / bills / payments", "Accounting", 530, 230),
            ("c", "decision", "Budget applicable?", "Budget / Project", 830, 150),
            ("d", "process", "Analytic budget BU/Branch/Project", "Budget / Project", 1080, 250),
            ("e", "custom", "Budget alert / hard lock", "Budget / Project", 1380, 220),
            ("f", "io", "Bank statement import", "Bank / Cash", 1080, 190),
            ("g", "process", "Bank reconciliation", "Bank / Cash", 1380, 190),
            ("h", "database", "Stock valuation FIFO/AVCO", "Stock / MRP Cost", 1380, 220),
            ("i", "report", "Ratio / EBITDA / BU / Branch", "Management", 1660, 230),
            ("j", "custom", "Consolidation / cash forecast", "Management", 1940, 230),
        ],
        [("a", "b", ""), ("b", "c", ""), ("c", "d", "Yes"), ("d", "e", "Over budget"), ("b", "f", "Payment"), ("f", "g", ""), ("a", "h", "Stock/MO"), ("g", "i", ""), ("h", "i", ""), ("i", "j", "")],
        "Standard: Accounting, multicurrency, bank reconciliation, analytic budgets, stock valuation. Custom: hard lock, cash forecast and consolidation.",
    ))
    diagrams.append(module_flow(
        "Planning / MRP Master Data Swimlane",
        ["Sales Forecast", "Master Data", "MRP Scheduler", "Procurement", "Manufacturing", "Reporting"],
        [
            ("a", "start", "Forecast / SO demand", "Sales Forecast", 230, 190),
            ("b", "io", "Forecast qty/date/customer PO", "Sales Forecast", 500, 230),
            ("c", "database", "Product, UoM, MOQ, lead time", "Master Data", 780, 240),
            ("d", "database", "Multi-layer BOM / routing / revision", "Master Data", 1090, 260),
            ("e", "process", "MRP / replenishment run", "MRP Scheduler", 1400, 230),
            ("f", "decision", "Buy or make?", "MRP Scheduler", 1680, 140),
            ("g", "document", "RFQ / PO", "Procurement", 1900, 160),
            ("h", "document", "MO / Work Orders", "Manufacturing", 1900, 180),
            ("i", "custom", "Forecast vs invoice KPI", "Reporting", 1900, 200),
        ],
        [("a", "b", ""), ("b", "c", ""), ("c", "d", ""), ("d", "e", ""), ("e", "f", ""), ("f", "g", "Buy"), ("f", "h", "Make"), ("g", "i", ""), ("h", "i", "")],
        "Standard: routes, supplier lead time, min/max, MRP and BOM/routing. Custom: customer forecast import and forecast-to-invoice KPI.",
    ))
    return diagrams


def main() -> None:
    SVG_DIR.mkdir(parents=True, exist_ok=True)
    diagrams = build_diagrams()
    links = []
    for i, diagram in enumerate(diagrams, start=1):
        filename = f"{i:02d}_{diagram.title.lower().replace(' ', '_').replace('/', '_').replace('->', 'to')}.svg"
        path = SVG_DIR / filename
        path.write_text(diagram.svg(), encoding="utf-8")
        links.append((diagram.title, path.name))

    html_parts = [
        '<!doctype html><html><head><meta charset="utf-8"><title>AMS Visual Flow Viewer</title>',
        "<style>body{font-family:Arial,'Noto Sans Thai',sans-serif;margin:24px;background:#f8fafc;color:#111827}h1{color:#5b1747}nav a{display:inline-block;margin:4px 8px 4px 0;padding:6px 10px;border:1px solid #cbd5e1;border-radius:16px;background:#fff;text-decoration:none;color:#1f2937}section{background:#fff;border:1px solid #e5e7eb;margin:24px 0;padding:16px;box-shadow:0 1px 4px rgba(0,0,0,.05)}img{width:100%;height:auto;border:1px solid #d1d5db}</style>",
        "</head><body><h1>AMS Visual Swimlane Flow Viewer</h1>",
        "<p>Visual flowcharts generated from the AMS Excel requirements and mapped to the Odoo AMS database.</p><nav>",
    ]
    for title, name in links:
        html_parts.append(f'<a href="#{html.escape(name)}">{html.escape(title)}</a>')
    html_parts.append("</nav>")
    for title, name in links:
        html_parts.append(f'<section id="{html.escape(name)}"><h2>{html.escape(title)}</h2><img src="flow_svgs/{html.escape(name)}" alt="{html.escape(title)}"></section>')
    html_parts.append("</body></html>")
    viewer = OUT / "AMS_Visual_Swimlane_Flow_Viewer.html"
    viewer.write_text("".join(html_parts), encoding="utf-8")

    index_path = OUT / "deliverables_index.json"
    index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {}
    index["visual_flow_viewer_html"] = str(viewer)
    index["visual_flow_svgs"] = [str(SVG_DIR / name) for _, name in links]
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"viewer": str(viewer), "svg_count": len(links), "svgs": [name for _, name in links]}, indent=2))


if __name__ == "__main__":
    main()
