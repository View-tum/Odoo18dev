import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const packageDir = "C:/365_project/TheCool18e/Dev/output/ams_customer_r001_compare/AMS_R001_COMPARE_PACKAGE";
const dashboardXlsx = `${packageDir}/00_DASHBOARD_AMS_R001_CLIENT_SUMMARY.xlsx`;
const dashboardPng = `${packageDir}/00_DASHBOARD_AMS_R001_CLIENT_SUMMARY.png`;
const dashboardHtml = `${packageDir}/00_DASHBOARD_AMS_R001_CLIENT_SUMMARY.html`;
const indexPath = `${packageDir}/deliverables_index.json`;

const metrics = {
  customerRequests: 44,
  supportingPoints: 24,
  totalMappingPoints: 68,
  r001Items: 44,
  blueprintAdditions: 24,
  mandayTotal: 358,
  mandayMin: 226.5,
  mandayMax: 493.5,
  highPriority: 36,
  standardConfigMd: 196,
  reportKpiMd: 67,
  customIntegrationMd: 95,
};

const topAreas = [
  ["Accounting & Finance", 117, "Thai Tax, budget, cash forecast, consolidation, payment"],
  ["Sales", 73.5, "CRM, quotation, SO, customer forecast/API"],
  ["Manufacturing", 42, "MRP, work orders, OEE/OPE, DPPM"],
  ["Procurement", 33, "PR/RFQ/PO, approval, supplier evaluation"],
  ["Warehouse & Logistic", 30, "Lot, barcode, shelf, delivery/fleet"],
];

const flowStandardCustom = [
  ["Sales + Forecast", "Quotation, Sales Order, Customer PO, Invoice", "Forecast/API import, legacy BI/SP/FA forms"],
  ["Procurement", "PR/RFQ/PO, vendor, blanket agreement, approval", "Auto grouping, supplier score, budget hard lock"],
  ["RM Warehouse", "Receive, lot, shelf/location, barcode, owner stock", "Customer supplied material report/valuation"],
  ["Engineering", "Product, BOM, routing, work center, PLM base", "PCC form, approval/revision, PPAP template"],
  ["Planning", "MPS/MRP, reorder, buy/make, material issue", "IS/WI legacy form, forecast accuracy view"],
  ["Production", "MO/WO, work order, quality check, scrap/rework base", "OEE/OPE, WIP/variance, exact rework route"],
  ["Quality", "Quality point/check/alert", "COA customer format, DPPM dashboard"],
  ["FG + Delivery", "FG receipt, delivery order, stock move", "Delivery ticket, driver KPI, non-fulfillment report"],
  ["Accounting", "Invoice, payment, bank reconcile, Thai localization, QR base", "Netting, multi-ledger, consolidation, legacy reports"],
];

function topLeft(address) {
  return address.split(":")[0];
}

function panel(sheet, address, value, fill = "#FFFFFF", fontColor = "#111827", fontSize = 11, bold = false) {
  const range = sheet.getRange(address);
  try {
    range.merge();
  } catch {}
  sheet.getRange(topLeft(address)).values = [[value]];
  range.format = {
    fill,
    font: { bold, color: fontColor, size: fontSize },
    wrapText: true,
    verticalAlignment: "top",
    horizontalAlignment: "left",
    borders: { preset: "all", style: "thin", color: "#CBD5E1" },
  };
}

function card(sheet, address, title, number, note, fill = "#EAF2FF") {
  const value = `${title}\n${number}\n${note}`;
  panel(sheet, address, value, fill, "#111827", 12, false);
}

const workbook = Workbook.create();
const sheet = workbook.worksheets.add("Client Dashboard");
sheet.showGridLines = false;

for (const col of ["A", "B", "C", "D", "E", "F", "G", "H"]) {
  sheet.getRange(`${col}1:${col}42`).format.columnWidthPx = 150;
}
for (let row = 1; row <= 42; row++) {
  sheet.getRange(`A${row}:H${row}`).format.rowHeightPx = 26;
}
sheet.getRange("A1:H1").format.rowHeightPx = 36;
sheet.getRange("A2:H2").format.rowHeightPx = 28;

