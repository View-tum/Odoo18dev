import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const presentDir = "C:\\365_project\\TheCool18e\\Dev\\output\\AMS_PRESENT_CUSTOMER_TH";
const packageDir = "C:\\365_project\\TheCool18e\\Dev\\output\\ams_customer_r001_compare\\AMS_R001_COMPARE_PACKAGE";
const downloadDir = "C:\\Users\\tumsu\\Downloads";
const jsonPath = path.join(presentDir, "04B_TFI_Blueprint_Standard_vs_Custom.json");
const outputName = "04B_TFI_Blueprint_Standard_vs_Custom.xlsx";
const previewName = "04B_TFI_Blueprint_Standard_vs_Custom_xlsx_preview.png";

const data = JSON.parse(await fs.readFile(jsonPath, "utf8"));
const workbook = Workbook.create();

function title(sheet, text, endCol = "H") {
  const range = sheet.getRange(`A1:${endCol}1`);
  range.merge();
  range.values = [[text]];
  range.format = {
    fill: "#5B1747",
    font: { bold: true, color: "#FFFFFF", size: 16 },
    horizontalAlignment: "center",
    verticalAlignment: "middle",
  };
  range.format.rowHeightPx = 36;
}

function header(range, fill = "#0F766E") {
  range.format = {
    fill,
    font: { bold: true, color: "#FFFFFF" },
    wrapText: true,
    verticalAlignment: "middle",
    horizontalAlignment: "center",
  };
  range.format.borders = { preset: "all", style: "thin", color: "#CBD5E1" };
}

function body(range) {
  range.format = { wrapText: true, verticalAlignment: "top" };
  range.format.borders = { preset: "all", style: "thin", color: "#E2E8F0" };
}

function widths(sheet, px) {
  px.forEach((w, i) => {
    const col = String.fromCharCode(65 + i);
    sheet.getRange(`${col}:${col}`).format.columnWidthPx = w;
  });
}

function countRows(category) {
  return data.rows.filter((row) => row.category === category).length;
}

function categoryThai(category) {
  if (category === "standard") return "Standard / Configuration";
  if (category === "custom") return "Custom เพิ่มใน Odoo";
  return "Manual / Reference";
}

function categoryFill(category) {
  if (category === "standard") return "#DCFCE7";
  if (category === "custom") return "#FFEDD5";
  return "#E2E8F0";
}

const summary = workbook.worksheets.add("00 Summary");
title(summary, "TFI Blueprint Mapping: Odoo Standard vs Custom", "H");
const summaryRows = [
  ["หัวข้อ", "สรุป", "ใช้พูดกับลูกค้า"],
  ["Coverage", "เข้า Odoo ได้ครบทุก flow", "ไม่มีจุดที่ต้องทำระบบนอก Odoo; แยกแค่ว่าใช้ standard/config หรือ custom เพิ่มใน Odoo"],
  ["Standard / Configuration", countRows("standard"), "รองรับด้วย Odoo app/config เช่น Sales, Purchase, Inventory, MRP, Quality, Accounting"],
  ["Custom เพิ่มใน Odoo", countRows("custom"), "ทำเฉพาะฟอร์ม/รายงาน/approval/เลขเอกสารที่ลูกค้ามีรูปแบบเฉพาะ"],
  ["Manual / Reference", countRows("external"), "เป็นข้อมูลอ้างอิง ไม่ใช่ function ที่ต้องพัฒนา"],
  ["ไฟล์คู่กัน", "04B_TFI_Blueprint_Standard_vs_Custom.drawio", "เปิด diagram ก่อน แล้วใช้ Excel นี้อธิบายเหตุผลราย block"],
];
summary.getRange(`A3:C${summaryRows.length + 2}`).values = summaryRows;
header(summary.getRange("A3:C3"));
body(summary.getRange(`A4:C${summaryRows.length + 2}`));
summary.getRange("B4:B7").format = { fill: "#F8FAFC", font: { bold: true }, wrapText: true };
summary.getRange("A10:E10").values = [["สีใน Flow", "ความหมาย", "จำนวน Block", "แนวทางทำงาน", "ผลกระทบ"]];
summary.getRange("A11:E13").values = [
  ["เขียว", "Standard / Configuration", countRows("standard"), "เปิดใช้ module + ตั้งค่า master/route/workflow", "Manday ต่ำกว่า custom"],
  ["ส้ม", "Custom เพิ่มใน Odoo", countRows("custom"), "ทำ form/report/approval/template เพิ่ม แต่ยังอยู่ใน Odoo", "ต้อง estimate และ confirm scope"],
  ["เทา", "Manual / Reference", countRows("external"), "ใช้เป็นเอกสารหรือข้อมูลประกอบ", "ไม่ใช่ระบบหลัก"],
];
header(summary.getRange("A10:E10"), "#334155");
body(summary.getRange("A11:E13"));
summary.getRange("A11:E11").format.fill = "#DCFCE7";
summary.getRange("A12:E12").format.fill = "#FFEDD5";
summary.getRange("A13:E13").format.fill = "#E2E8F0";
widths(summary, [180, 260, 560, 460, 310, 24, 24, 24]);
summary.freezePanes.freezeRows(3);
summary.showGridLines = false;

