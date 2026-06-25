import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const packageDir = "C:/365_project/TheCool18e/Dev/output/ams_customer_r001_compare/AMS_R001_COMPARE_PACKAGE";
const sourceXlsx = `${packageDir}/01_AMS_R001_Comparison_Manday_Sequence.xlsx`;
const outputXlsx = `${packageDir}/09_R001_Flow_Mapping_Table.xlsx`;
const outputHtml = `${packageDir}/10_R001_Flow_Mapping_Table.html`;
const previewPng = `${packageDir}/11_R001_Flow_Mapping_Summary_Preview.png`;
const indexPath = `${packageDir}/deliverables_index.json`;

const flowOrder = [
  "01 Overall R001 Blueprint End-to-End",
  "02 Sales + Customer Forecast API",
  "03 Procurement + PR PO Approval",
  "04 RM Warehouse + Customer Supplied Material",
  "05 Engineering + PCC BOM Routing",
  "06 Quality + COA",
  "07 Planning + IS WI MRP",
  "08 Production + MO WO Rework",
  "09 FG Warehouse + Delivery",
  "10 Accounting + Thai Tax Legacy Docs",
];

function str(value) {
  return value == null ? "" : String(value).trim();
}

function num(value) {
  if (typeof value === "number") return value;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function readTable(sheet, range) {
  const values = sheet.getRange(range).values;
  const headers = values[0].map(str);
  return values.slice(1).filter((row) => row.some((cell) => cell !== null && cell !== "")).map((row) => {
    const obj = {};
    headers.forEach((header, index) => {
      obj[header] = row[index];
    });
    return obj;
  });
}

function mapFlow(row) {
  const area = str(row.Area).toLowerCase();
  const text = `${str(row["Customer Requirement"])} ${str(row["Customer Solution"])} ${str(row["Apps / Modules"])} ${str(row["Odoo Standard Explanation"])}`.toLowerCase();

  if (area.includes("account") || text.match(/consolidation|ledger|thai tax|qr|netting|payment|bank|cash|budget|asset|deferred|invoice|vat|audit|financial|finance|capital/)) {
    return "10 Accounting + Thai Tax Legacy Docs";
  }
  if (area.includes("sales") || text.match(/sales|crm|quotation|customer forecast|customer po|so |rma|dppm|bi form|forecast api/)) {
    return "02 Sales + Customer Forecast API";
  }
  if (area.includes("procurement") || text.match(/purchase|supplier|vendor|rfq|po|pr|blanket|approval/)) {
    return "03 Procurement + PR PO Approval";
  }
  if (area.includes("quality") || text.match(/quality|coa|dppm|inspection|spec/)) {
    return "06 Quality + COA";
  }
  if (area.includes("planning") || text.match(/mps|mrp|planning|forecast accuracy|is|wi/)) {
    return "07 Planning + IS WI MRP";
  }
  if (area.includes("production engineering") || text.match(/pcc|bom|routing|work center|engineering|plm|eco/)) {
    return "05 Engineering + PCC BOM Routing";
  }
  if (area.includes("manufacturing") || text.match(/manufacturing|production|mo|wo|oee|ope|wip|variance|scrap|rework|workorder/)) {
    return "08 Production + MO WO Rework";
  }
  if (area.includes("raw material") || text.match(/raw material|rm |customer supplied|owner stock|lot|shelf|barcode|material issue/)) {
    return "04 RM Warehouse + Customer Supplied Material";
  }
  if (area.includes("warehouse") || area.includes("logistic") || text.match(/finished goods|fg|delivery|fleet|driver|shipment|pi/)) {
    return text.match(/delivery|fleet|driver|finished goods|fg|shipment|pi/) ? "09 FG Warehouse + Delivery" : "04 RM Warehouse + Customer Supplied Material";
  }
  return "01 Overall R001 Blueprint End-to-End";
}

function decisionText(row) {
  const status = str(row["Standard vs Custom"]);
  const action = str(row["What to Add / Explain"]);
  const next = str(row["Next Action"]);
  if (/custom|integration|gap|guard|design/i.test(`${status} ${action}`)) {
    return action || next || "ต้องยืนยัน scope/custom rule ใน workshop";
  }
  if (/report|kpi/i.test(`${status} ${action}`)) {
    return action || "ใช้ข้อมูล standard แล้วทำ report/KPI เพิ่มตาม format ลูกค้า";
  }
  return action || next || "ใช้ Odoo standard/config แล้วทำ UAT scenario";
}

function fitGroup(row) {
  const value = `${str(row["Standard vs Custom"])} ${str(row["Our Fit"])} ${str(row["MD Category"])}`.toLowerCase();
  if (value.includes("custom") || value.includes("integration") || value.includes("guard") || value.includes("design") || value.includes("gap")) return "Custom/Integration";
  if (value.includes("report") || value.includes("kpi")) return "Report/KPI";
  return "Standard/Config";
}

function presentText(row, flow) {
  const req = str(row["Customer Requirement"]);
  const standard = str(row["Odoo Standard Explanation"]);
  const decision = decisionText(row);
  return `${flow}: ${req} -> ${standard || "ใช้ Odoo standard ตาม module ที่เกี่ยวข้อง"} / ${decision}`;
}

const sourceWb = await SpreadsheetFile.importXlsx(await FileBlob.load(sourceXlsx));
const r001Rows = readTable(sourceWb.worksheets.getItem("01 R001 vs Our Mapping"), "A1:W45");
const addonRows = readTable(sourceWb.worksheets.getItem("02 Additions from R001 Blueprint"), "A1:W25");
const blueprintRows = readTable(sourceWb.worksheets.getItem("03 Blueprint Flow Mapping"), "A1:F10");

const detailRows = [...r001Rows, ...addonRows].map((row, index) => {
  const flow = mapFlow(row);
  return {
    seq: index + 1,
    source: str(row.Source),
    flow,
    area: str(row.Area),
    no: str(row.No) || "-",
    requirement: str(row["Customer Requirement"]),
    solution: str(row["Customer Solution"]),
    standardExplanation: str(row["Odoo Standard Explanation"]),
    apps: str(row["Apps / Modules"]),
    models: str(row["Models / Objects"]),
    fit: fitGroup(row),
    standardVsCustom: str(row["Standard vs Custom"]),
    addExplain: decisionText(row),
    nextAction: str(row["Next Action"]),
    md: num(row["MD Rec"]),
    phase: str(row.Phase),
    priority: str(row.Priority),
    presentText: presentText(row, flow),
  };
});

const blueprintByFlow = new Map();
for (const row of blueprintRows) {
  const lane = str(row["Blueprint Lane"]);
  const odoo = str(row["Odoo equivalent"]);
  const standard = str(row["Standard support"]);
  const custom = str(row["Custom risk"]);
  const note = str(row["Presentation note"]);
  let flow = "01 Overall R001 Blueprint End-to-End";
  if (lane.includes("ขาย")) flow = "02 Sales + Customer Forecast API";
  else if (lane.includes("ซื้อ")) flow = "03 Procurement + PR PO Approval";
  else if (lane.includes("คลังวัตถุดิบ")) flow = "04 RM Warehouse + Customer Supplied Material";
  else if (lane.includes("วิศวกรรม")) flow = "05 Engineering + PCC BOM Routing";
  else if (lane.includes("คุณภาพ")) flow = "06 Quality + COA";
  else if (lane.includes("วางแผน")) flow = "07 Planning + IS WI MRP";
  else if (lane.includes("คลังสินค้าสำเร็จรูป") || lane.includes("จัดส่ง")) flow = "09 FG Warehouse + Delivery";
  else if (lane.includes("ผลิต")) flow = "08 Production + MO WO Rework";
  else if (lane.includes("การเงิน")) flow = "10 Accounting + Thai Tax Legacy Docs";
  blueprintByFlow.set(flow, { lane, odoo, standard, custom, note });
}

const summaries = flowOrder.map((flow) => {
  const rows = detailRows.filter((row) => row.flow === flow);
  const standardCount = rows.filter((row) => row.fit === "Standard/Config").length;
  const reportCount = rows.filter((row) => row.fit === "Report/KPI").length;
  const customCount = rows.filter((row) => row.fit === "Custom/Integration").length;
  const highCount = rows.filter((row) => row.priority.toLowerCase() === "high").length;
  const md = rows.reduce((sum, row) => sum + row.md, 0);
  const blueprint = blueprintByFlow.get(flow) || {};
  return {
    flow,
    lane: blueprint.lane || "ภาพรวม End-to-End",
    itemCount: rows.length,
    standardCount,
    reportCount,
    customCount,
    md,
    highCount,
    odoo: blueprint.odoo || "End-to-end Odoo process mapping",
    standard: blueprint.standard || "ใช้เป็นหน้าภาพรวมเชื่อมทุก module",
    custom: blueprint.custom || "ใช้ระบุ cross-module decision และ dependency",
    note: blueprint.note || "เริ่มจากภาพรวมก่อนลงราย module",
  };
});

const workbook = Workbook.create();
const summarySheet = workbook.worksheets.add("00 Flow Mapping Summary");
const detailSheet = workbook.worksheets.add("01 Detail Mapping 44+24");
const readSheet = workbook.worksheets.add("02 วิธีอ่าน");

summarySheet.showGridLines = false;
detailSheet.showGridLines = false;
readSheet.showGridLines = false;

const summaryHeaders = [
  "ลำดับ",
  "Flow / Draw.io Page",
  "Lane ลูกค้า",
  "จำนวนข้อ",
  "Standard/Config",
  "Report/KPI",
  "Custom/Integration",
  "MD Rec",
  "High Priority",
  "Odoo Equivalent",
  "Standard รองรับ",
  "จุดที่ต้องเพิ่ม/เสี่ยง custom",
  "วิธีอธิบายตอน present",
];
const summaryData = summaries.map((row, index) => [
  index + 1,
  row.flow,
  row.lane,
  row.itemCount,
  row.standardCount,
  row.reportCount,
  row.customCount,
  row.md,
  row.highCount,
  row.odoo,
  row.standard,
  row.custom,
  row.note,
]);
summarySheet.getRange("A1:M1").values = [summaryHeaders];
summarySheet.getRangeByIndexes(1, 0, summaryData.length, summaryHeaders.length).values = summaryData;

const detailHeaders = [
  "Seq",
  "Source",
  "Flow / Draw.io Page",
  "Area",
  "R001 No/Add-on",
  "Customer Requirement / Add-on Point",
  "Customer Solution",
  "Odoo Standard Explanation",
  "Apps / Modules",
  "Models / Objects",
  "Fit Group",
  "Standard vs Custom",
  "ต้องอธิบาย/ต้องเพิ่ม",
  "Next Action",
  "MD Rec",
  "Phase",
  "Priority",
  "ประโยคสำหรับ present",
];
const detailData = detailRows.map((row) => [
  row.seq,
  row.source,
  row.flow,
  row.area,
  row.no,
  row.requirement,
  row.solution,
  row.standardExplanation,
  row.apps,
  row.models,
  row.fit,
  row.standardVsCustom,
  row.addExplain,
  row.nextAction,
  row.md,
  row.phase,
  row.priority,
  row.presentText,
]);
detailSheet.getRange("A1:R1").values = [detailHeaders];
detailSheet.getRangeByIndexes(1, 0, detailData.length, detailHeaders.length).values = detailData;

readSheet.getRange("A1:F1").values = [["คำถาม", "คำตอบสั้น", "ใช้ไฟล์ไหน", "เปิดตรงไหน", "สิ่งที่ต้องพูด", "หมายเหตุ"]];
readSheet.getRange("A2:F8").values = [
  ["เก็บครบทุกจุดไหม", "Customer request จริงมี 44 ข้อ และมี supporting mapping point อีก 24 จุด", "09_R001_Flow_Mapping_Table.xlsx", "00 Flow Mapping Summary", "แยก 44 customer requests ออกจาก 24 blueprint/add-on points แล้ว map ตาม flow", "ยังต้อง confirm รายละเอียดจริงกับลูกค้า"],
  ["เริ่ม present ตรงไหน", "เริ่ม Dashboard ก่อน", "00_DASHBOARD_AMS_R001_CLIENT_SUMMARY.html", "หน้าแรก", "เราเข้ามา map request เข้า Odoo flow และแยก standard/custom", "ใช้พูดเร็ว 3-5 นาที"],
  ["Manday ใช้ไปกับอะไร", "ดู MD ตาม flow และ fit group", "01_AMS_R001_Comparison_Manday_Sequence.xlsx", "05 Manday Summary", "ตัวเลขเป็น initial estimate ไม่ใช่ fixed quotation", "ใช้จัด P1/P2/P3"],
  ["แต่ละ flow มีอะไร", "ดู summary ตาม Draw.io page", "09_R001_Flow_Mapping_Table.xlsx", "00 Flow Mapping Summary", "ไล่ flow จาก Sales ไป Accounting", "ใช้คู่กับ draw.io"],
  ["แต่ละข้ออยู่ flow ไหน", "ดู detail 44+24 รายการ", "09_R001_Flow_Mapping_Table.xlsx", "01 Detail Mapping 44+24", "มี Odoo standard, ต้องเพิ่ม, MD, phase, priority", "ใช้ตอบ Q&A"],
  ["จุดไหนต้อง custom", "ดูคอลัมน์ Custom/Integration และ ต้องอธิบาย/ต้องเพิ่ม", "09_R001_Flow_Mapping_Table.xlsx", "ทุก sheet", "custom เฉพาะ standard ไม่พอ", "Stock/Accounting ต้อง design review"],
  ["ปิด meeting ด้วยอะไร", "Workshop Questions และ Present Sequence", "01_AMS_R001_Comparison_Manday_Sequence.xlsx", "07 Workshop Questions / 06 Present Sequence", "ขอ sample document/API/report และ lock scope", "ปิดด้วย action items"],
];

function styleSheet(sheet, usedRange, headerRange) {
  sheet.getRange(usedRange).format = {
    font: { color: "#111827", size: 10 },
    wrapText: true,
    verticalAlignment: "top",
    borders: { preset: "all", style: "thin", color: "#CBD5E1" },
  };
  sheet.getRange(headerRange).format = {
    fill: "#5B1747",
    font: { bold: true, color: "#FFFFFF", size: 10 },
    wrapText: true,
    verticalAlignment: "middle",
    horizontalAlignment: "center",
    borders: { preset: "all", style: "thin", color: "#FFFFFF" },
  };
}

styleSheet(summarySheet, `A1:M${summaryData.length + 1}`, "A1:M1");
styleSheet(detailSheet, `A1:R${detailData.length + 1}`, "A1:R1");
styleSheet(readSheet, "A1:F8", "A1:F1");

summarySheet.freezePanes.freezeRows(1);
detailSheet.freezePanes.freezeRows(1);
readSheet.freezePanes.freezeRows(1);

summarySheet.getRange("A:A").format.columnWidthPx = 48;
summarySheet.getRange("B:B").format.columnWidthPx = 230;
summarySheet.getRange("C:C").format.columnWidthPx = 120;
summarySheet.getRange("D:I").format.columnWidthPx = 78;
summarySheet.getRange("J:M").format.columnWidthPx = 230;
detailSheet.getRange("A:A").format.columnWidthPx = 48;
detailSheet.getRange("B:E").format.columnWidthPx = 120;
detailSheet.getRange("F:H").format.columnWidthPx = 260;
detailSheet.getRange("I:J").format.columnWidthPx = 180;
detailSheet.getRange("K:L").format.columnWidthPx = 125;
detailSheet.getRange("M:N").format.columnWidthPx = 260;
detailSheet.getRange("O:Q").format.columnWidthPx = 70;
detailSheet.getRange("R:R").format.columnWidthPx = 360;
readSheet.getRange("A:F").format.columnWidthPx = 210;

for (let row = 1; row <= summaryData.length + 1; row++) summarySheet.getRange(`A${row}:M${row}`).format.rowHeightPx = row === 1 ? 42 : 78;
for (let row = 1; row <= detailData.length + 1; row++) detailSheet.getRange(`A${row}:R${row}`).format.rowHeightPx = row === 1 ? 42 : 96;
for (let row = 1; row <= 8; row++) readSheet.getRange(`A${row}:F${row}`).format.rowHeightPx = row === 1 ? 42 : 72;

summarySheet.tables.add(`A1:M${summaryData.length + 1}`, true, "FlowMappingSummary");
detailSheet.tables.add(`A1:R${detailData.length + 1}`, true, "DetailMapping68Items");
readSheet.tables.add("A1:F8", true, "HowToReadFlowMapping");

const preview = await workbook.render({ sheetName: "00 Flow Mapping Summary", range: `A1:M${summaryData.length + 1}`, scale: 1, format: "png" });
await fs.writeFile(previewPng, new Uint8Array(await preview.arrayBuffer()));
const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(outputXlsx);

const flowRowsHtml = summaries.map((row) => `<tr>
<td>${row.flow}</td>
<td>${row.lane}</td>
<td class="num">${row.itemCount}</td>
<td class="num">${row.standardCount}</td>
<td class="num">${row.reportCount}</td>
<td class="num">${row.customCount}</td>
<td class="num">${row.md}</td>
<td>${row.odoo}</td>
<td>${row.custom}</td>
<td>${row.note}</td>
</tr>`).join("\n");

const flowStandardCustomRowsHtml = summaries.map((row) => `<tr>
<td><strong>${row.flow}</strong><br><span class="muted">${row.lane}</span></td>
<td><strong class="std">${row.standardCount} จุด</strong><br>${row.standard}</td>
<td><strong class="report">${row.reportCount} จุด</strong><br>Report/KPI หรือแบบฟอร์มที่ต้องทำให้ตรงรูปแบบ AMS</td>
<td><strong class="cust">${row.customCount} จุด</strong><br>${row.custom}</td>
<td class="num">${row.md}</td>
</tr>`).join("\n");

const detailRowsHtml = detailRows.map((row) => `<tr>
<td>${row.seq}</td>
<td>${row.flow}</td>
<td>${row.area}</td>
<td>${row.no}</td>
<td>${row.requirement}</td>
<td>${row.standardExplanation}</td>
<td>${row.fit}</td>
<td>${row.addExplain}</td>
<td class="num">${row.md}</td>
<td>${row.phase}</td>
<td>${row.priority}</td>
</tr>`).join("\n");

const html = `<!doctype html>
<html><head><meta charset="utf-8"><title>AMS R001 Flow Mapping Table</title>
<style>
body{font-family:Arial,'Noto Sans Thai',sans-serif;margin:0;background:#f8fafc;color:#111827}
.wrap{max-width:1400px;margin:0 auto;padding:28px}
.hero{background:#5B1747;color:white;padding:20px 24px;border-radius:8px}
h1{margin:0;font-size:26px}h2{color:#5B1747;margin-top:26px}
.note{background:#fff7ed;border:1px solid #fed7aa;border-radius:8px;padding:12px;margin-top:12px}
table{border-collapse:collapse;width:100%;background:white;border:1px solid #cbd5e1;font-size:13px}
th{background:#5B1747;color:white;text-align:left;position:sticky;top:0}
td,th{border:1px solid #cbd5e1;padding:8px;vertical-align:top}
.num{text-align:right;white-space:nowrap}.fit{font-weight:700}.std{color:#166534}.report{color:#7C3AED}.cust{color:#9A3412}.muted{color:#64748b;font-size:12px}
</style></head><body><div class="wrap">
<section class="hero"><h1>AMS R001 Flow Mapping Table</h1><p>Customer request จริงใน R001 มี 44 ข้อ ส่วนอีก 24 จุดคือ supporting mapping points จาก solution note และ blueprint image ไม่ใช่ request เพิ่มของลูกค้า</p></section>
<div class="note"><strong>สรุปคำตอบ:</strong> ตารางนี้แยก 44 customer requests ออกจาก 24 blueprint/add-on mapping points แล้ว map เข้า Draw.io flow เพื่อใช้ตอบว่า Odoo standard รองรับตรงไหน และตรงไหนต้องเพิ่ม รายการที่เป็น API, report format, COA, DPPM/OEE/OPE, budget hard lock, netting, multi-ledger, WIP/valuation ยังต้อง confirm rule/sample กับลูกค้าก่อน final quotation</div>
<h2>1. Flow Standard/Custom Map</h2>
<table><thead><tr><th>Flow</th><th>Standard Odoo ใช้ได้</th><th>Report / KPI</th><th>ต้องทำเพิ่ม / Custom</th><th>MD</th></tr></thead><tbody>${flowStandardCustomRowsHtml}</tbody></table>
<h2>2. Mapping Summary by Flow</h2>
<table><thead><tr><th>Flow</th><th>Lane</th><th>Items</th><th>Std</th><th>Report</th><th>Custom</th><th>MD</th><th>Odoo Equivalent</th><th>Custom Risk</th><th>Present Note</th></tr></thead><tbody>${flowRowsHtml}</tbody></table>
<h2>3. Detail Mapping: 44 Customer Requests + 24 Supporting Points</h2>
<table><thead><tr><th>Seq</th><th>Flow</th><th>Area</th><th>No</th><th>Customer Requirement</th><th>Odoo Standard Explanation</th><th>Fit</th><th>ต้องอธิบาย/ต้องเพิ่ม</th><th>MD</th><th>Phase</th><th>Priority</th></tr></thead><tbody>${detailRowsHtml}</tbody></table>
</div></body></html>`;
await fs.writeFile(outputHtml, html, "utf8");

let index = {};
try {
  index = JSON.parse(await fs.readFile(indexPath, "utf8"));
} catch {
  index = {};
}
Object.assign(index, {
  r001_flow_mapping_table_xlsx: outputXlsx,
  r001_flow_mapping_table_html: outputHtml,
  r001_flow_mapping_summary_preview_png: previewPng,
});
await fs.writeFile(indexPath, JSON.stringify(index, null, 2), "utf8");

console.log(JSON.stringify({
  outputXlsx,
  outputHtml,
  previewPng,
  totalItems: detailRows.length,
  summaryFlows: summaries.length,
}, null, 2));
