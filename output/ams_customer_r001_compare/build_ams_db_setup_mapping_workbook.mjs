import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const presentDir = "C:\\365_project\\TheCool18e\\Dev\\output\\AMS_PRESENT_CUSTOMER_TH";
const packageDir = "C:\\365_project\\TheCool18e\\Dev\\output\\ams_customer_r001_compare\\AMS_R001_COMPARE_PACKAGE";
const downloadDir = "C:\\Users\\tumsu\\Downloads";
const summaryPath = path.join(presentDir, "AMS_DB_SETUP_SUMMARY.json");
const blockMappingPath = path.join(presentDir, "04A_Client_Original_Flow_Standard_vs_Custom.xlsx");
const outputName = "06_หลักฐาน_Setup_DB_AMS_และ_Mapping_Standard_Custom.xlsx";
const previewName = "06_หลักฐาน_Setup_DB_AMS_และ_Mapping_Standard_Custom_preview.png";

const summary = JSON.parse(await fs.readFile(summaryPath, "utf8"));
const sourceBlob = await FileBlob.load(blockMappingPath);
const sourceWorkbook = await SpreadsheetFile.importXlsx(sourceBlob);
const sourceSheet = sourceWorkbook.worksheets.getItemAt(0);
const blockRows = sourceSheet.getUsedRange(true).values;
const blockHeader = blockRows[0];
const blockData = blockRows.slice(1);

const countByResult = blockData.reduce((acc, row) => {
  const result = row[3] || "ไม่ระบุ";
  acc[result] = (acc[result] || 0) + 1;
  return acc;
}, {});

const workbook = Workbook.create();

function setTitle(sheet, title, lastCol = "G") {
  const range = sheet.getRange(`A1:${lastCol}1`);
  range.merge();
  range.values = [[title]];
  range.format = {
    fill: "#5B1747",
    font: { bold: true, color: "#FFFFFF", size: 16 },
    horizontalAlignment: "center",
    verticalAlignment: "middle",
  };
  range.format.rowHeightPx = 34;
}

function styleHeader(range, fill = "#0F766E") {
  range.format = {
    fill,
    font: { bold: true, color: "#FFFFFF" },
    wrapText: true,
    verticalAlignment: "middle",
  };
  range.format.borders = { preset: "all", style: "thin", color: "#CBD5E1" };
}

function styleBody(range) {
  range.format = {
    wrapText: true,
    verticalAlignment: "top",
  };
  range.format.borders = { preset: "all", style: "thin", color: "#E2E8F0" };
}

function setWidths(sheet, widths) {
  widths.forEach((width, index) => {
    const col = String.fromCharCode(65 + index);
    sheet.getRange(`${col}:${col}`).format.columnWidthPx = width;
  });
}

const overview = workbook.worksheets.add("00 สรุป");
setTitle(overview, "AMS Demo DB Setup และ Mapping Standard/Custom", "G");
const overviewRows = [
  ["หัวข้อ", "รายละเอียด"],
  ["Database", summary.database],
  ["URL", `http://localhost:${summary.port}`],
  ["Login", "admin / admin"],
  ["Standard-only", summary.standard_only ? "ใช่: ไม่ติดตั้ง custom module" : "ไม่ใช่: พบ custom module"],
  ["Run Code ล่าสุด", summary.run_code],
  ["Test flow", summary.test_flow.every((row) => row.status === "passed") ? "ผ่านครบทุก step" : "ยังมี step ไม่ผ่าน"],
  ["Product Master", `${summary.records.products} รายการ`],
  ["BOM", `${summary.records.bom_components} components / ${summary.records.bom_operations} operations`],
  ["Quality Point", `${summary.records.quality_points_total} จุด`],
  ["Reordering Rules", `${summary.records.raw_material_orderpoints} จุด`],
];
overview.getRange(`A3:B${overviewRows.length + 2}`).values = overviewRows;
styleHeader(overview.getRange("A3:B3"), "#0F766E");
styleBody(overview.getRange(`A4:B${overviewRows.length + 2}`));
overview.getRange("D3:E6").values = [
  ["ประเภทใน Flow", "จำนวน block"],
  ["Standard Odoo / Configuration", countByResult["Standard Odoo / Configuration"] || 0],
  ["Custom / Report / API / Approval เพิ่ม", countByResult["Custom / Report / API / Approval เพิ่ม"] || 0],
  ["External / Manual Reference", countByResult["External / Manual Reference"] || 0],
];
styleHeader(overview.getRange("D3:E3"), "#334155");
styleBody(overview.getRange("D4:E6"));
overview.getRange("D4:D4").format.fill = "#DCFCE7";
overview.getRange("D5:D5").format.fill = "#FFEDD5";
overview.getRange("D6:D6").format.fill = "#E2E8F0";
setWidths(overview, [190, 430, 24, 300, 120, 24, 24]);
overview.freezePanes.freezeRows(3);
overview.showGridLines = false;