const mapping = workbook.worksheets.add("01 Block Mapping");
title(mapping, "Mapping ราย Block จาก Blueprint", "I");
const rows = [["No.", "Blueprint Step", "แผนก/Lane", "Result", "Odoo Module", "Standard รองรับอะไร", "ทำไมต้อง Custom", "ใช้ Present ยังไง", "Code"]];
data.rows.forEach((row) => {
  rows.push([
    row.no,
    row.label,
    row.lane,
    categoryThai(row.category),
    row.module,
    row.standard_support,
    row.category === "custom" ? row.custom_reason : row.custom_reason || "ไม่ต้อง custom",
    row.present_note,
    row.code,
  ]);
});
mapping.getRange(`A3:I${rows.length + 2}`).values = rows;
header(mapping.getRange("A3:I3"), "#334155");
body(mapping.getRange(`A4:I${rows.length + 2}`));
for (let i = 0; i < data.rows.length; i += 1) {
  const excelRow = i + 4;
  mapping.getRange(`D${excelRow}`).format.fill = categoryFill(data.rows[i].category);
}
widths(mapping, [55, 230, 150, 170, 220, 380, 430, 390, 80]);
mapping.freezePanes.freezeRows(3);
mapping.showGridLines = false;

const custom = workbook.worksheets.add("02 Custom Scope");
title(custom, "รายการที่ต้อง Custom เพิ่มใน Odoo และเหตุผล", "G");
const customRows = [["No.", "Blueprint Step", "Odoo Module", "Standard มีแล้ว", "เหตุผลที่ต้อง Custom", "Deliverable ที่ควรกำหนด", "หมายเหตุ Present"]];
data.rows.filter((row) => row.category === "custom").forEach((row) => {
  customRows.push([
    row.no,
    row.label,
    row.module,
    row.standard_support,
    row.custom_reason,
    "ฟอร์ม / รายงาน / approval / template / sequence เฉพาะตามเอกสารลูกค้า",
    row.present_note,
  ]);
});
custom.getRange(`A3:G${customRows.length + 2}`).values = customRows;
header(custom.getRange("A3:G3"), "#C2410C");
body(custom.getRange(`A4:G${customRows.length + 2}`));
custom.getRange(`A4:G${customRows.length + 2}`).format.fill = "#FFF7ED";
widths(custom, [55, 230, 230, 360, 430, 380, 360]);
custom.freezePanes.freezeRows(3);
custom.showGridLines = false;

const standard = workbook.worksheets.add("03 Standard Support");
title(standard, "รายการที่ Odoo Standard รองรับ", "F");
const standardRows = [["No.", "Blueprint Step", "Odoo Module", "Standard รองรับอะไร", "ต้อง Config อะไร", "พูดกับลูกค้า"]];
data.rows.filter((row) => row.category === "standard").forEach((row) => {
  standardRows.push([
    row.no,
    row.label,
    row.module,
    row.standard_support,
    "ตั้งค่า master data / route / operation type / approval rule / report template ตาม module",
    row.present_note,
  ]);
});
standard.getRange(`A3:F${standardRows.length + 2}`).values = standardRows;
header(standard.getRange("A3:F3"), "#15803D");
body(standard.getRange(`A4:F${standardRows.length + 2}`));
standard.getRange(`A4:F${standardRows.length + 2}`).format.fill = "#F0FDF4";
widths(standard, [55, 230, 230, 430, 430, 390]);
standard.freezePanes.freezeRows(3);
standard.showGridLines = false;

