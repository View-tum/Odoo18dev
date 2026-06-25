import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const root = "C:/365_project/TheCool18e/Dev/output/ams_workflow_editable_new";
const sourcePath = `${root}/AMS_Editable_Workflow_Mapping.xlsx`;
const outputPath = `${root}/AMS_Workflow_Mapping_with_Manday.xlsx`;
const previewPath = `${root}/manday_summary_preview.png`;

function text(value) {
  return value == null ? "" : String(value);
}

function estimate(row) {
  const area = text(row[0]);
  const no = text(row[1]);
  const req = text(row[2]);
  const fit = text(row[7] ?? row[3]);
  const pain = text(row[8] ?? row[4]);
  const key = `${fit} ${pain} ${req}`.toLowerCase();
  let category = "Standard / Config";
  let min = 1;
  let max = 2;
  let rec = 1.5;
  let phase = "P1";
  let priority = "Medium";
  let basis = "Standard Odoo configuration and UAT support.";

  if (key.includes("gap") || key.includes("consolidation") || key.includes("external")) {
    category = "Custom / External Design";
    min = 12;
    max = 25;
    rec = 18;
    phase = "P3";
    priority = "High";
    basis = "Standard coverage is not enough; requires solution design, prototype and UAT.";
  } else if (key.includes("config + custom guard") || key.includes("hard lock") || key.includes("constraint")) {
    category = "Config + Custom Guard";
    min = 5;
    max = 10;
    rec = 8;
    phase = "P2";
    priority = "High";
    basis = "Standard setup plus custom validation/approval guard.";
  } else if (key.includes("custom report") || key.includes("dashboard") || key.includes("kpi")) {
    category = "Report / KPI";
    min = 4;
    max = 8;
    rec = 6;
    phase = "P2";
    priority = key.includes("cash") || key.includes("dppm") || key.includes("ope") ? "High" : "Medium";
    basis = "Requires report definition, data source mapping, build and validation.";
  } else if (key.includes("partial")) {
    category = "Partial Standard + Gap";
    min = area.includes("Accounting") || area.includes("Manufacturing") ? 8 : 6;
    max = area.includes("Accounting") || area.includes("Manufacturing") ? 15 : 12;
    rec = area.includes("Accounting") || area.includes("Manufacturing") ? 12 : 9;
    phase = "P2";
    priority = "High";
    basis = "Standard supports base data, but business rule/reporting gap remains.";
  } else if (key.includes("config/report")) {
    category = "Config + Report";
    min = 2;
    max = 5;
    rec = 3.5;
    phase = "P1";
    priority = "Medium";
    basis = "Mostly standard setup; add dashboard/pivot/report layout.";
  } else if (key.includes("config")) {
    category = "Configuration";
    min = 1;
    max = 3;
    rec = 2;
    phase = "P1";
    priority = "Medium";
    basis = "Standard Odoo configuration, master data and validation.";
  } else if (key.includes("standard")) {
    category = "Standard";
    min = 0.5;
    max = 1.5;
    rec = 1;
    phase = "P1";
    priority = "Low";
    basis = "Covered by standard Odoo flow; estimate is setup/demo/UAT only.";
  }

  if (/approval|budget|valuation|cost|wip|dppm|cash|supplier|forecast/i.test(`${req} ${pain}`)) {
    priority = priority === "Low" ? "Medium" : priority;
  }
  if (area.includes("Accounting") || area.includes("Manufacturing")) {
    priority = priority === "Medium" ? "High" : priority;
  }

  return { area, no, req, fit, category, min, max, rec, phase, priority, basis };
}