const testFlow = workbook.worksheets.add("01 Test Flow ใน Odoo");
setTitle(testFlow, "เอกสารที่ระบบสร้างและทดสอบผ่านใน Odoo AMS", "F");
const testRows = [["ลำดับ", "Step", "Status", "Record", "Model", "อธิบาย"]];
const explainByStep = {
  "Purchase Order confirmed": "สร้าง PO จาก Supplier ด้วย Odoo Purchase standard",
  "Vendor receipt validated": "รับวัตถุดิบเข้า WH/Stock ด้วย Odoo Inventory standard",
  "Sales Order confirmed": "สร้าง SO จาก Customer ด้วย Odoo Sales standard",
  "Manufacturing Order produced": "ผลิต FG ผ่าน MO/WO, BOM, Routing และ Quality Check standard",
  "Customer delivery validated": "ส่งสินค้า FG ด้วย Delivery Order standard",
  "Customer invoice posted": "ออก Invoice/AR ด้วย Odoo Accounting standard",
};
summary.test_flow.forEach((row, index) => {
  testRows.push([
    index + 1,
    row.step,
    row.status.toUpperCase(),
    row.record || "",
    row.model || "",
    explainByStep[row.step] || "",
  ]);
});
testFlow.getRange(`A3:F${testRows.length + 2}`).values = testRows;
styleHeader(testFlow.getRange("A3:F3"), "#0F766E");
styleBody(testFlow.getRange(`A4:F${testRows.length + 2}`));
setWidths(testFlow, [70, 230, 90, 240, 170, 430]);
testFlow.freezePanes.freezeRows(3);
testFlow.showGridLines = false;

const mapping = workbook.worksheets.add("02 Mapping Block Flow");
setTitle(mapping, "Mapping block ตาม Flow ลูกค้า: Standard Odoo / Custom / External", "G");
const mappingRows = [["ลำดับ", ...blockHeader.slice(1), "ข้อสรุปสำหรับ present"]];
blockData.forEach((row) => {
  const result = row[3];
  let presentNote = "ใช้ standard Odoo/config ได้";
  if (result.includes("Custom")) {
    presentNote = "ต้องตกลง scope custom/report/approval เพิ่ม";
  } else if (result.includes("External")) {
    presentNote = "เป็นเอกสารหรือจุดเชื่อม ไม่ใช่ function หลัก";
  }
  mappingRows.push([row[0], row[1], row[2], row[3], row[4], row[5], presentNote]);
});
mapping.getRange(`A3:G${mappingRows.length + 2}`).values = mappingRows;
styleHeader(mapping.getRange("A3:G3"), "#0F766E");
styleBody(mapping.getRange(`A4:G${mappingRows.length + 2}`));
for (let rowIndex = 4; rowIndex <= mappingRows.length + 2; rowIndex += 1) {
  const result = mapping.getRange(`D${rowIndex}:D${rowIndex}`);
  const value = mappingRows[rowIndex - 3][3];
  if (value.includes("Standard")) result.format.fill = "#DCFCE7";
  if (value.includes("Custom")) result.format.fill = "#FFEDD5";
  if (value.includes("External")) result.format.fill = "#E2E8F0";
}
setWidths(mapping, [60, 230, 180, 250, 210, 520, 300]);
mapping.freezePanes.freezeRows(3);
mapping.showGridLines = false;

