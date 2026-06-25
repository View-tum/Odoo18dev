import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const outputDir = "C:/365_project/TheCool18e/Dev/output/aws_painpoint_mapping";
const originalPath = "C:/Users/tumsu/Downloads/Requirement on New System_R001.xlsx";
const currentPath = "C:/Users/tumsu/Desktop/AMS_Present/ams_source_files/02_Require.xlsx";
const filledSourcePath = process.env.FILLED_REQUIRE_PATH || currentPath;
const awsPresentPath = "C:/Users/tumsu/Desktop/AMS_Present/AWS_Present.xlsx";
const renderPath = path.join(outputDir, "02_Require_customer_format_preview.png");

const today = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
const backupPath = path.join(outputDir, `02_Require_before_customer_format_${today}.xlsx`);

function text(value) {
  if (value === null || value === undefined) return "";
  return String(value).trim();
}

function isRequirementRow(no, req) {
  return text(no) !== "" && text(req) !== "" && /^[0-9]+$/.test(text(no));
}

function shortLine(label, value) {
  const v = text(value);
  return v ? `${label}: ${v}` : "";
}

function cleanSolution(value) {
  const raw = text(value).replace(/\r\n/g, "\n");
  if (!raw) return "";
  const stopMarkers = [
    "\nModule:",
    "\nFit:",
    "\nPain Point:",
    "\nEstimate/Priority:",
    "\nManday:",
    "\nPriority:",
  ];
  const cutAt = stopMarkers
    .map((marker) => raw.indexOf(marker))
    .filter((idx) => idx >= 0)
    .sort((a, b) => a - b)[0];
  return (cutAt >= 0 ? raw.slice(0, cutAt) : raw).trim();
}

function buildNote(row, data) {
  const lines = [
    "Note อธิบายสำหรับ Solution",
    "ที่มา: เติมจากไฟล์ AWS_Present.xlsx ที่เรา mapping ไว้กับ Requirement ของ AMS",
    `อ้างอิง Requirement row: ${row}`,
    shortLine("Solution เต็มจากไฟล์ mapping", data.solution),
    shortLine("Module", data.module),
    shortLine("Standard/Custom", data.standardCustom),
    shortLine("Pain Point Mapping", data.painPoint),
    data.md || data.priority ? `Manday/Priority: ${text(data.md) || "-"} MD / ${text(data.priority) || "-"}` : "",
    shortLine("Present Note", data.presentNote),
    "เหตุผล: ไฟล์นี้คงรูปแบบลูกค้าเดิมไว้ เหลือเฉพาะคอลัมน์ Solution และย้ายรายละเอียดอธิบายมาไว้ใน note/comment ของเซลล์แทน",
  ].filter(Boolean);
  return lines.join("\n").slice(0, 6000);
}

await fs.mkdir(outputDir, { recursive: true });
await fs.copyFile(currentPath, backupPath);

const currentInput = await FileBlob.load(filledSourcePath);
const currentWorkbook = await SpreadsheetFile.importXlsx(currentInput);
const currentSheet = currentWorkbook.worksheets.getItemAt(0);
const currentValues = currentSheet.getRange("A1:K120").values;

const solutionByRow = new Map();
for (let i = 0; i < currentValues.length; i += 1) {
  const rowNo = i + 1;
  const row = currentValues[i] || [];
  const no = text(row[0]);
  const req = row[1];
  const solution = row[3];
  if (!isRequirementRow(no, req) || text(solution) === "") continue;
  solutionByRow.set(rowNo, {
    row: rowNo,
    solution,
    linkAws: row[4],
    module: row[5],
    standardCustom: row[6],
    painPoint: row[7],
    md: row[8],
    priority: row[9],
    presentNote: row[10],
  });
}

const originalInput = await FileBlob.load(originalPath);
const outputWorkbook = await SpreadsheetFile.importXlsx(originalInput);
const sheet = outputWorkbook.worksheets.getItemAt(0);
outputWorkbook.comments.setSelf({ displayName: "Codex" });

const originalValues = sheet.getRange("A1:D120").values;
let applied = 0;
let notes = 0;
for (let i = 0; i < originalValues.length; i += 1) {
  const rowNo = i + 1;
  const row = originalValues[i] || [];
  const no = text(row[0]);
  const req = row[1];
  if (!isRequirementRow(no, req)) continue;
  const data = solutionByRow.get(rowNo);
  if (!data) continue;
  const cell = sheet.getRange(`D${rowNo}`);
  cell.values = [[cleanSolution(data.solution)]];
  outputWorkbook.comments.addThread({ cell }, buildNote(rowNo, data));
  applied += 1;
  notes += 1;
}

const solutionRange = sheet.getRange("D1:D120");
solutionRange.format.wrapText = true;
solutionRange.format.columnWidth = 72;
sheet.getRange("A1:D120").format.autofitRows();

const inspect = await outputWorkbook.inspect({
  kind: "table",
  sheetId: sheet.name,
  range: "A1:D70",
  include: "values",
  tableMaxRows: 70,
  tableMaxCols: 4,
  tableMaxCellChars: 80,
});

const errorScan = await outputWorkbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "final formula error scan",
});

const preview = await outputWorkbook.render({
  sheetName: sheet.name,
  range: "A1:D70",
  scale: 1,
  format: "png",
});
await fs.writeFile(renderPath, new Uint8Array(await preview.arrayBuffer()));

const output = await SpreadsheetFile.exportXlsx(outputWorkbook);
await output.save(currentPath);

console.log(JSON.stringify({
  currentPath,
  originalPath,
  filledSourcePath,
  awsPresentPath,
  backupPath,
  renderPath,
  applied,
  notes,
  inspectPreview: inspect.ndjson.split("\n").slice(0, 12).join("\n"),
  errorScan: errorScan.ndjson,
}, null, 2));