const present = workbook.worksheets.add("04 Present Script");
title(present, "ลำดับการอธิบาย 2 ไฟล์หลักให้ลูกค้า", "F");
const presentRows = [
  ["ลำดับ", "เปิดไฟล์", "พูดอะไร", "จุดที่ต้องชี้", "ผลลัพธ์ที่ต้องให้ลูกค้าเข้าใจ"],
  [1, "04B_TFI_Blueprint_Standard_vs_Custom.drawio", "เริ่มจากภาพรวม blueprint เดิมของลูกค้า แล้วบอกว่าสีเขียวคือ standard/config สีส้มคือ custom เพิ่มใน Odoo", "ชี้ว่าไม่ได้ตัด flow ลูกค้าออก แต่เอาเข้า Odoo ได้ครบ", "ลูกค้าเห็นภาพใหญ่ก่อน"],
  [2, "04B_TFI_Blueprint_Standard_vs_Custom.xlsx / 00 Summary", "สรุปจำนวน block ที่ standard และ custom", "ย้ำว่า custom คืออยู่ใน Odoo ไม่ใช่ระบบนอก", "เข้าใจ scope โดยรวม"],
  [3, "01 Block Mapping", "ไล่ทีละ block ตาม flow", "อธิบาย module เช่น Sales, Purchase, Inventory, MRP, Quality, Accounting", "รู้ว่าแต่ละช่องไปอยู่ตรงไหนใน Odoo"],
  [4, "02 Custom Scope", "คุยเฉพาะรายการส้ม", "ถามลูกค้าว่าต้องการฟอร์ม/เลขเอกสาร/report เหมือนเดิมแค่ไหน", "ปิดความเสี่ยงเรื่อง manday/custom"],
  [5, "03 Standard Support", "ปิดด้วยรายการที่ standard ทำได้", "ย้ำ quick win และจุดที่ setup ได้ทันที", "ลูกค้าเห็นว่าส่วนใหญ่ใช้ standard ได้"],
];
present.getRange(`A3:E${presentRows.length + 2}`).values = presentRows;
header(present.getRange("A3:E3"), "#5B1747");
body(present.getRange(`A4:E${presentRows.length + 2}`));
widths(present, [65, 340, 480, 430, 360]);
present.freezePanes.freezeRows(3);
present.showGridLines = false;

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "formula error scan",
});
const check = await workbook.inspect({
  kind: "table",
  sheetId: "00 Summary",
  range: "A3:E13",
  include: "values,formulas",
  tableMaxRows: 12,
  tableMaxCols: 5,
});
for (const sheetName of ["00 Summary", "01 Block Mapping", "02 Custom Scope", "03 Standard Support", "04 Present Script"]) {
  const preview = await workbook.render({ sheetName, autoCrop: "all", scale: 1, format: "png" });
  await fs.writeFile(path.join(presentDir, `${sheetName.replaceAll(" ", "_")}_04B_mapping_preview.png`), new Uint8Array(await preview.arrayBuffer()));
}
const preview = await workbook.render({ sheetName: "00 Summary", autoCrop: "all", scale: 1, format: "png" });
const bytes = new Uint8Array(await preview.arrayBuffer());
for (const dir of [presentDir, packageDir, downloadDir]) {
  await fs.mkdir(dir, { recursive: true });
  await fs.writeFile(path.join(dir, previewName), bytes);
}
const output = await SpreadsheetFile.exportXlsx(workbook);
for (const dir of [presentDir, packageDir, downloadDir]) {
  await output.save(path.join(dir, outputName));
}
console.log(JSON.stringify({
  output: path.join(downloadDir, outputName),
  present: path.join(presentDir, outputName),
  formulaScan: errors.ndjson,
  inspect: check.ndjson,
  total: data.summary.total,
  standard: data.summary.standard,
  custom: data.summary.custom,
}));
