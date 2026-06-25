from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape


ROOT = Path(r"C:\365_project\TheCool18e\Dev\output\ams_workflow_editable_new")
SOURCE = ROOT / "AMS_SWINLANE.drawio"
TARGET = ROOT / "AMS_SWINLANE_TH_PRESENT.drawio"
GUIDE_MD = ROOT / "AMS_SWINLANE_TH_วิธีอ่านและลำดับพรีเซนต์.md"
GUIDE_HTML = ROOT / "AMS_SWINLANE_TH_วิธีอ่านและลำดับพรีเซนต์.html"
INDEX = ROOT / "deliverables_index.json"


PAGE_NAMES = {
    "Symbol Legend": "02 คำอธิบายสัญลักษณ์",
    "00 Overall AMS to Odoo Flow": "03 ภาพรวม AMS End-to-End",
    "01 Sales CRM Flow": "04 Sales / CRM",
    "02 Procurement Flow": "05 Procurement",
    "03 Warehouse Logistics Flow": "06 Warehouse / Logistics",
    "04 Manufacturing Quality Flow": "07 Manufacturing / Quality",
    "05 Accounting Finance Flow": "08 Accounting / Finance",
    "06 Planning MRP Master Data Flow": "09 Planning / MRP Master Data",
}


TRANSLATIONS = {
    "3-way match": "ตรวจ 3-way match\nPO / Receipt / Vendor Bill",
    "AMS evidence: shelf/QC/WIP locations, RM1 min/max reordering rule, stock_barcode, delivery and fleet installed.": "หลักฐานใน AMS\nมี shelf/QC/WIP location, RM1 min/max, stock_barcode, delivery และ fleet",
    "Accounting": "บัญชี",
    "Accounting / Costing": "บัญชี / ต้นทุน",
    "Accounting / Finance": "บัญชี / การเงิน",
    "Accounting / Finance Swimlane": "Swimlane: บัญชี / การเงิน",
    "Accounting integrity: do not manipulate valuation/accounting via SQL. Design accounts, valuation method, WIP and COGS rules before custom allocation.": "หลัก Accounting Integrity\nห้ามแก้ valuation/accounting ด้วย SQL\nต้องออกแบบผังบัญชี, valuation method, WIP และ COGS ให้ถูกก่อนทำ custom allocation",
    "Analytic Budget BU/Branch/Project": "งบประมาณแบบ Analytic\nBU / Branch / Project",
    "Analytic dimensions Business Unit / Branch": "มิติ Analytic\nBusiness Unit / Branch",
    "Approval Request AMS Purchase Request Approval": "สร้าง Approval Request\nAMS Purchase Request Approval",
    "Approved?": "อนุมัติหรือไม่?",
    "Approver / Budget": "ผู้อนุมัติ / งบประมาณ",
    "BOM / Routing multi-layer + revisions": "BOM / Routing\nหลายชั้น + Revision",
    "BOM AMS.400 REV 00 18 components": "BOM AMS.400 REV 00\n18 components",
    "BOM, routing, MRP, MO, work orders, barcode, QC, WIP/FG and OEE/OPE": "BOM, Routing, MRP, MO, Work Orders, Barcode, QC, WIP/FG และ OEE/OPE",
    "BU/Branch": "BU / Branch",
    "Bank / Cash": "ธนาคาร / เงินสด",
    "Bank reconciliation match payments": "กระทบยอดธนาคาร\nจับคู่ payment",
    "Bank statement import CSV/CAMT/OFX/QIF": "นำเข้า Bank Statement\nCSV / CAMT / OFX / QIF",
    "Barcode Device": "อุปกรณ์ Barcode",
    "Barcode input start/finish, qty, waste, time": "Barcode input\nเริ่ม/จบงาน, qty, waste, time",
    "Below min stock?": "ต่ำกว่า Min Stock?",
    "Best supplier?": "Supplier ที่เหมาะสุด?",
    "Budget / Project": "งบประมาณ / Project",
    "Budget / approval required?": "ต้องคุมงบหรือขออนุมัติ?",
    "Budget alert / hard lock": "แจ้งเตือนงบ / Hard Lock",
    "Budget applicable?": "รายการนี้เกี่ยวกับงบ?",
    "Buy": "ซื้อ",
    "Buy or Make?": "ซื้อหรือผลิตเอง?",
    "Cash forecast PR/PO/AP/AR combined": "Cash Forecast\nรวม PR / PO / AP / AR",
    "Check forecasted stock MTO/MTS/MRP": "เช็ค Forecasted Stock\nMTO / MTS / MRP",
    "Components available?": "วัตถุดิบพร้อมหรือไม่?",
    "Components ready": "วัตถุดิบพร้อม",
    "Connector จุดเชื่อม flow ข้าม lane/page": "Connector\nจุดเชื่อม flow ข้าม lane/page",
    "Consolidation / elimination": "Consolidation /\nElimination",
    "Costing WIP, FG, variance source": "ต้นทุน WIP, FG\nและแหล่งที่มาของ variance",
    "Create lead / opportunity CRM customer profile": "สร้าง Lead / Opportunity\nและข้อมูลลูกค้าใน CRM",
    "Custom / Report Candidate จุดที่ standard มี data แต่ต้องทำ report/guard เพิ่ม": "Custom / Report Candidate\nจุดที่ Standard มี data แต่ต้องเพิ่ม report/guard",
    "Custom option": "ทางเลือก Custom",
    "Custom quotation BOM / PPAP costing template": "Custom Template\nQuotation BOM / PPAP Costing",
    "Custom/report candidates: budget hard lock, supplier score, DPPM, cash forecast PR/PO/AP/AR, cost variance allocation, automotive forecast import": "Custom / Report Candidate\nBudget hard lock, Supplier score, DPPM, Cash forecast PR/PO/AP/AR,\nCost variance allocation, Automotive forecast import",
    "Customer": "ลูกค้า",
    "Customer / Sales": "ลูกค้า / ฝ่ายขาย",
    "Customer accepts?": "ลูกค้ายืนยัน?",
    "Customer requirement Spec, MOQ, delivery date": "Requirement ลูกค้า\nSpec, MOQ, วันส่งมอบ",
    "Dashboard / Reports BU, Branch, GP, KPI": "Dashboard / Reports\nBU, Branch, GP, KPI",
    "Database ข้อมูล master/transaction ใน AMS": "Database\nข้อมูล Master / Transaction ใน AMS",
    "Decision เงื่อนไข Yes/No หรือเลือกทาง": "Decision\nเงื่อนไข Yes/No หรือเลือกทาง",
    "Deliver / invoice": "ส่งของ / ออก Invoice",
    "Delivery Method cost + carrier route": "Delivery Method\nต้นทุนขนส่ง + route",
    "Delivery Route + delivery cost + fleet": "Delivery\nRoute + delivery cost + fleet",
    "Demand": "ความต้องการ",
    "Document เอกสาร Odoo เช่น SO, PO, MO, Invoice": "Document\nเอกสาร Odoo เช่น SO, PO, MO, Invoice",
    "End / Reject": "จบ / Reject",
    "End Lost / revise quotation": "จบ: Lost\nหรือ revise quotation",
    "End Lost quotation": "จบ: Lost Quotation",
    "End Management decision": "จบ\nผู้บริหารตัดสินใจ",
    "Engineering / Master Data": "Engineering / Master Data",
    "FG stock / WIP data stock.move + valuation": "FG Stock / WIP Data\nstock.move + valuation",
    "FG stock Lot + WIP/stock moves": "FG Stock\nLot + WIP / stock moves",
    "Fail": "ไม่ผ่าน",
    "Fail: rework/scrap": "ไม่ผ่าน: Rework / Scrap",
    "Financial dashboards Ratio, EBITDA, BU/Branch": "Financial Dashboard\nRatio, EBITDA, BU / Branch",
    "Financial reports, BU/Branch, reconciliation, budget, cash forecast, multicurrency, valuation": "Financial Reports, BU/Branch, Reconciliation, Budget, Cash Forecast, Multicurrency, Valuation",
    "Fleet / driver vehicle tracking": "Fleet / Driver\nติดตามรถและคนขับ",
    "Flowchart Symbols Legend": "คำอธิบายสัญลักษณ์ Flowchart",
    "Flowline ลูกศรแสดงลำดับงาน": "Flowline\nลูกศรแสดงลำดับงาน",
    "Forecast accuracy sales vs invoice / delivery": "Forecast Accuracy\nSales vs Invoice / Delivery",
    "Forecast, MPS/MRP, multi-level BOM, MOQ, lead time, replenishment and reporting dimensions": "Forecast, MPS/MRP, Multi-level BOM, MOQ, Lead Time, Replenishment และ Reporting Dimensions",
    "Input / Output ข้อมูลเข้า/ผลลัพธ์ออก": "Input / Output\nข้อมูลเข้า / ผลลัพธ์ออก",
    "Input MRP shortage, min/max, manual PR": "Input\nMRP Shortage, Min/Max, Manual PR",
    "Input demand Forecast, RFQ, customer PO": "Input Demand\nForecast, RFQ, Customer PO",
    "Input forecast qty, date, customer PO": "Input Forecast\nQty, Date, Customer PO",
    "Inventory / MRP": "Inventory / MRP",
    "Invoice / Bill / Payment Multi-currency": "Invoice / Bill / Payment\nMulti-currency",
    "Invoice AR multi-currency": "Invoice AR\nMulti-currency",
    "Invoices / Bills AR/AP multi-currency": "Invoices / Bills\nAR / AP Multi-currency",
    "KPI gap": "KPI Gap",
    "Logistics / Fleet": "Logistics / Fleet",
    "Lot / serial required?": "ต้องใช้ Lot / Serial?",
    "Lot control, shelf/location, barcode, min/max, route, delivery cost and fleet": "Lot Control, Shelf/Location, Barcode, Min/Max, Route, Delivery Cost และ Fleet",
    "MO / Work Orders BOM + Routing": "MO / Work Orders\nBOM + Routing",
    "MO / Work Orders capacity and routing": "MO / Work Orders\nCapacity + Routing",
    "MRP / Replenishment run compare demand vs supply": "MRP / Replenishment Run\nเปรียบเทียบ Demand vs Supply",
    "MRP Scheduler": "MRP Scheduler",
    "Make": "ผลิตเอง",
    "Management": "ผู้บริหาร",
    "Management Reporting": "Management Reporting",
    "Manufacturing": "Manufacturing",
    "Manufacturing / QC": "Manufacturing / QC",
    "Manufacturing / Quality Swimlane": "Swimlane: ผลิต / Quality",
    "Manufacturing Order WH/MO/00001": "Manufacturing Order\nWH/MO/00001",
    "Master Data": "Master Data",
    "Need BOM-based costing?": "ต้องคิดต้นทุนจาก BOM?",
    "Need buy": "ต้องซื้อ",
    "Need manufacture": "ต้องผลิต",
    "Next Step": "ขั้นตอนถัดไป",
    "No": "ไม่ใช่",
    "No / analyze": "ไม่ใช่ / วิเคราะห์ต่อ",
    "No / buy": "ไม่ใช่ / ซื้อ",
    "No / fulfill": "ไม่ใช่ / ใช้ของที่มี",
    "No / qty only": "ไม่ใช่ / คุมเฉพาะจำนวน",
    "No / standard product": "ไม่ใช่ / สินค้า Standard",
    "OEE/OPE, DPPM, Cost variance dashboard": "OEE/OPE, DPPM\nCost Variance Dashboard",
    "Odoo AMS evidence: S00001 quotation, sale_margin/sale_stock_margin/sale_mrp_margin installed, analytic BU/Branch configured.": "หลักฐานใน Odoo AMS\nมี S00001 quotation, sale_margin / sale_stock_margin / sale_mrp_margin\nและ Analytic BU/Branch",
    "Operation Receipt, Delivery, MO move": "Operation\nReceipt, Delivery, MO Move",
    "Operation checks": "ตรวจตาม Operation",
    "Overall Business Flow: Excel Requirement -> Odoo AMS Standard Flow": "ภาพรวม Business Flow\nจาก Excel Requirement -> Odoo AMS Standard Flow",
    "PO / Blanket Agreement P00002 / BO00001": "PO / Blanket Agreement\nP00002 / BO00001",
    "Pass": "ผ่าน",
    "Pick / Pack / Ship Delivery order": "Pick / Pack / Ship\nDelivery Order",
    "Planning / MRP": "Planning / MRP",
    "Planning / MRP / Master Data Swimlane": "Swimlane: Planning / MRP / Master Data",
    "Process งานที่ user หรือ Odoo ทำ": "Process\nงานที่ User หรือ Odoo ทำ",
    "Procurement": "Procurement",
    "Procurement Swimlane": "Swimlane: Procurement",
    "Procurement flow": "Procurement Flow",
    "Product / Engineering": "Product / Engineering",
    "Product master UoM, MOQ, routes, lead time": "Product Master\nUoM, MOQ, Routes, Lead Time",
    "Production / Shop Floor": "Production / Shop Floor",
    "Purchase / Sales / MRP": "Purchase / Sales / MRP",
    "Purchasing": "Purchasing",
    "QC pass at operation?": "QC ผ่านใน Operation?",
    "QC pass?": "QC ผ่าน?",
    "Quality": "Quality",
    "Quotation / SO Sales + Margin": "Quotation / SO\nSales + Margin",
    "Quotation sale.order draft": "Quotation\nsale.order draft",
    "Quotation, win rate, SO, customer PO, margin, branch/BU reporting": "Quotation, Win Rate, SO, Customer PO, Margin, Branch/BU Reporting",
    "RFQ / PO / Blanket Approval if needed": "RFQ / PO / Blanket\nขออนุมัติเมื่อจำเป็น",
    "RFQ / PO supplier lead time": "RFQ / PO\nSupplier Lead Time",
    "RFQ purchase.order draft": "RFQ\npurchase.order draft",
    "RFQ, PR/Approval, supplier evaluation, Blanket Agreement, PO, receipt and vendor bill": "RFQ, PR/Approval, Supplier Evaluation, Blanket Agreement, PO, Receipt และ Vendor Bill",
    "Receive + Barcode Lot, shelf/location": "รับสินค้า + Barcode\nLot, Shelf / Location",
    "Receive goods lot/barcode/location": "รับสินค้า\nLot / Barcode / Location",
    "Reordering Rule Generate RFQ/MO": "Reordering Rule\nสร้าง RFQ / MO",
    "Reporting": "Reporting",
    "Requester / MRP": "ผู้ขอซื้อ / MRP",
    "Rework / Scrap / Alert": "Rework / Scrap / Alert",
    "Routing 21 operations / 7 work centers": "Routing\n21 Operations / 7 Work Centers",
    "Run MRP / Replenishment SO demand + forecast + min/max": "Run MRP / Replenishment\nSO Demand + Forecast + Min/Max",
    "Run MRP plan buy/manufacture": "Run MRP\nวางแผนซื้อ / ผลิต",
    "Sales / CRM": "Sales / CRM",
    "Sales / CRM Swimlane": "Swimlane: Sales / CRM",
    "Sales Forecast": "Sales Forecast",
    "Sales Order Customer PO ref": "Sales Order\nCustomer PO Ref",
    "Sales analysis BU/Branch/GP/win rate": "Sales Analysis\nBU / Branch / GP / Win Rate",
    "Scan barcode product, lot, location": "สแกน Barcode\nProduct, Lot, Location",
    "Send RFQ": "ส่ง RFQ",
    "Slow/dead stock turnover dashboard": "Slow / Dead Stock\nTurnover Dashboard",
    "Source Documents": "เอกสารต้นทาง",
    "Standard fit: MRP, Work Orders, Quality, Barcode MRP, Stock Accounting. Custom candidates: OPE formula, DPPM, WIP value by process without locations, variance allocation.": "Standard Fit\nMRP, Work Orders, Quality, Barcode MRP, Stock Accounting\nCustom Candidate: สูตร OPE, DPPM, มูลค่า WIP ตาม process, Variance Allocation",
    "Standard fit: Purchase, Purchase Agreements, Approvals, Inventory, Accounting. Custom candidate: weighted supplier evaluation and purchasing suggestion.": "Standard Fit\nPurchase, Purchase Agreements, Approvals, Inventory, Accounting\nCustom Candidate: Weighted Supplier Evaluation และ Purchasing Suggestion",
    "Standard fit: routes, vendor lead time, min/max, MRP, BOM/routing. Custom candidate: automotive rolling forecast import and forecast-to-invoice KPI.": "Standard Fit\nRoutes, Vendor Lead Time, Min/Max, MRP, BOM/Routing\nCustom Candidate: Automotive Rolling Forecast Import และ Forecast-to-Invoice KPI",
    "Start / End จุดเริ่มต้นหรือจบ flow": "Start / End\nจุดเริ่มต้นหรือจบ Flow",
    "Start Customer forecast / PO / RFQ": "Start\nCustomer Forecast / PO / RFQ",
    "Start Customer forecast / SO demand": "Start\nCustomer Forecast / SO Demand",
    "Start Customer inquiry / RFQ": "Start\nCustomer Inquiry / RFQ",
    "Start Need material / service": "Start\nต้องการ Material / Service",
    "Start Receipt / delivery / production movement": "Start\nReceipt / Delivery / Production Movement",
    "Start SO, PO, MO, Delivery, Receipt": "Start\nSO, PO, MO, Delivery, Receipt",
    "Start SO/forecast/min-max demand": "Start\nSO / Forecast / Min-Max Demand",
    "Stock / MRP Cost": "Stock / MRP Cost",
    "Stock / material enough?": "Stock / Material เพียงพอ?",
    "Stock Lot + Quant Shelf/location": "Stock Lot + Quant\nShelf / Location",
    "Stock valuation FIFO / AVCO / COGS": "Stock Valuation\nFIFO / AVCO / COGS",
    "Stock valuation FIFO/AVCO/standard cost": "Stock Valuation\nFIFO / AVCO / Standard Cost",
    "Supplier scorecard price, OTD, credit": "Supplier Scorecard\nPrice, OTD, Credit",
    "Use product, BoM, cost and pricelist Standard data source": "ใช้ข้อมูล Standard\nProduct, BOM, Cost, Pricelist",
    "Vendor": "Vendor",
    "Vendor Bill AP due / CNY": "Vendor Bill\nAP Due / CNY",
    "Vendor delivery": "Vendor Delivery",
    "Vendor quotation price, lead time, MOQ, credit term": "Vendor Quotation\nPrice, Lead Time, MOQ, Credit Term",
    "Vendor ships": "Vendor ส่งสินค้า",
    "WIP / COGS / FG cost accounting entries": "Accounting Entries\nWIP / COGS / FG Cost",
    "Warehouse": "Warehouse",
    "Warehouse / Logistic Swimlane": "Swimlane: Warehouse / Logistics",
    "Warehouse / Logistics": "Warehouse / Logistics",
    "Won?": "Won?",
    "Work Orders SLIT/LAMINATE/PUNCH/CUT/ASSEMBLY/PACK": "Work Orders\nSLIT / LAMINATE / PUNCH / CUT / ASSEMBLY / PACK",
    "Yes": "ใช่",
    "Yes / capture lot": "ใช่ / บันทึก Lot",
    "Yes / special costing": "ใช่ / Special Costing",
    "after replenish": "หลังเติมของ",
    "cash data": "ข้อมูลเงินสด",
    "commitment": "ภาระผูกพัน",
    "control": "ควบคุม",
    "cost data": "ข้อมูลต้นทุน",
    "delivery": "ส่งของ",
    "fleet context": "ข้อมูล Fleet",
    "group reporting": "Group Reporting",
    "history": "ประวัติ",
    "payment": "Payment",
    "posted data": "ข้อมูลที่ Post แล้ว",
    "production data": "ข้อมูลผลิต",
    "quality point": "Quality Point",
    "report": "Report",
    "report data": "ข้อมูล Report",
    "rework": "Rework",
    "stock update": "อัปเดต Stock",
    "stock/MO data": "ข้อมูล Stock / MO",
    "supply data": "ข้อมูล Supply",
    "valuation": "Valuation",
    "ทิศทาง": "ทิศทาง",
    "ภาพใหญ่ตั้งแต่ customer demand ถึง accounting/reporting ใน DB AMS": "ภาพใหญ่ตั้งแต่ Customer Demand ถึง Accounting / Reporting ใน Database AMS",
    "สีเขียว = จุดเริ่ม/จบ, ฟ้า = process มาตรฐาน, ส้มอ่อน = custom/report candidate, เหลือง = document, ม่วง = database, แดงอ่อน = decision": "สีเขียว = จุดเริ่ม/จบ, ฟ้า = Process มาตรฐาน, ส้มอ่อน = Custom/Report Candidate, เหลือง = Document, ม่วง = Database, แดงอ่อน = Decision",
    "ใช้สัญลักษณ์ชุดนี้เหมือนกันทุก swimlane diagram": "ใช้สัญลักษณ์ชุดนี้เหมือนกันทุก Swimlane Diagram",
}