function groupByArea(estimates) {
  const map = new Map();
  for (const e of estimates) {
    if (!map.has(e.area)) {
      map.set(e.area, {
        area: e.area,
        items: 0,
        standard: 0,
        report: 0,
        custom: 0,
        min: 0,
        max: 0,
        rec: 0,
        high: 0,
      });
    }
    const row = map.get(e.area);
    row.items += 1;
    row.min += e.min;
    row.max += e.max;
    row.rec += e.rec;
    if (e.priority === "High") row.high += 1;
    if (e.category.includes("Custom") || e.category.includes("Gap") || e.category.includes("Guard")) row.custom += e.rec;
    else if (e.category.includes("Report") || e.category.includes("KPI")) row.report += e.rec;
    else row.standard += e.rec;
  }
  return [...map.values()];
}

function setHeader(range) {
  range.format = {
    fill: "#5B1747",
    font: { bold: true, color: "#FFFFFF" },
    wrapText: true,
    borders: { preset: "all", style: "thin", color: "#D9D9D9" },
  };
}

function setBody(range) {
  range.format = {
    wrapText: true,
    verticalAlignment: "top",
    borders: { preset: "all", style: "thin", color: "#E5E7EB" },
  };
}

const blob = await FileBlob.load(sourcePath);
const workbook = await SpreadsheetFile.importXlsx(blob);

const reqSheet = workbook.worksheets.getItem("Requirement Mapping");
const backlogSheet = workbook.worksheets.getItem("Custom Backlog");
const reqValues = reqSheet.getRange("A1:J45").values;
const reqRows = reqValues.slice(1).filter((row) => row.some((v) => v != null && v !== ""));
const reqEstimates = reqRows.map(estimate);

reqSheet.getRange("K1:Q1").values = [[
  "Manday Category",
  "Manday Min",
  "Manday Max",
  "Manday Recommended",
  "Manday Basis",
  "Phase",
  "Priority",
]];
reqSheet.getRange(`K2:Q${reqEstimates.length + 1}`).values = reqEstimates.map((e) => [
  e.category,
  e.min,
  e.max,
  e.rec,
  e.basis,
  e.phase,
  e.priority,
]);
setHeader(reqSheet.getRange("K1:Q1"));
setBody(reqSheet.getRange(`K2:Q${reqEstimates.length + 1}`));
reqSheet.getRange(`L2:N${reqEstimates.length + 1}`).format.numberFormat = "0.0";
reqSheet.getRange("A1:Q1").format = {
  fill: "#5B1747",
  font: { bold: true, color: "#FFFFFF" },
  wrapText: true,
};
reqSheet.freezePanes.freezeRows(1);

const backlogValues = backlogSheet.getRange("A1:E17").values;
const backlogRows = backlogValues.slice(1).filter((row) => row.some((v) => v != null && v !== ""));
const backlogEstimates = backlogRows.map((row) => estimate([row[0], row[1], row[2], null, null, null, null, row[3], row[4]]));
backlogSheet.getRange("F1:L1").values = [[
  "Manday Category",
  "Manday Min",
  "Manday Max",
  "Manday Recommended",
  "Phase",
  "Priority",
  "Estimate Basis",
]];
backlogSheet.getRange(`F2:L${backlogEstimates.length + 1}`).values = backlogEstimates.map((e) => [
  e.category,
  e.min,
  e.max,
  e.rec,
  e.phase,
  e.priority,
  e.basis,
]);
setHeader(backlogSheet.getRange("F1:L1"));
setBody(backlogSheet.getRange(`F2:L${backlogEstimates.length + 1}`));
backlogSheet.getRange(`G2:I${backlogEstimates.length + 1}`).format.numberFormat = "0.0";
backlogSheet.freezePanes.freezeRows(1);

const summary = workbook.worksheets.add("Manday Summary");
summary.showGridLines = false;
const areaRows = groupByArea(reqEstimates);
const total = areaRows.reduce((acc, row) => {
  for (const key of ["items", "standard", "report", "custom", "min", "max", "rec", "high"]) acc[key] += row[key];
  return acc;
}, { items: 0, standard: 0, report: 0, custom: 0, min: 0, max: 0, rec: 0, high: 0 });