panel(
  sheet,
  "A1:H1",
  "AMS R001 Dashboard: เราเข้ามาช่วยให้ AMS ทำงานได้ง่ายขึ้นอย่างไร",
  "#5B1747",
  "#FFFFFF",
  16,
  true,
);
panel(
  sheet,
  "A2:H2",
  "เริ่มจากหน้านี้ -> Manday -> Workflow / Business Flow",
  "#7C285F",
  "#FFFFFF",
  12,
  true,
);

card(sheet, "A4:B7", "Customer R001 requests", metrics.customerRequests, "เลข 44 คือ request ลูกค้าจริง");
card(sheet, "C4:D7", "Standard / Config MD", metrics.standardConfigMd, "ใช้ Odoo standard ก่อน");
card(sheet, "E4:F7", "Report / KPI MD", metrics.reportKpiMd, "COA, DPPM, OEE/OPE, dashboards");
card(sheet, "G4:H7", "Custom / Integration MD", metrics.customIntegrationMd, "API, hard lock, netting, multi-ledger", "#FCE4D6");

panel(sheet, "A9:D9", "เราเข้ามาทำอะไรให้ลูกค้า", "#5B1747", "#FFFFFF", 13, true);
panel(
  sheet,
  "A10:D17",
  [
    "1. แปลง R001 + Blueprint ให้เป็น Odoo flow ที่อ่านง่าย",
    "2. แยก 44 customer requests ออกจาก 24 blueprint/add-on mapping points",
    "3. ชี้จุดที่ Standard ไม่มี ต้องเป็น Report / Integration / Custom",
    "4. ทำ Manday ให้เห็นว่า effort ใช้ไปกับอะไร",
    "5. เตรียม workflow/business flow สำหรับ workshop และ UAT",
    "",
    "ผลลัพธ์: ลูกค้าเข้าใจเร็วขึ้น ลดการคุยวน และรู้ว่าต้องตัดสินใจตรงไหน",
  ].join("\n"),
  "#FFFFFF",
);

panel(sheet, "E9:H9", "Odoo Standard ที่ช่วยให้ทำงานง่ายขึ้น", "#5B1747", "#FFFFFF", 13, true);
panel(
  sheet,
  "E10:H17",
  [
    "Sales/CRM: Lead, Quotation, SO, Customer PO Ref, Margin",
    "Purchase: RFQ/PO, Blanket Agreement, Approval",
    "Inventory: Lot, Shelf/Location, Barcode, Reordering Rule",
    "MRP/Quality: BOM, Routing, MO/WO, Quality Check",
    "Accounting: Invoice, Bank Reconcile, Thai Localization, QR base",
    "Reporting: Spreadsheet dashboard เป็นฐานสำหรับ KPI/management view",
  ].join("\n"),
  "#F8FAFC",
);

panel(sheet, "A19:D19", "จุดที่ Odoo ไม่มีครบ ต้องเพิ่ม", "#9A3412", "#FFFFFF", 13, true);
panel(
  sheet,
  "A20:D28",
  [
    "Integration: Customer Forecast/API, legacy data migration",
    "Report/KPI: COA, DPPM, OEE/OPE, slow/dead stock, BI form",
    "Control: Budget hard lock, approval suggestion, supplier score",
    "Accounting design: Consolidation, netting payment, multi-ledger, WIP/variance",
    "Legacy docs: SP, FA, IMR, PCC, IS, WI, PI, IV, BI, PD, RR, PS, RE",
    "",
    "ต้องตัดสินใจ: อะไรอยู่ P1 และอะไรเป็น future phase",
  ].join("\n"),
  "#FFF7ED",
);

panel(sheet, "E19:H19", "Manday ใช้ไปกับอะไร", "#5B1747", "#FFFFFF", 13, true);
panel(
  sheet,
  "E20:H28",
  [
    `Standard/Config: ${metrics.standardConfigMd} MD - setup module, master data, UAT standard flow`,
    `Report/KPI: ${metrics.reportKpiMd} MD - COA, dashboard, DPPM, OEE/OPE`,
    `Custom/Integration: ${metrics.customIntegrationMd} MD - API/import, guard, accounting design`,
    `Total Recommended: ${metrics.mandayTotal} MD`,
    `Scope basis: 44 customer requests + 24 supporting mapping points`,
    `Range: ${metrics.mandayMin}-${metrics.mandayMax} MD`,
    `High priority: ${metrics.highPriority} items`,
    "",
    "หมายเหตุ: initial estimate สำหรับ planning/workshop ยังไม่ใช่ fixed quotation",
  ].join("\n"),
  "#FFFFFF",
);