def norm(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def set_style(cell: ET.Element, updates: dict[str, str]) -> None:
    parts = [part for part in cell.attrib.get("style", "").split(";") if part]
    values: dict[str, str] = {}
    flags: list[str] = []
    for part in parts:
        if "=" in part:
            key, value = part.split("=", 1)
            values[key] = value
        else:
            flags.append(part)
    values.update(updates)
    cell.set("style", ";".join(flags + [f"{k}={v}" for k, v in values.items()]) + ";")


def cell(
    root: ET.Element,
    cell_id: str,
    label: str,
    x: int,
    y: int,
    w: int,
    h: int,
    style: str,
) -> None:
    item = ET.SubElement(root, "mxCell", {
        "id": cell_id,
        "value": label,
        "style": style,
        "vertex": "1",
        "parent": "1",
    })
    ET.SubElement(item, "mxGeometry", {
        "x": str(x),
        "y": str(y),
        "width": str(w),
        "height": str(h),
        "as": "geometry",
    })


def text_page(page_id: str, name: str, title: str, subtitle: str, sections: list[tuple[str, str]]) -> ET.Element:
    diagram = ET.Element("diagram", {"id": page_id, "name": name})
    model = ET.SubElement(diagram, "mxGraphModel", {
        "dx": "1700",
        "dy": "1250",
        "grid": "1",
        "gridSize": "10",
        "guides": "1",
        "tooltips": "1",
        "connect": "1",
        "arrows": "1",
        "fold": "1",
        "page": "1",
        "pageScale": "1",
        "pageWidth": "1700",
        "pageHeight": "1250",
        "math": "0",
        "shadow": "0",
    })
    root = ET.SubElement(model, "root")
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})
    title_style = "text;html=1;strokeColor=none;fillColor=none;fontSize=28;fontStyle=1;fontColor=#5B1747;align=left;verticalAlign=middle;fontFamily=Arial;"
    subtitle_style = "text;html=1;strokeColor=none;fillColor=none;fontSize=14;fontColor=#475569;align=left;verticalAlign=middle;fontFamily=Arial;"
    header_style = "rounded=1;whiteSpace=wrap;html=1;fillColor=#5B1747;strokeColor=#5B1747;fontColor=#FFFFFF;fontSize=16;fontStyle=1;spacing=10;fontFamily=Arial;"
    body_style = "rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#CBD5E1;fontColor=#111827;fontSize=13;spacing=12;fontFamily=Arial;verticalAlign=top;"
    cell(root, "2", title, 50, 30, 1600, 46, title_style)
    cell(root, "3", subtitle, 50, 80, 1600, 38, subtitle_style)
    x_positions = [60, 600, 1140]
    y_positions = [150, 440, 730, 1020]
    index = 4
    for i, (section_title, section_body) in enumerate(sections):
        x = x_positions[i % 3]
        y = y_positions[i // 3]
        cell(root, str(index), section_title, x, y, 500, 46, header_style)
        index += 1
        cell(root, str(index), section_body, x, y + 46, 500, 210, body_style)
        index += 1
    return diagram


def build_intro_pages() -> list[ET.Element]:
    reading_sections = [
        (
            "1. อ่านจากซ้ายไปขวา",
            "เริ่มที่กล่อง Start แล้วตามลูกศรไปทีละขั้น\nถ้าเจอเส้นย้อนกลับ ให้มองว่าเป็น loop เช่น Rework หรือ Replenish\nอย่าข้าม Decision เพราะเป็นจุดที่ระบบแยกทางเลือก",
        ),
        (
            "2. อ่านตาม Swimlane",
            "แต่ละ lane คือเจ้าของงานหรือ module\nถ้าลูกศรข้าม lane แปลว่ามี handoff ระหว่างแผนกหรือ Odoo app\nจุดข้าม lane คือจุดที่ควรถามเรื่อง owner, SLA และข้อมูลที่ต้องส่งต่อ",
        ),
        (
            "3. ใช้สีและ Symbol",
            "เขียว = Start/End\nฟ้า = Process มาตรฐาน Odoo\nเหลือง = Document เช่น SO/PO/MO/Invoice\nม่วง = Database/Master Data\nแดง = Decision\nส้ม = Custom หรือ Report Candidate",
        ),
        (
            "4. แยก Standard vs Pain Point",
            "ถ้าเป็นกล่องฟ้าหรือเหลือง ให้เริ่มจาก Odoo Standard ก่อน\nถ้าเป็นกล่องส้ม ให้ใช้เป็นรายการ workshop ต่อว่าต้อง custom จริงหรือเป็น config/report ได้\nหลักคือ Standard First, Custom Later",
        ),
        (
            "5. อ่าน Decision",
            "Decision คือจุดควบคุมธุรกิจ เช่น Approve?, QC Pass?, Buy or Make?\nทุก Decision ต้องมีคำตอบชัดเจนว่าใครตัดสินใจ ใช้ข้อมูลอะไร และผลลัพธ์ไป flow ไหน",
        ),
        (
            "6. อ่านผลกระทบ Stock/Accounting",
            "ทุกขั้นที่มี stock.move, valuation, WIP, FG, COGS, Invoice หรือ Payment ต้องระวัง Accounting & Stock Integrity\nห้ามออกแบบให้แก้ stock/cost/accounting ด้วย manual SQL",
        ),
    ]
    present_sections = [
        (
            "1. เปิดด้วย Scope",
            "บอกว่า diagram นี้แปลง Business Flow จาก Excel ไปเทียบกับ Odoo AMS DB\nเป้าหมายคือดูว่า Standard Odoo รองรับตรงไหน และ Pain Point ไหนต้อง custom/config/report",
        ),
        (
            "2. อธิบาย Legend",
            "ใช้หน้า Symbol Legend อธิบายความหมายของสีและรูปทรง\nย้ำว่าอ่านทุกหน้าแบบเดียวกันเพื่อไม่ให้ทีมตีความต่างกัน",
        ),
        (
            "3. Present Overall Flow",
            "พาอ่านภาพรวมจาก Customer Demand -> Sales -> MRP -> Procurement/Manufacturing -> Warehouse -> Accounting -> Management Reporting\nหน้านี้ใช้เพื่อให้ทุกฝ่ายเห็น End-to-End ก่อนลง module",
        ),
        (
            "4. ลง Module ทีละหน้า",
            "เรียง Sales, Procurement, Warehouse, Manufacturing, Accounting, Planning\nในแต่ละหน้าให้พูด Owner, Document, Decision, Standard Fit, Pain Point และ Data ที่ต้อง setup",
        ),
        (
            "5. สรุป Gap",
            "รวมรายการที่ Odoo Standard มีแล้ว, ต้อง config, ต้อง report และอาจต้อง custom\nเน้นว่าทุก custom ต้องมีเหตุผลและไม่กระทบ Stock/Accounting Integrity",
        ),
        (
            "6. ปิดด้วย Next Step",
            "เสนอ workshop ตรวจ owner/data/master setup\nยืนยัน module ที่ต้องเปิดใน AMS DB\nจัด priority custom candidate และกำหนด UAT scenario จาก flow นี้",
        ),
    ]
    return [
        text_page("00-how-to-read-flow-th", "00 วิธีอ่าน Flow", "วิธีอ่าน Swimlane Flow", "ใช้หน้านี้อธิบายวิธีอ่าน diagram ก่อนเริ่ม present flow จริง", reading_sections),
        text_page("01-present-sequence-th", "01 ลำดับ Present", "ลำดับการ Present ตั้งแต่ต้นจนจบ", "ใช้เป็น speaker guide ใน diagrams.net ก่อนเข้า flow ราย module", present_sections),
    ]


def translate_drawio() -> tuple[int, list[str]]:
    tree = ET.parse(SOURCE)
    mxfile = tree.getroot()
    mxfile.set("modified", datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
    mxfile.set("agent", "Codex Thai Flow")
    for diagram in mxfile.findall("diagram"):
        original_name = diagram.attrib.get("name", "")
        if original_name in PAGE_NAMES:
            diagram.set("name", PAGE_NAMES[original_name])
        graph = diagram.find("mxGraphModel")
        if graph is None:
            continue
        root = graph.find("root")
        if root is None:
            continue
        for item in root.findall("mxCell"):
            value = item.attrib.get("value")
            if value:
                translated = TRANSLATIONS.get(norm(value))
                if translated:
                    item.set("value", translated)
            if item.attrib.get("vertex") == "1":
                set_style(item, {
                    "fontFamily": "Arial",
                    "fontSize": "12" if not item.attrib.get("style", "").startswith("text;") else "14",
                    "spacing": "10",
                })
            if item.attrib.get("edge") == "1":
                set_style(item, {
                    "fontFamily": "Arial",
                    "fontSize": "12",
                    "labelBackgroundColor": "#FFFFFF",
                })
    existing = list(mxfile)
    for child in existing:
        mxfile.remove(child)
    intro_pages = build_intro_pages()
    for page in intro_pages:
        mxfile.append(page)
    for child in existing:
        mxfile.append(child)
    tree.write(TARGET, encoding="utf-8", xml_declaration=False)
    pages = [d.attrib.get("name", "") for d in ET.parse(TARGET).getroot().findall("diagram")]
    return len(pages), pages


GUIDE = """# AMS Swimlane ภาษาไทย: วิธีอ่าน Flow และลำดับการ Present

## วัตถุประสงค์ของเอกสาร

เอกสารนี้ใช้คู่กับไฟล์ `AMS_SWINLANE_TH_PRESENT.drawio` เพื่อ present Business Flow ที่แปลงจาก Excel Requirement ไปเทียบกับ Odoo AMS DB โดยยึดหลัก Standard First, Custom Later

สิ่งที่ต้องตอบระหว่าง present:

- Odoo Standard รองรับ flow นี้ตรงไหน
- จุดไหนเป็น configuration หรือ master data setup
- จุดไหนเป็น pain point ที่อาจต้อง custom/report
- จุดไหนกระทบ Stock, Costing, Accounting หรือ Approval
- ข้อมูลอะไรต้องเตรียมก่อน UAT

## วิธีอ่าน Swimlane Flow แบบละเอียด

### 1. อ่านจากซ้ายไปขวา

ให้เริ่มจากกล่อง `Start` ทางซ้าย แล้วไล่ตามลูกศรไปทางขวาเสมอ ถ้ามีลูกศรย้อนกลับ ให้ตีความเป็น loop ของงาน เช่น Rework, Replenishment, Revision หรือ Re-approval

จุดที่ไม่ควรข้ามคือ Decision เพราะเป็นจุดที่ระบบเปลี่ยนเส้นทาง เช่น `Approved?`, `QC pass?`, `Buy or Make?`, `Stock enough?`

### 2. อ่านตาม Swimlane

แต่ละ Swimlane คือเจ้าของงาน, แผนก หรือ Odoo module ที่รับผิดชอบ ถ้าเส้น flow ข้าม lane แปลว่ามีการ handoff ข้อมูลหรือเอกสารจากฝ่ายหนึ่งไปอีกฝ่ายหนึ่ง

เวลาตรวจ flow ให้ถาม 4 เรื่องที่จุดข้าม lane:

- ใครเป็น owner ของขั้นตอนนี้
- ข้อมูลส่งต่อคืออะไร
- เอกสาร Odoo ที่ถูกสร้างคืออะไร
- ต้องมี approval หรือ validation หรือไม่

### 3. อ่านจากสัญลักษณ์

| Symbol | ความหมาย | วิธีใช้ถามใน workshop |
|---|---|---|
| Start / End | จุดเริ่มหรือจบ flow | Trigger คืออะไร และจบเมื่อเอกสาร/สถานะอะไร |
| Process | งานที่ user หรือ Odoo ทำ | ทำใน Odoo app ไหน และทำ manual หรือ automate |
| Decision | จุดตัดสินใจ | ใครตัดสินใจ ใช้ข้อมูลอะไร มีทางออกกี่ทาง |
| Input / Output | ข้อมูลเข้า/ผลลัพธ์ | Source data มาจากไหน format อะไร |
| Document | เอกสาร Odoo | SO, PO, MO, Invoice, Receipt, Delivery คือเลขเอกสารหลัก |
| Database | Master/Transaction data | ต้อง setup master อะไร และ data นี้กระทบ module ไหน |
| Custom / Report Candidate | จุดที่ standard ยังไม่ตอบครบ | เป็น config, report, import, automation หรือ custom code |

### 4. อ่าน Standard vs Pain Point

ถ้าเป็น process/document/database มาตรฐาน ให้เริ่มตอบด้วย Odoo Standard ก่อน เช่น Sales, Purchase, Inventory, MRP, Quality, Accounting, Approval, Barcode

ถ้าเป็น custom/report candidate อย่ารีบสรุปว่า custom ทันที ให้แยกเป็น 4 ระดับ:

- Standard ทำได้เลย
- Standard ทำได้แต่ต้อง config/master data
- ต้องทำ report/import/automation เพิ่ม
- ต้อง custom จริง เพราะ standard ไม่มี business rule นั้น

### 5. อ่านผลกระทบ Accounting & Stock

ขั้นตอนที่เกี่ยวกับ stock.move, stock valuation, WIP, FG, COGS, Invoice, Vendor Bill, Payment ต้องตรวจเป็นพิเศษ เพราะถ้าออกแบบผิดจะกระทบต้นทุนและงบการเงิน

หลักที่ใช้ตอบคือ ห้ามแก้ stock/cost/accounting ด้วย manual SQL หรือ logic ที่ไม่ผ่าน Odoo model มาตรฐาน

## ลำดับการ Present ตั้งแต่ต้นจนจบ

### ช่วงที่ 1: เปิดการนำเสนอ

เวลาแนะนำ: 3-5 นาที

พูดให้ชัดว่า flow นี้สร้างจาก Excel Requirement และถูก mapping กับ Odoo AMS DB โดยเน้นการใช้ Standard Odoo ก่อน custom จุดประสงค์ไม่ใช่แค่ดูภาพสวย แต่ใช้เป็นเอกสารตัดสินใจว่า implementation จะทำอะไรบ้าง

Key message:

- AMS DB setup เป็นฐานสำหรับทดลอง standard flow
- Diagram แยกเป็นภาพรวมและ flow ราย module
- สีส้มคือจุดที่ยังต้องหารือ ไม่ใช่สรุปว่าต้อง custom แล้วเสมอ

### ช่วงที่ 2: อธิบายวิธีอ่านและ Symbol

เวลาแนะนำ: 5 นาที

เปิดหน้า `00 วิธีอ่าน Flow` และ `02 คำอธิบายสัญลักษณ์`

พูดตามลำดับ:

1. อ่านซ้ายไปขวา
2. อ่านตาม lane เพื่อดู owner
3. Decision คือจุดที่ต้องมี business rule
4. Document คือเอกสาร Odoo ที่ตรวจสอบได้
5. Database คือ master/transaction ที่ต้อง setup
6. Custom/Report Candidate คือ pain point ที่ต้องแยกระดับ

### ช่วงที่ 3: Present ภาพรวม End-to-End

เวลาแนะนำ: 8-10 นาที

เปิดหน้า `03 ภาพรวม AMS End-to-End`

ลำดับพูด:

1. เริ่มจาก Customer Forecast / PO / RFQ
2. Sales สร้าง Quotation/SO
3. ถ้า won แล้วส่ง demand เข้า MRP/Replenishment
4. ระบบตัดสินใจว่าต้องซื้อ, ผลิต หรือใช้ stock ที่มี
5. Procurement ออก RFQ/PO/Blanket และรับสินค้าเข้า warehouse
6. Manufacturing สร้าง MO/Work Orders และ QC
7. Warehouse จัด FG stock และ delivery
8. Accounting ทำ invoice/bill/payment และ valuation
9. Management ดู dashboard/report เพื่อใช้ตัดสินใจ

จุดเน้น:

- ภาพนี้คือ flow ใหญ่ ไม่ลง detail ทุก field
- จุดข้าม module คือจุดสำคัญของ data handoff
- Pain point ใหญ่จะไปแตกในแต่ละ module

### ช่วงที่ 4: Sales / CRM

เวลาแนะนำ: 6-8 นาที

เปิดหน้า `04 Sales / CRM`

สิ่งที่ต้องพูด:

- Trigger คือ Customer Inquiry/RFQ
- Standard Odoo รองรับ CRM, Quotation, Sales Order, Customer PO Ref, Pricelist, Margin และ Sales Analysis
- ถ้าต้องคิดราคาจาก BOM หรือ PPAP Costing Template จะเป็น custom/report candidate
- เมื่อ SO confirmed จะส่ง demand ไป Inventory/MRP

คำถามที่ควรถามทีม:

- ใช้ quotation revision อย่างไร
- Margin ต้องดูระดับ line, order, product หรือ customer
- Customer forecast เข้ามาเป็นไฟล์หรือ manual entry
- ต้องการ approval ก่อนส่ง quotation หรือไม่

### ช่วงที่ 5: Procurement

เวลาแนะนำ: 8-10 นาที

เปิดหน้า `05 Procurement`

สิ่งที่ต้องพูด:

- Trigger มาจาก MRP shortage, min/max, manual PR หรือ service request
- Standard Odoo รองรับ RFQ, PO, Blanket Agreement, Approval, Receipt และ Vendor Bill
- 3-way match ต้องโยง PO, Receipt และ Vendor Bill
- Supplier scorecard เป็น pain point ที่อาจต้อง report/custom ถ้าต้อง weighted score

คำถามที่ควรถามทีม:

- มี PR จริงก่อน PO หรือใช้ Approval แทนได้
- Approval rule อิงวงเงิน, budget, product category หรือ department
- Supplier evaluation ใช้คะแนนอะไร เช่น price, OTD, quality, credit
- Blanket Agreement ต้องคุมราคาและช่วงเวลาอย่างไร

### ช่วงที่ 6: Warehouse / Logistics

เวลาแนะนำ: 7-9 นาที

เปิดหน้า `06 Warehouse / Logistics`

สิ่งที่ต้องพูด:

- Standard Odoo รองรับ Receipt, Delivery, Internal Transfer, Barcode, Lot/Serial, Location, Reordering Rule
- Shelf/QC/WIP location ใน AMS ถูก setup เพื่อรองรับการ track stock
- Delivery Method และ Fleet เป็น standard ที่ใช้ต่อยอด logistics ได้
- Slow/dead stock dashboard เป็น report candidate

คำถามที่ควรถามทีม:

- ต้องบังคับ Lot/Serial กับ product ไหน
- ต้อง scan ทุก operation หรือเฉพาะ receipt/delivery
- Shelf location ลึกถึงระดับใด
- KPI stock aging/slow moving คำนวณจากวันไหน

### ช่วงที่ 7: Manufacturing / Quality

เวลาแนะนำ: 10-12 นาที

เปิดหน้า `07 Manufacturing / Quality`

สิ่งที่ต้องพูด:

- Standard Odoo รองรับ BOM, Routing, Work Centers, MO, Work Orders, Quality Points, Barcode MRP และ Stock Accounting
- AMS.400 REV 00 เป็นตัวอย่าง BOM พร้อม routing หลาย operation
- Decision สำคัญคือ Components available? และ QC pass?
- ถ้า QC fail ต้องระบุว่า rework, scrap หรือ quality alert
- OEE/OPE, DPPM และ variance allocation เป็น custom/report candidate

คำถามที่ควรถามทีม:

- ต้อง track WIP ตาม process หรือ location
- Waste/scrap เก็บที่ operation ไหน
- Quality point ต้องเกิดก่อน/ระหว่าง/หลัง operation
- Cost variance ต้องแยก material, labor, overhead หรือ machine

### ช่วงที่ 8: Accounting / Finance

เวลาแนะนำ: 8-10 นาที

เปิดหน้า `08 Accounting / Finance`

สิ่งที่ต้องพูด:

- Source document มาจาก SO, PO, MO, Receipt, Delivery
- Standard Odoo รองรับ AR/AP, multicurrency, bank statement import, reconciliation, analytic budget และ stock valuation
- Budget hard lock, cash forecast, consolidation อาจเป็น custom/report candidate
- ต้องรักษา Accounting & Stock Integrity โดยไม่แก้ valuation/accounting แบบ manual

คำถามที่ควรถามทีม:

- ใช้ FIFO, AVCO หรือ Standard Cost กับ product กลุ่มใด
- Budget control ต้อง warning หรือ hard block
- Cash forecast ต้องรวม PR/PO/AP/AR ระดับไหน
- Consolidation ต้องรวมบริษัทหรือ branch อย่างไร

### ช่วงที่ 9: Planning / MRP / Master Data

เวลาแนะนำ: 7-9 นาที

เปิดหน้า `09 Planning / MRP Master Data`

สิ่งที่ต้องพูด:

- Master data คือฐานของ flow ทั้งหมด เช่น Product, UoM, MOQ, Route, Lead Time, BOM, Routing
- Standard Odoo รองรับ MRP/Replenishment, Buy/Make, Min/Max, Vendor Lead Time
- Rolling Forecast import และ Forecast-to-Invoice KPI เป็น candidate ที่ต้องออกแบบเพิ่ม

คำถามที่ควรถามทีม:

- Forecast format มาจากลูกค้าแบบใด
- MOQ และ lead time อยู่ที่ product หรือ vendor
- BOM revision control ต้อง strict แค่ไหน
- MRP run ต้อง manual, scheduled หรือ auto ตามรอบ

### ช่วงที่ 10: สรุป Standard vs Pain Point

เวลาแนะนำ: 5-7 นาที

สรุปเป็น 4 กลุ่ม:

- Standard ได้เลย: Sales, Purchase, Inventory, MRP, Quality, Accounting, Barcode, Approval, Fleet บางส่วน
- ต้อง config/master: Analytic BU/Branch, product route, BOM/routing, quality point, location, valuation, budget
- Report/automation candidate: Supplier score, slow/dead stock, cash forecast, forecast accuracy, OEE/OPE, DPPM
- Custom candidate: Budget hard lock, automotive forecast import, variance allocation rule, PPAP/BOM costing template

### ช่วงที่ 11: ปิดการนำเสนอด้วย Next Step

เวลาแนะนำ: 5 นาที

เสนอ action ต่อ:

1. ยืนยัน owner ของแต่ละ swimlane
2. ตรวจ master data ที่ต้อง setup ใน AMS
3. แยก requirement เป็น Standard / Config / Report / Custom
4. ทำ UAT scenario จาก flow แต่ละหน้า
5. ตัดสินใจ custom เฉพาะจุดที่ standard ไม่ตอบโจทย์จริง

## Checklist ก่อนใช้ Present

- เปิดไฟล์ drawio แล้วดูหน้าครบ 10 หน้า
- เริ่ม present จากหน้า `00 วิธีอ่าน Flow`
- ใช้หน้า Overall ก่อนลง module
- ทุกครั้งที่เจอกล่องสีส้ม ให้จดเป็น discussion item
- ทุกขั้นที่กระทบ Stock/Accounting ให้ถามเรื่อง valuation, posting และ owner
- ปิดท้ายด้วย action list ไม่ใช่ปิดด้วย diagram อย่างเดียว
"""


def markdown_to_html(markdown: str) -> str:
    lines = markdown.splitlines()
    out = [
        "<!doctype html><html><head><meta charset=\"utf-8\"><title>AMS Swimlane Thai Presentation Guide</title>",
        "<style>body{font-family:Arial,'Noto Sans Thai',sans-serif;margin:32px;line-height:1.55;color:#111827;max-width:1180px}h1{color:#5B1747}h2{border-bottom:2px solid #E5E7EB;padding-bottom:6px;margin-top:34px}h3{color:#374151;margin-top:28px}table{border-collapse:collapse;width:100%;margin:14px 0}th,td{border:1px solid #CBD5E1;padding:8px;vertical-align:top}th{background:#5B1747;color:#fff}code{background:#F3F4F6;padding:2px 5px;border-radius:4px}li{margin:4px 0}</style>",
        "</head><body>",
    ]
    in_ul = False
    in_table = False
    for line in lines:
        if not line.strip():
            if in_ul:
                out.append("</ul>")
                in_ul = False
            if in_table:
                out.append("</table>")
                in_table = False
            continue
        if line.startswith("# "):
            out.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            out.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("### "):
            out.append(f"<h3>{html.escape(line[4:])}</h3>")
        elif line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if set(cells[0]) <= {"-", ":"}:
                continue
            if not in_table:
                out.append("<table>")
                in_table = True
                tag = "th"
            else:
                tag = "td"
            out.append("<tr>" + "".join(f"<{tag}>{html.escape(c)}</{tag}>" for c in cells) + "</tr>")
        elif line.startswith("- "):
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{html.escape(line[2:])}</li>")
        elif re.match(r"^\d+\. ", line):
            if not in_ul:
                out.append("<ol>")
                in_ul = True
            out.append(f"<li>{html.escape(re.sub(r'^\\d+\\. ', '', line))}</li>")
        else:
            out.append(f"<p>{html.escape(line)}</p>")
    if in_ul:
        out.append("</ul>")
    if in_table:
        out.append("</table>")
    out.append("</body></html>")
    return "\n".join(out)


def main() -> None:
    page_count, pages = translate_drawio()
    GUIDE_MD.write_text(GUIDE, encoding="utf-8")
    GUIDE_HTML.write_text(markdown_to_html(GUIDE), encoding="utf-8")
    index = json.loads(INDEX.read_text(encoding="utf-8")) if INDEX.exists() else {}
    index.update({
        "thai_present_drawio": str(TARGET),
        "thai_present_guide_md": str(GUIDE_MD),
        "thai_present_guide_html": str(GUIDE_HTML),
        "thai_present_pages": pages,
    })
    INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "drawio": str(TARGET),
        "guide_md": str(GUIDE_MD),
        "guide_html": str(GUIDE_HTML),
        "page_count": page_count,
        "pages": pages,
    }, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