summary.getRange("A1:I1").values = [["AMS Workflow Manday Estimate", "", "", "", "", "", "", "", ""]];
summary.getRange("A1:I1").format = {
  fill: "#5B1747",
  font: { bold: true, color: "#FFFFFF", size: 16 },
  horizontalAlignment: "center",
};
summary.getRange("A3:B8").values = [
  ["Estimate type", "Initial workshop estimate"],
  ["Scope", "Business flow mapping, standard/config/report/custom assessment"],
  ["1 Manday", "1 consultant/developer working day"],
  ["Total Requirement Items", total.items],
  ["Total Recommended MD", total.rec],
  ["High Priority Items", total.high],
];
summary.getRange("A3:B8").format = {
  borders: { preset: "all", style: "thin", color: "#D9D9D9" },
  wrapText: true,
};
summary.getRange("A3:A8").format = {
  fill: "#E2E8F0",
  font: { bold: true },
};

summary.getRange("A10:I10").values = [[
  "Area",
  "Items",
  "Standard/Config MD",
  "Report/KPI MD",
  "Custom/Gap MD",
  "MD Min",
  "MD Max",
  "MD Recommended",
  "High Priority",
]];
summary.getRange(`A11:I${areaRows.length + 11}`).values = [
  ...areaRows.map((row) => [
    row.area,
    row.items,
    row.standard,
    row.report,
    row.custom,
    row.min,
    row.max,
    row.rec,
    row.high,
  ]),
  ["TOTAL", total.items, total.standard, total.report, total.custom, total.min, total.max, total.rec, total.high],
];
setHeader(summary.getRange("A10:I10"));
setBody(summary.getRange(`A11:I${areaRows.length + 11}`));
summary.getRange(`C11:H${areaRows.length + 11}`).format.numberFormat = "0.0";
summary.getRange(`A${areaRows.length + 11}:I${areaRows.length + 11}`).format = {
  fill: "#FDE68A",
  font: { bold: true },
  borders: { preset: "all", style: "thin", color: "#D9D9D9" },
};

const assumptions = [
  ["Assumption / วิธีใช้ตัวเลข Manday"],
  ["ตัวเลขนี้เป็น initial estimate สำหรับ planning/workshop ไม่ใช่ fixed quotation"],
  ["Standard/Config รวม setup, master data check, demo และ UAT support ขั้นต้น"],
  ["Report/KPI รวม data source mapping, report build และ validation"],
  ["Custom/Gap รวม solution design, build, unit test, UAT fix ขั้นต้น แต่ไม่รวม external API/data migration ขนาดใหญ่"],
  ["Accounting/Stock related items ต้องผ่าน design review ก่อนเริ่ม custom เพื่อรักษา Stock & Accounting Integrity"],
];
summary.getRange(`A${areaRows.length + 14}:I${areaRows.length + 19}`).values = assumptions.map((row) => [row[0], "", "", "", "", "", "", "", ""]);
summary.getRange(`A${areaRows.length + 14}:I${areaRows.length + 14}`).merge();
summary.getRange(`A${areaRows.length + 14}`).format = {
  fill: "#5B1747",
  font: { bold: true, color: "#FFFFFF" },
};
for (let r = areaRows.length + 15; r <= areaRows.length + 19; r++) {
  summary.getRange(`A${r}:I${r}`).merge();
}
summary.getRange(`A${areaRows.length + 15}:I${areaRows.length + 19}`).format = {
  wrapText: true,
  borders: { preset: "all", style: "thin", color: "#E5E7EB" },
};