panel(sheet, "A30:H30", "ลำดับ Present ที่แนะนำ", "#334155", "#FFFFFF", 13, true);
panel(
  sheet,
  "A31:H34",
  "1. Dashboard: สรุปว่าเราช่วยอะไร -> 2. Manday: effort ใช้กับอะไร -> 3. Workflow: ไล่ business flow ราย module -> 4. Decision: lock scope และคำถามลูกค้า\n\nKey message: Standard first, custom only when needed. งานที่กระทบ Stock/Accounting ต้อง design review ก่อน custom.",
  "#F8FAFC",
);

panel(sheet, "A36:H36", "Top Manday Areas", "#5B1747", "#FFFFFF", 13, true);
panel(
  sheet,
  "A37:H41",
  topAreas.map(([area, md, note], index) => `${index + 1}. ${area}: ${md} MD - ${note}`).join("\n"),
  "#FFFFFF",
  "#111827",
  11,
  false,
);

const preview = await workbook.render({ sheetName: "Client Dashboard", autoCrop: "all", scale: 1, format: "png" });
await fs.writeFile(dashboardPng, new Uint8Array(await preview.arrayBuffer()));
const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(dashboardXlsx);

const html = `<!doctype html>
<html><head><meta charset="utf-8"><title>AMS R001 Client Dashboard</title>
<style>
body{font-family:Arial,'Noto Sans Thai',sans-serif;margin:0;background:#f8fafc;color:#111827}
.wrap{max-width:1180px;margin:0 auto;padding:28px}.hero{background:#5B1747;color:white;padding:22px 26px;border-radius:8px}
.hero h1{margin:0;font-size:28px}.hero p{margin:8px 0 0;color:#FDEFF8}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:18px 0}
.card{background:white;border:1px solid #e5e7eb;border-radius:8px;padding:14px;min-height:92px}.card strong{display:block;color:#475569;font-size:13px}
.num{font-size:32px;font-weight:700;color:#5B1747;margin:6px 0}.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.panel{background:white;border:1px solid #e5e7eb;border-radius:8px;padding:16px}
.panel h2{font-size:17px;margin:0 0 12px;color:#5B1747}ul{margin:0;padding-left:20px}li{margin:7px 0}.orange h2{color:#9A3412}
.step{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.step div{background:#eef2ff;border:1px solid #c7d2fe;border-radius:8px;padding:12px}.footer{margin-top:14px;background:#111827;color:white;border-radius:8px;padding:14px}
.flowmap{width:100%;border-collapse:collapse;background:white;font-size:13px}.flowmap th{background:#5B1747;color:white;text-align:left}.flowmap td,.flowmap th{border:1px solid #e5e7eb;padding:9px;vertical-align:top}.std{color:#166534;font-weight:700}.cust{color:#9A3412;font-weight:700}
</style></head>
<body><div class="wrap">
<section class="hero"><h1>AMS R001 Dashboard: เราเข้ามาช่วยอะไร</h1><p>สรุปให้ลูกค้าเข้าใจเร็ว: map requirement เข้า Odoo, แยก Standard vs Custom, ประเมิน Manday และเตรียม Workflow/UAT</p></section>
<section class="cards">
<div class="card"><strong>Customer R001 requests</strong><div class="num">${metrics.customerRequests}</div><span>เลข 44 คือ request ลูกค้าจริง</span></div>
<div class="card"><strong>Standard/Config MD</strong><div class="num">${metrics.standardConfigMd}</div><span>ใช้ Odoo standard ก่อน</span></div>
<div class="card"><strong>Report/KPI MD</strong><div class="num">${metrics.reportKpiMd}</div><span>COA, DPPM, OEE/OPE, dashboards</span></div>
<div class="card"><strong>Custom/Integration MD</strong><div class="num">${metrics.customIntegrationMd}</div><span>API/import, guards, accounting design</span></div>
</section>
<section class="grid">
<div class="panel"><h2>เราเข้ามาทำอะไร</h2><ul><li>แปลง R001 + Blueprint เป็น Odoo flow ที่อ่านง่าย</li><li>แยก 44 customer requests ออกจาก 24 blueprint/add-on mapping points</li><li>ชี้ว่าอะไรใช้ Standard/Config ได้</li><li>แยกว่าอะไรต้อง Report / Integration / Custom</li><li>ทำ Manday เพื่อให้เห็น effort ใช้ไปกับอะไร</li><li>เตรียม workflow/business flow สำหรับ workshop และ UAT</li></ul></div>
<div class="panel"><h2>Odoo Standard ช่วยตรงไหน</h2><ul><li>Sales/CRM: RFQ, Quotation, SO, Customer PO</li><li>Purchase: RFQ/PO, Blanket, Approval</li><li>Inventory: Lot, Shelf, Barcode, Reorder</li><li>MRP/Quality: BOM, Routing, MO/WO, QC</li><li>Accounting: Invoice, Bank, Thai localization, QR base</li></ul></div>
<div class="panel orange"><h2>จุดที่ต้องเพิ่ม</h2><ul><li>Customer Forecast/API และ legacy data migration</li><li>COA, DPPM, OEE/OPE, BI และ KPI dashboards</li><li>Budget hard lock, supplier score, approval suggestion</li><li>Consolidation, netting payment, multi-ledger, WIP/variance</li><li>Legacy document codes: SP, FA, IMR, PCC, IS, WI, PI, IV, BI, PD, RR, PS, RE</li></ul></div>
<div class="panel"><h2>Manday ใช้ไปกับอะไร</h2><ul><li>Standard/Config: ${metrics.standardConfigMd} MD</li><li>Report/KPI: ${metrics.reportKpiMd} MD</li><li>Custom/Integration: ${metrics.customIntegrationMd} MD</li><li>Total Recommended: ${metrics.mandayTotal} MD</li><li>Basis: 44 customer requests + 24 supporting mapping points</li><li>Range: ${metrics.mandayMin}-${metrics.mandayMax} MD, ต้อง scope lock ก่อน quotation</li></ul></div>
</section>
<section class="panel" style="margin-top:14px"><h2>Mapping ไปที่ Flow: ตรงไหน Standard / ตรงไหนต้องเพิ่ม</h2>
<table class="flowmap"><thead><tr><th>Flow</th><th><span class="std">Standard Odoo ใช้ได้</span></th><th><span class="cust">ต้องทำเพิ่ม / Custom / Report</span></th></tr></thead><tbody>
${flowStandardCustom.map(([flow, standard, custom]) => `<tr><td><strong>${flow}</strong></td><td>${standard}</td><td>${custom}</td></tr>`).join("")}
</tbody></table>
<p style="margin:10px 0 0;color:#475569">ใช้ตารางนี้อธิบายลูกค้าแบบง่าย: เราเริ่มจาก standard ก่อน แล้วทำเพิ่มเฉพาะจุดที่รูปแบบงานของ AMS ต้องการมากกว่า standard.</p></section>
<section class="panel" style="margin-top:14px"><h2>ลำดับ Present ที่แนะนำ</h2><div class="step"><div><strong>1. Dashboard</strong><br>เข้าใจเร็วว่าเราช่วยอะไร</div><div><strong>2. Manday</strong><br>ดู effort ใช้กับอะไร</div><div><strong>3. Workflow</strong><br>ไล่ business flow ราย module</div><div><strong>4. Decision</strong><br>lock scope และคำถามลูกค้า</div></div></section>
<section class="footer">Key message: Standard first, custom only when needed. งานที่กระทบ Stock/Accounting ต้อง design review ก่อน custom.</section>
</div></body></html>`;

await fs.writeFile(dashboardHtml, html, "utf8");

let index = {};
try {
  index = JSON.parse(await fs.readFile(indexPath, "utf8"));
} catch {
  index = {};
}
Object.assign(index, {
  client_dashboard_xlsx: dashboardXlsx,
  client_dashboard_png: dashboardPng,
  client_dashboard_html: dashboardHtml,
});
await fs.writeFile(indexPath, JSON.stringify(index, null, 2), "utf8");
console.log(JSON.stringify({ dashboardXlsx, dashboardPng, dashboardHtml }, null, 2));