const gaps = workbook.worksheets.add("03 จุดที่ต้อง Custom");
setTitle(gaps, "จุดที่ Standard ยังไม่ตอบครบและต้องตัดสินใจ Custom", "D");
const gapRows = [["ลำดับ", "Flow", "Pain Point / Gap", "Standard Position"]];
summary.custom_gaps.forEach((gap, index) => {
  gapRows.push([index + 1, gap.flow, gap.gap, gap.standard_position]);
});
gaps.getRange(`A3:D${gapRows.length + 2}`).values = gapRows;
styleHeader(gaps.getRange("A3:D3"), "#C2410C");
styleBody(gaps.getRange(`A4:D${gapRows.length + 2}`));
setWidths(gaps, [70, 230, 430, 520]);
gaps.freezePanes.freezeRows(3);
gaps.showGridLines = false;

const modules = workbook.worksheets.add("04 Module ที่ Setup");
setTitle(modules, "Odoo Standard Modules ที่ใช้ใน AMS Demo", "C");
const moduleRows = [["Module", "Status", "ใช้ตอบโจทย์ flow"]];
const moduleUse = {
  sale_management: "Quotation, Sale Order",
  purchase: "PO, รับของจาก Supplier",
  stock: "รับเข้า, เบิก, โอน, ส่งสินค้า, Stock RM/FG",
  mrp: "BOM, MO, Work Order, Routing",
  mrp_workorder: "Production operation ทีละ process",
  quality_control: "Quality Check / QC point",
  quality_mrp: "QC บน Manufacturing operation",
  stock_account: "Stock valuation/accounting integration",
  account: "Vendor Bill, Invoice, AR/AP",
  approvals: "ใช้เป็นฐาน approval ได้ แต่ flow เฉพาะยังต้อง config/custom",
  stock_barcode: "รองรับ barcode/QR operation ในอนาคต",
  l10n_th: "รองรับ localization ไทย",
};
Object.entries(summary.records.required_modules).forEach(([module, status]) => {
  moduleRows.push([module, status, moduleUse[module] || ""]);
});
modules.getRange(`A3:C${moduleRows.length + 2}`).values = moduleRows;
styleHeader(modules.getRange("A3:C3"), "#0F766E");
styleBody(modules.getRange(`A4:C${moduleRows.length + 2}`));
setWidths(modules, [210, 120, 560]);
modules.freezePanes.freezeRows(3);
modules.showGridLines = false;

const renderBlob = await workbook.render({ sheetName: "00 สรุป", autoCrop: "all", scale: 1, format: "png" });
const previewBytes = new Uint8Array(await renderBlob.arrayBuffer());
for (const dir of [presentDir, packageDir, downloadDir]) {
  await fs.mkdir(dir, { recursive: true });
  await fs.writeFile(path.join(dir, previewName), previewBytes);
}

const exported = await SpreadsheetFile.exportXlsx(workbook);
for (const dir of [presentDir, packageDir, downloadDir]) {
  await exported.save(path.join(dir, outputName));
}

const imported = await SpreadsheetFile.importXlsx(await FileBlob.load(path.join(presentDir, outputName)));
const inspect = await imported.inspect({
  kind: "sheet,table,match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 20 },
  maxChars: 4000,
});
console.log(inspect.ndjson);
console.log(JSON.stringify({
  output: path.join(presentDir, outputName),
  preview: path.join(presentDir, previewName),
  rows: {
    testFlow: summary.test_flow.length,
    blockMapping: blockData.length,
    gaps: summary.custom_gaps.length,
  },
}));
