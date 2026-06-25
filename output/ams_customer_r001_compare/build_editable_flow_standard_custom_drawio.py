from pathlib import Path
from xml.sax.saxutils import escape

package_dir = Path(r"C:\365_project\TheCool18e\Dev\output\ams_customer_r001_compare\AMS_R001_COMPARE_PACKAGE")
present_dir = Path(r"C:\365_project\TheCool18e\Dev\output\AMS_PRESENT_CUSTOMER_TH")

outputs = [
    package_dir / "12_Flow_Standard_Custom_Map.drawio",
    present_dir / "03A_Mapping_Standard_Custom_By_Flow.drawio",
]

rows = [
    ("Sales + Forecast", "Sales, CRM, Invoicing, MRP/MPS", "Quotation, Sales Order, Customer PO, Invoice", "Forecast/API import, legacy BI/SP/FA forms"),
    ("Procurement", "Purchase, Approvals, Inventory, Accounting Budget", "PR/RFQ/PO, vendor, blanket agreement, approval", "Auto grouping, supplier score, budget hard lock"),
    ("RM Warehouse", "Inventory, Barcode, Purchase", "Receive, lot, shelf/location, barcode, owner stock", "Customer supplied material report/valuation"),
    ("Engineering", "Manufacturing, PLM, Inventory", "Product, BOM, routing, work center, PLM base", "PCC form, approval/revision, PPAP template"),
    ("Planning", "Manufacturing, MPS/MRP, Inventory", "MPS/MRP, reorder, buy/make, material issue", "IS/WI legacy form, forecast accuracy view"),
    ("Production", "Manufacturing, Shop Floor, Quality, Maintenance", "MO/WO, work order, quality check, scrap/rework base", "OEE/OPE, WIP/variance, exact rework route"),
    ("Quality", "Quality, Manufacturing, Inventory", "Quality point/check/alert", "COA customer format, DPPM dashboard"),
    ("FG + Delivery", "Inventory, Barcode, Sales, Fleet", "FG receipt, delivery order, stock move", "Delivery ticket, driver KPI, non-fulfillment report"),
    ("Accounting", "Accounting, Thai Localization, Spreadsheet, Approvals", "Invoice, payment, bank reconcile, Thai localization, QR base", "Netting, multi-ledger, consolidation, legacy reports"),
]

def cell(cell_id, value, x, y, w, h, style, parent="1"):
    return (
        f'<mxCell id="{cell_id}" value="{escape(value)}" style="{style}" vertex="1" parent="{parent}">'
        f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry" />'
        "</mxCell>"
    )

def make_diagram():
    cells = ['<mxCell id="0" />', '<mxCell id="1" parent="0" />']
    title_style = "rounded=1;whiteSpace=wrap;html=1;fillColor=#5B1747;fontColor=#FFFFFF;strokeColor=#5B1747;fontStyle=1;fontSize=20;align=center;verticalAlign=middle;"
    note_style = "rounded=1;whiteSpace=wrap;html=1;fillColor=#FFF7ED;strokeColor=#FED7AA;fontColor=#111827;fontSize=13;align=left;spacing=12;"
    header_style = "rounded=0;whiteSpace=wrap;html=1;fillColor=#334155;fontColor=#FFFFFF;strokeColor=#334155;fontStyle=1;fontSize=14;align=center;verticalAlign=middle;"
    flow_style = "rounded=1;whiteSpace=wrap;html=1;fillColor=#EAF2FF;strokeColor=#93C5FD;fontColor=#111827;fontStyle=1;fontSize=13;align=center;verticalAlign=middle;"
    standard_style = "rounded=1;whiteSpace=wrap;html=1;fillColor=#ECFDF5;strokeColor=#86EFAC;fontColor=#14532D;fontSize=12;align=left;verticalAlign=top;spacing=10;"
    custom_style = "rounded=1;whiteSpace=wrap;html=1;fillColor=#FFF7ED;strokeColor=#FDBA74;fontColor=#7C2D12;fontSize=12;align=left;verticalAlign=top;spacing=10;"

    cells.append(cell("title", "AMS Flow Mapping: Module / Standard Odoo / ต้องทำเพิ่ม", 40, 30, 1320, 58, title_style))
    cells.append(cell("note", "วิธีอ่าน: ไล่ทีละ Flow จากซ้ายไปขวา ดูก่อนว่าอยู่ใน Odoo module ไหน จากนั้นดูว่าส่วนไหนใช้ standard/config ได้ และส่วนไหนต้องทำรายงานเพิ่ม เชื่อมระบบเพิ่ม หรือ custom เฉพาะ AMS", 40, 100, 1320, 70, note_style))

    x0, y0 = 40, 195
    widths = [200, 300, 390, 390]
    cells.append(cell("h_flow", "Flow", x0, y0, widths[0], 46, header_style))
    cells.append(cell("h_module", "Odoo Module", x0 + widths[0] + 16, y0, widths[1], 46, header_style))
    cells.append(cell("h_standard", "Standard Odoo ใช้ได้", x0 + widths[0] + widths[1] + 32, y0, widths[2], 46, header_style))
    cells.append(cell("h_custom", "ต้องทำเพิ่ม / Custom / Report", x0 + widths[0] + widths[1] + widths[2] + 48, y0, widths[3], 46, header_style))

    row_h = 76
    y = y0 + 58
    module_style = "rounded=1;whiteSpace=wrap;html=1;fillColor=#EEF2FF;strokeColor=#A5B4FC;fontColor=#312E81;fontSize=12;align=left;verticalAlign=top;spacing=10;"
    for idx, (flow, module, standard, custom) in enumerate(rows, start=1):
        cells.append(cell(f"f{idx}", flow, x0, y, widths[0], row_h, flow_style))
        cells.append(cell(f"m{idx}", module, x0 + widths[0] + 16, y, widths[1], row_h, module_style))
        cells.append(cell(f"s{idx}", standard, x0 + widths[0] + widths[1] + 32, y, widths[2], row_h, standard_style))
        cells.append(cell(f"c{idx}", custom, x0 + widths[0] + widths[1] + widths[2] + 48, y, widths[3], row_h, custom_style))
        y += row_h + 12

    close_y = y + 10
    cells.append(cell("close", "ข้อความหลักตอน present: เราใช้ Odoo module มาตรฐานก่อน แล้วทำเพิ่มเฉพาะจุดที่รูปแบบงานของ AMS ต้องการมากกว่า standard โดยเฉพาะจุดที่กระทบ Stock, MRP และ Accounting ต้องยืนยัน rule ก่อน", 40, close_y, 1320, 72, note_style))

    graph = (
        '<mxGraphModel dx="1600" dy="1000" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" '
        'fold="1" page="1" pageScale="1" pageWidth="1420" pageHeight="1160" math="0" shadow="0">'
        "<root>"
        + "".join(cells)
        + "</root></mxGraphModel>"
    )
    return (
        '<mxfile host="app.diagrams.net" modified="2026-06-18T00:00:00.000Z" agent="Codex" version="24.7.17">'
        f'<diagram id="ams-flow-standard-custom" name="Flow Standard Custom Map">{graph}</diagram>'
        "</mxfile>"
    )

content = make_diagram()
for output in outputs:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    print(output)