const present = workbook.worksheets.add("Present Sequence");
present.showGridLines = false;
present.getRange("A1:F1").values = [["Step", "Page / File", "Time", "Talk Track", "Decision Point", "Output"]];
const sequenceRows = [
  [1, "00_README_START_HERE_TH", "3 min", "เปิด scope, อธิบายว่าเป็น Standard First mapping จาก Excel -> Odoo AMS", "เห็นตรงกันเรื่อง scope", "Audience เข้าใจเป้าหมาย"],
  [2, "01_AMS_SWINLANE_TH_PRESENT.drawio / 00 วิธีอ่าน Flow", "5 min", "อธิบายวิธีอ่าน lane, symbol, color, decision", "ยืนยันวิธีอ่านร่วมกัน", "ทีมไม่ตีความ diagram คนละแบบ"],
  [3, "03 ภาพรวม AMS End-to-End", "10 min", "เล่า flow ใหญ่ Customer -> Sales -> MRP -> Buy/Make -> Stock -> Accounting -> Report", "ยืนยัน end-to-end owner", "เห็นภาพรวมก่อนลง detail"],
  [4, "04 Sales / CRM", "8 min", "RFQ, Quotation, SO, Margin, Customer PO, forecast handoff", "BOM costing/PPAP เป็น standard หรือ custom", "Sales gap list"],
  [5, "05 Procurement", "10 min", "MRP shortage, PR/Approval, RFQ, PO, Blanket, Receipt, Vendor Bill", "Approval/budget/supplier score", "Procurement gap list"],
  [6, "06 Warehouse / Logistics", "8 min", "Receipt, barcode, lot, shelf, min/max, delivery, fleet", "Lot control และ slow/dead stock KPI", "Warehouse setup list"],
  [7, "07 Manufacturing / Quality", "12 min", "BOM, Routing, MO, Work Orders, Barcode, QC, Rework/Scrap", "OPE/DPPM/WIP/cost variance", "Manufacturing gap list"],
  [8, "08 Accounting / Finance", "10 min", "Invoice, Bill, Payment, bank reconcile, budget, valuation", "Budget lock/cash forecast/consolidation", "Finance gap list"],
  [9, "09 Planning / MRP Master Data", "8 min", "Forecast, product master, MOQ, lead time, BOM/routing, buy/make", "Forecast import และ MRP run policy", "Master data action list"],
  [10, "02_AMS_Workflow_Mapping_with_Manday.xlsx", "10 min", "Review Manday Summary และ Custom Backlog", "Priority/phase ของ custom candidate", "Initial effort plan"],
  [11, "Close", "5 min", "สรุป Standard/Config/Report/Custom และ next step สำหรับ UAT", "Approve next workshop action", "Action owner + next meeting"],
];
present.getRange(`A2:F${sequenceRows.length + 1}`).values = sequenceRows;
setHeader(present.getRange("A1:F1"));
setBody(present.getRange(`A2:F${sequenceRows.length + 1}`));
present.freezePanes.freezeRows(1);

for (const sheet of [present, reqSheet, backlogSheet]) {
  const used = sheet.getUsedRange();
  used.format.autofitRows();
  used.format.autofitColumns();
}

summary.getRange("A1:A24").format.columnWidthPx = 310;
summary.getRange("B1:B24").format.columnWidthPx = 230;
summary.getRange("C1:E24").format.columnWidthPx = 125;
summary.getRange("F1:I24").format.columnWidthPx = 115;
summary.getRange("A1:I24").format.wrapText = true;
summary.getRange("A1:I24").format.verticalAlignment = "middle";
summary.getRange("A1:I1").format.rowHeightPx = 34;
summary.getRange("A3:I8").format.rowHeightPx = 28;
summary.getRange("A10:I16").format.rowHeightPx = 30;
summary.getRange("A19:I24").format.rowHeightPx = 34;

const preview = await workbook.render({
  sheetName: "Manday Summary",
  range: "A1:I22",
  scale: 1,
  format: "png",
});
await fs.writeFile(previewPath, new Uint8Array(await preview.arrayBuffer()));

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "formula error scan",
});
console.log(errors.ndjson);

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(JSON.stringify({
  outputPath,
  previewPath,
  requirementRows: reqEstimates.length,
  backlogRows: backlogEstimates.length,
  totalRecommendedManday: total.rec,
}, null, 2));
