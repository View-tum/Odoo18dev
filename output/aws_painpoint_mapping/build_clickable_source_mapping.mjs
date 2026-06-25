import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const mode = process.argv[2] || "inspect";

const baseWorkbookPath = "C:/365_project/TheCool18e/Dev/output/AMS_PRESENT_CUSTOMER_TH/AWS_PainPoint_Reference_Package/AWS_Present_All_PainPoint_Mapped_With_References.xlsx";
const r001Path = "C:/Users/tumsu/Downloads/Requirement on New System_R001.xlsx";
const amsWorkflowPath = "C:/Users/tumsu/Downloads/AMS_Workflow ERP.xlsx";
const blueprintPath = "C:/Users/tumsu/Downloads/S__51593240.jpg";
const requestMappingPath = "C:/365_project/TheCool18e/Dev/output/AMS_PRESENT_CUSTOMER_TH/03_Mapping_44_Request_กับ_Flow.xlsx";
const outputDir = "C:/365_project/TheCool18e/Dev/output/AMS_PRESENT_CUSTOMER_TH/AMS_Clickable_AMS_Source_Mapping";
const sourceDir = path.join(outputDir, "ams_source_files");
const outputPath = path.join(outputDir, "AWS_Present_All_Clickable_AMS_Source_Mapping.xlsx");
const downloadCopyPath = "C:/Users/tumsu/Downloads/AWS_Present_All_Clickable_AMS_Source_Mapping.xlsx";

const sourceFiles = [
  {
    source: amsWorkflowPath,
    fileName: "01_AMS_Workflow_ERP.xlsx",
    title: "AMS Workflow ERP.xlsx",
    type: "Excel ลูกค้า",
    use: "Business flow / workflow เดิมของ AMS",
  },
  {
    source: r001Path,
    fileName: "02_Requirement_on_New_System_R001.xlsx",
    title: "Requirement on New System_R001.xlsx",
    type: "Excel ลูกค้า",
    use: "Requirement R001 จำนวน 44 ข้อ",
  },
  {
    source: blueprintPath,
    fileName: "03_TFI_business_blueprint_22042024.jpg",
    title: "TFI business blueprint 22/04/2024",
    type: "รูปภาพลูกค้า",
    use: "Blueprint flow ภาพรวมจากลูกค้า",
  },
];

const painPointLinkRows = [
  { row: 9, files: "R001 + AMS Workflow + Blueprint", point: "R001 Sales 1-2 / Flow ฝ่ายขาย / RFQ-Quotation-SO", r001Row: 25, note: "ใช้ชี้ว่า RFQ, Drawing, Quotation และ SO มีหลายจุดก่อนเป็น order จริง" },
  { row: 10, files: "R001 + Blueprint", point: "R001 Sales 1, Accounting Cost 8-10 / BOM Option -> Run Cost", r001Row: 25, note: "ใช้ชี้ว่าต้องคิด cost ก่อน quote และต้องเชื่อม BOM/route/cost" },
  { row: 11, files: "R001 + AMS Workflow + Blueprint", point: "R001 Sales 2,6 / Manufacturing 1 / SO-Forecast-MRP", r001Row: 26, note: "ใช้ยืนยันว่า forecast, customer PO, SO และแผนผลิตต้องเชื่อมกัน" },
  { row: 12, files: "R001 + AMS Workflow + Blueprint", point: "R001 Procurement 5-6 / Warehouse 4-5 / PR-PO-RM shortage", r001Row: 41, note: "ใช้ยืนยันว่าปัญหาวัตถุดิบขาดกระทบ PR/PO และวันส่งของ" },
  { row: 13, files: "R001 + AMS Workflow + Blueprint", point: "R001 Manufacturing 2-3 / WO-Production status", r001Row: 57, note: "ใช้ยืนยันว่าฝ่ายขายต้องเห็นสถานะผลิตแบบ real-time จาก WO/MO" },
  { row: 14, files: "R001 + AMS Workflow + Blueprint", point: "R001 Warehouse 1,3 / Manufacturing 8 / Lot-Barcode tracking", r001Row: 47, note: "ใช้ชี้ว่าการตาม lot/QR/Barcode เกิดจาก flow stock และ production จริง" },
  { row: 15, files: "R001 + Blueprint", point: "R001 Manufacturing 9 / QC-DPPM-COA", r001Row: 64, note: "ใช้ชี้ว่า QC ต้องเชื่อมกับ production และทำ DPPM/COA ตามรูปแบบ AMS" },
  { row: 16, files: "R001 + Blueprint", point: "R001 Sales 3 / Warehouse 6 / Delivery performance", r001Row: 27, note: "ใช้ยืนยัน KPI ส่งช้า/ส่งไม่ครบจาก request vs delivery จริง" },
  { row: 17, files: "R001 + Blueprint", point: "R001 Accounting 4,11 / Invoice-AR-Payment-Bank", r001Row: 9, note: "ใช้ชี้ว่าบัญชีต้องเชื่อม invoice, payment และ bank reconciliation" },
  { row: 18, files: "R001 + AMS Workflow", point: "R001 Accounting 1-2 / Sales 4-5 / BU-Branch reporting", r001Row: 6, note: "ใช้ยืนยันว่ารายงานต้องแยก BU/Branch/Customer/Product ตั้งแต่ต้นทาง" },
  { row: 19, files: "R001 + AMS Workflow", point: "R001 Accounting 6-7 / Procurement 6 / Budget-Approval", r001Row: 11, note: "ใช้ชี้ว่า budget/approval เป็น requirement ลูกค้า ไม่ใช่ scope ที่คิดเพิ่มเอง" },
  { row: 20, files: "R001 + AMS Workflow + Blueprint", point: "R001 Accounting 8-10 / Manufacturing 2,5 / Cost-WIP-Variance", r001Row: 13, note: "ใช้ยืนยันว่า cost variance/WIP ต้องเชื่อม stock valuation และ accounting" },
];

async function importWorkbook(filePath) {
  const blob = await FileBlob.load(filePath);
  return SpreadsheetFile.importXlsx(blob);
}

async function inspectWorkbook(label, filePath) {
  console.log(`=== ${label}: ${filePath} ===`);
  const wb = await importWorkbook(filePath);
  const summary = await wb.inspect({
    kind: "workbook,sheet,table",
    maxChars: 18000,
    tableMaxRows: 12,
    tableMaxCols: 14,
    tableMaxCellChars: 180,
  });
  console.log(summary.ndjson);
  return wb;
}

async function mainInspect() {
  const base = await inspectWorkbook("BASE", baseWorkbookPath);
  await inspectWorkbook("R001", r001Path);
  await inspectWorkbook("REQUEST_MAPPING_44", requestMappingPath);
  await inspectWorkbook("AMS_WORKFLOW", amsWorkflowPath);
  console.log("=== HYPERLINK HELP ===");
  console.log(base.help("fx.HYPERLINK", { include: "index,examples,notes", maxChars: 3000 }).ndjson);
}

async function hyperlinkHelp() {
  const wb = await importWorkbook(baseWorkbookPath);
  console.log(wb.help("*", {
    search: "hyperlink|link",
    include: "index,examples,notes",
    maxChars: 12000,
  }).ndjson);
}

async function inspectSourceDetails() {
  for (const [label, filePath] of [
    ["R001", r001Path],
    ["REQUEST_MAPPING_44", requestMappingPath],
    ["BASE", baseWorkbookPath],
  ]) {
    console.log(`=== ${label} SHEETS ===`);
    const wb = await importWorkbook(filePath);
    const sheets = await wb.inspect({
      kind: "sheet",
      include: "id,name",
      maxChars: 6000,
    });
    console.log(sheets.ndjson);

    for (const sheetName of ["Requirement", "REQUIREMENT", "Sheet1", "03_Mapping_44_Request_กับ_Flow", "Mapping 44 Request", "Pain Point Mapping"]) {
      try {
        console.log(`=== ${label} ${sheetName} A1:N80 ===`);
        const region = await wb.inspect({
          kind: "region",
          sheetId: sheetName,
          range: "A1:N80",
          maxChars: 20000,
          tableMaxRows: 80,
          tableMaxCols: 14,
          tableMaxCellChars: 160,
        });
        console.log(region.ndjson);
      } catch {
      }
    }
  }
}

async function sheetsOnly() {
  for (const [label, filePath] of [
    ["BASE", baseWorkbookPath],
    ["R001", r001Path],
    ["REQUEST_MAPPING_44", requestMappingPath],
    ["AMS_WORKFLOW", amsWorkflowPath],
  ]) {
    const wb = await importWorkbook(filePath);
    const sheets = await wb.inspect({
      kind: "sheet",
      include: "id,name",
      maxChars: 4000,
    });
    console.log(`=== ${label} ===`);
    console.log(sheets.ndjson);
  }
}

async function outputSheetsOnly() {
  const wb = await importWorkbook(outputPath);
  const sheets = await wb.inspect({
    kind: "sheet",
    include: "id,name",
    maxChars: 5000,
  });
  console.log(sheets.ndjson);
  const req = await wb.inspect({
    kind: "region",
    sheetId: "06 R001 Requirement Links",
    range: "A1:R12",
    maxChars: 16000,
    tableMaxRows: 12,
    tableMaxCols: 18,
    tableMaxCellChars: 140,
  });
  console.log(req.ndjson);
}

async function renderOutput() {
  const wb = await importWorkbook(outputPath);
  const previews = [
    ["Pain Point Mapping", "A1:P20", "pain_point_clickable_source_native.png"],
    ["05 Reference Files", "A1:G10", "ams_source_files_only_native.png"],
    ["06 R001 Requirement Links", "A1:R28", "r001_requirement_links_native.png"],
  ];
  for (const [sheetName, range, fileName] of previews) {
    const preview = await wb.render({ sheetName, range, scale: 1, format: "png" });
    await fs.writeFile(path.join(outputDir, fileName), new Uint8Array(await preview.arrayBuffer()));
    console.log(path.join(outputDir, fileName));
  }
}

async function inspectMappingDetail() {
  const mapping = await importWorkbook(requestMappingPath);
  const detail = await mapping.inspect({
    kind: "region",
    sheetId: "01 Detail Mapping 44+24",
    range: "A1:R75",
    maxChars: 50000,
    tableMaxRows: 75,
    tableMaxCols: 18,
    tableMaxCellChars: 200,
  });
  console.log(detail.ndjson);
}

function styleTitle(range) {
  range.format = {
    fill: "#6B0F3F",
    font: { bold: true, color: "#FFFFFF", size: 15 },
    horizontalAlignment: "center",
    verticalAlignment: "middle",
    borders: { preset: "outside", style: "thin", color: "#6B0F3F" },
  };
}

function styleHeader(range) {
  range.format = {
    fill: "#6B0F3F",
    font: { bold: true, color: "#FFFFFF" },
    wrapText: true,
    horizontalAlignment: "center",
    verticalAlignment: "middle",
    borders: { preset: "all", style: "thin", color: "#FFFFFF" },
  };
}

function styleBody(range) {
  range.format = {
    wrapText: true,
    verticalAlignment: "top",
    borders: { preset: "all", style: "thin", color: "#CBD5E1" },
  };
}

function moduleKey(value) {
  const text = String(value || "").toLowerCase();
  if (text.includes("account")) return "accounting";
  if (text.includes("sale")) return "sales";
  if (text.includes("procure")) return "procurement";
  if (text.includes("warehouse")) return "warehouse";
  if (text.includes("manufact")) return "manufacturing";
  return text.trim();
}

function formulaText(value) {
  return String(value).replaceAll('"', '""');
}

function r001Link(rowNumber, label = null) {
  const friendly = label || `เปิด R001 แถว ${rowNumber}`;
  return `=HYPERLINK("[ams_source_files/02_Requirement_on_New_System_R001.xlsx]Requirement!A${rowNumber}","${formulaText(friendly)}")`;
}

function amsWorkflowLink(label = "เปิด AMS Workflow") {
  return `=HYPERLINK("[ams_source_files/01_AMS_Workflow_ERP.xlsx]'Follow on Requirement'!A1","${formulaText(label)}")`;
}

function blueprintLink(label = "เปิด Blueprint") {
  return `=HYPERLINK("ams_source_files/03_TFI_business_blueprint_22042024.jpg","${formulaText(label)}")`;
}

function painPointForRequirement(area, no, requirement) {
  const module = moduleKey(area);
  const n = String(no || "").trim();
  const req = String(requirement || "").toLowerCase();
  if (module === "accounting") {
    if (["1", "2"].includes(n)) return "10";
    if (["4", "11"].includes(n)) return "9";
    if (["6", "7"].includes(n)) return "11";
    if (["8", "9", "10"].includes(n)) return "12";
    if (n === "3") return "10";
    if (n === "5") return "9,12";
  }
  if (module === "sales") {
    if (n === "1") return "1,2";
    if (["2", "6", "7"].includes(n)) return "3";
    if (n === "3") return "8";
    if (["4", "5", "10"].includes(n)) return "10";
    if (n === "8") return "1,10";
    if (n === "9") return "1";
  }
  if (module === "procurement") {
    if (n === "1") return "2,4";
    if (["2", "3", "7"].includes(n)) return "4";
    if (n === "4") return "12";
    if (n === "5") return "3,4";
    if (n === "6") return "4,11";
    if (n === "8") return "10";
  }
  if (module === "warehouse") {
    if (["1", "3"].includes(n)) return "6";
    if (n === "2") return "4,6";
    if (["4", "5"].includes(n)) return "3,4";
    if (n === "6") return "8";
  }
  if (module === "manufacturing") {
    if (n === "1") return "3,4,5";
    if (n === "2") return "5,12";
    if (n === "3") return "5";
    if (n === "4") return "5,7";
    if (n === "5") return "5,12";
    if (["6", "7"].includes(n)) return "2,12";
    if (n === "8") return "5,6";
    if (n === "9") return "7,8";
  }
  if (req.includes("forecast")) return "3";
  if (req.includes("barcode") || req.includes("lot")) return "6";
  if (req.includes("budget")) return "11";
  if (req.includes("cost") || req.includes("wip")) return "12";
  return "ต้องยืนยันใน workshop";
}

function buildPainPointText(painPointMap, ids) {
  return String(ids)
    .split(",")
    .map((id) => id.trim())
    .filter(Boolean)
    .map((id) => painPointMap.get(Number(id)) ? `${id}: ${painPointMap.get(Number(id))}` : id)
    .join(" | ");
}

async function copySourceFiles() {
  await fs.mkdir(sourceDir, { recursive: true });
  for (const item of sourceFiles) {
    await fs.copyFile(item.source, path.join(sourceDir, item.fileName));
  }
}

function parseR001Rows(r001Workbook) {
  const sheet = r001Workbook.worksheets.getItem("Requirement");
  const values = sheet.getRange("A1:D82").values;
  const rows = new Map();
  let currentModule = "";
  for (let i = 0; i < values.length; i += 1) {
    const [no, requirement, yn, solution] = values[i];
    if (no && !requirement && Number.isNaN(Number(no))) {
      currentModule = moduleKey(no);
      continue;
    }
    if (no !== null && no !== undefined && requirement) {
      const noText = String(no).trim();
      if (noText && !Number.isNaN(Number(noText))) {
        rows.set(`${currentModule}|${noText}`, {
          rowNumber: i + 1,
          yn,
          solution,
          requirement,
        });
      }
    }
  }
  return rows;
}

async function applyClickableMapping() {
  await fs.mkdir(outputDir, { recursive: true });
  await copySourceFiles();

  const workbook = await importWorkbook(baseWorkbookPath);
  const mappingWorkbook = await importWorkbook(requestMappingPath);
  const r001Workbook = await importWorkbook(r001Path);
  const r001Rows = parseR001Rows(r001Workbook);

  const painSheet = workbook.worksheets.getItem("Pain Point Mapping");
  const painValues = painSheet.getRange("A9:B20").values;
  const painPointMap = new Map(painValues.map((row) => [Number(row[0]), row[1]]));

  painSheet.getRange("J8:P20").clear({ applyTo: "all" });
  painSheet.getRange("J8:P8").values = [[
    "ไฟล์ AMS/ลูกค้าที่ใช้ยืนยัน",
    "จุดที่ดูในไฟล์ต้นทาง",
    "กดเปิด R001",
    "กดเปิด AMS Workflow",
    "กดเปิด Blueprint",
    "Sheet/Row อ้างอิง",
    "วิธีอธิบายจากหลักฐาน",
  ]];
  styleHeader(painSheet.getRange("J8:P8"));
  for (const item of painPointLinkRows) {
    painSheet.getRange(`J${item.row}:K${item.row}`).values = [[item.files, item.point]];
    painSheet.getRange(`L${item.row}:N${item.row}`).formulas = [[
      r001Link(item.r001Row),
      amsWorkflowLink(),
      blueprintLink(),
    ]];
    painSheet.getRange(`O${item.row}:P${item.row}`).values = [[`Requirement!A${item.r001Row}`, item.note]];
  }
  styleBody(painSheet.getRange("J9:P20"));
  for (const [col, width] of [["J", 28], ["K", 42], ["L", 18], ["M", 20], ["N", 18], ["O", 22], ["P", 42]]) {
    painSheet.getRange(`${col}:${col}`).format.columnWidth = width;
  }
  painSheet.getRange("A9:P20").format.rowHeight = 88;

  const refSheet = workbook.worksheets.getOrAdd("05 Reference Files");
  refSheet.showGridLines = false;
  refSheet.getRange("A1:J30").clear({ applyTo: "all" });
  refSheet.getRange("A1:J1").merge();
  refSheet.getRange("A1").values = [["ไฟล์ AMS/ลูกค้าต้นทางที่ใช้ทำ Pain Point Mapping"]];
  styleTitle(refSheet.getRange("A1:J1"));
  refSheet.getRange("A2:J3").merge();
  refSheet.getRange("A2").values = [[
    "หน้านี้เหลือเฉพาะไฟล์จาก AMS/ลูกค้าเท่านั้น ไม่รวมไฟล์ mapping/draw.io/dashboard ที่เราทำเพิ่ม เพื่อให้ลูกค้าตรวจสอบแหล่งที่มาได้ตรง ๆ",
  ]];
  refSheet.getRange("A2:J3").format = {
    fill: "#FFF7ED",
    font: { bold: true, color: "#7C2D12" },
    wrapText: true,
    verticalAlignment: "middle",
    borders: { preset: "outside", style: "thin", color: "#FDBA74" },
  };
  refSheet.getRange("A5:G5").values = [["No.", "ไฟล์ต้นทาง AMS", "ประเภท", "ใช้ยืนยัน", "Path ในแพ็ก", "กดเปิดไฟล์", "หมายเหตุ"]];
  styleHeader(refSheet.getRange("A5:G5"));
  const refRows = sourceFiles.map((item, index) => [
    index + 1,
    item.title,
    item.type,
    item.use,
    `ams_source_files\\${item.fileName}`,
    null,
    "ไฟล์ลูกค้า/AMS ต้นทาง",
  ]);
  refSheet.getRangeByIndexes(5, 0, refRows.length, 7).values = refRows;
  refSheet.getRange("F6:F8").formulas = [
    [amsWorkflowLink("เปิด AMS Workflow")],
    [r001Link(6, "เปิด R001 Requirement")],
    [blueprintLink("เปิด Blueprint")],
  ];
  styleBody(refSheet.getRangeByIndexes(5, 0, refRows.length, 7));
  for (const [col, width] of [["A", 6], ["B", 38], ["C", 18], ["D", 42], ["E", 42], ["F", 20], ["G", 28]]) {
    refSheet.getRange(`${col}:${col}`).format.columnWidth = width;
  }
  refSheet.getRange("A1:J1").format.rowHeight = 34;
  refSheet.getRange("A2:J3").format.rowHeight = 42;
  refSheet.getRange("A5:G8").format.rowHeight = 40;

  const detailSheet = mappingWorkbook.worksheets.getItem("01 Detail Mapping 44+24");
  const detailValues = detailSheet.getRange("A1:R69").values;
  const headers = detailValues[0];
  const r001RowsOnly = detailValues.slice(1).filter((row) => row[1] === "R001 Requirement");

  const reqSheet = workbook.worksheets.getOrAdd("06 R001 Requirement Links");
  reqSheet.showGridLines = false;
  reqSheet.getRange("A1:R80").clear({ applyTo: "all" });
  reqSheet.getRange("A1:R1").merge();
  reqSheet.getRange("A1").values = [["R001 Requirement Mapping ครบทุกข้อ พร้อมกดเปิด Excel AMS ต้นทาง"]];
  styleTitle(reqSheet.getRange("A1:R1"));
  reqSheet.getRange("A2:R3").merge();
  reqSheet.getRange("A2").values = [[
    "ตารางนี้เอา requirement 44 ข้อจาก R001 มาโยงกับ pain point, Odoo module, Standard vs Custom, manday และลิงก์เปิดไฟล์ลูกค้าต้นทาง เพื่อใช้ตอบลูกค้าว่าแต่ละ pain point มาจากข้อมูลจริงตรงไหน",
  ]];
  reqSheet.getRange("A2:R3").format = {
    fill: "#FFF7ED",
    font: { bold: true, color: "#7C2D12" },
    wrapText: true,
    verticalAlignment: "middle",
    borders: { preset: "outside", style: "thin", color: "#FDBA74" },
  };

  reqSheet.getRange("A5:R5").values = [[
    "Seq",
    "Module",
    "R001 No.",
    "Requirement ลูกค้า",
    "Solution ใน R001",
    "Odoo Standard / Fit",
    "Apps / Modules",
    "Fit Group",
    "Standard vs Custom",
    "Pain Point ที่เกี่ยวข้อง",
    "Pain Point Summary",
    "MD",
    "Priority",
    "Source Row",
    "กดเปิด R001",
    "กดเปิด AMS Workflow",
    "กดเปิด Blueprint",
    "ประโยคสำหรับ Present",
  ]];
  styleHeader(reqSheet.getRange("A5:R5"));

  const reqRows = r001RowsOnly.map((row) => {
    const seq = row[0];
    const area = row[3];
    const r001No = row[4];
    const requirement = row[5];
    const source = r001Rows.get(`${moduleKey(area)}|${String(r001No).trim()}`) || {};
    const sourceRow = source.rowNumber || "";
    const painIds = painPointForRequirement(area, r001No, requirement);
    return [
      seq,
      area,
      r001No,
      requirement,
      row[6] || source.solution || "",
      row[7],
      row[8],
      row[10],
      row[11],
      painIds,
      buildPainPointText(painPointMap, painIds),
      row[14],
      row[16],
      sourceRow ? `Requirement!A${sourceRow}` : "",
      null,
      null,
      null,
      row[17],
    ];
  });
  reqSheet.getRangeByIndexes(5, 0, reqRows.length, 18).values = reqRows;
  const linkFormulas = reqRows.map((row) => {
    const sourceRow = Number(String(row[13]).replace("Requirement!A", ""));
    return [
      sourceRow ? r001Link(sourceRow) : "",
      amsWorkflowLink(),
      blueprintLink(),
    ];
  });
  reqSheet.getRangeByIndexes(5, 14, linkFormulas.length, 3).formulas = linkFormulas;
  styleBody(reqSheet.getRangeByIndexes(5, 0, reqRows.length, 18));

  const widths = [7, 22, 9, 44, 28, 46, 34, 18, 22, 18, 42, 8, 12, 18, 18, 20, 18, 50];
  widths.forEach((width, idx) => {
    reqSheet.getRangeByIndexes(0, idx, 1, 1).format.columnWidth = width;
  });
  reqSheet.getRange("A1:R1").format.rowHeight = 34;
  reqSheet.getRange("A2:R3").format.rowHeight = 46;
  reqSheet.getRange("A5:R5").format.rowHeight = 40;
  reqSheet.getRangeByIndexes(5, 0, reqRows.length, 18).format.rowHeight = 74;
  reqSheet.freezePanes.freezeRows(5);

  const errors = await workbook.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
    options: { useRegex: true, maxResults: 200 },
    summary: "final formula error scan",
  });
  console.log("=== FORMULA ERRORS ===");
  console.log(errors.ndjson);

  await fs.mkdir(outputDir, { recursive: true });
  const previews = [
    ["Pain Point Mapping", "A1:P20", "pain_point_clickable_source.png"],
    ["05 Reference Files", "A1:G10", "ams_source_files_only.png"],
    ["06 R001 Requirement Links", "A1:R28", "r001_requirement_links.png"],
  ];
  for (const [sheetName, range, fileName] of previews) {
    const preview = await workbook.render({ sheetName, range, scale: 1, format: "png" });
    await fs.writeFile(path.join(outputDir, fileName), new Uint8Array(await preview.arrayBuffer()));
  }

  const output = await SpreadsheetFile.exportXlsx(workbook);
  await output.save(outputPath);
  await output.save(downloadCopyPath);
  console.log(outputPath);
  console.log(downloadCopyPath);
}

if (mode === "inspect") {
  await mainInspect();
} else if (mode === "inspect-source") {
  await inspectSourceDetails();
} else if (mode === "sheets-only") {
  await sheetsOnly();
} else if (mode === "sheets-output") {
  await outputSheetsOnly();
} else if (mode === "render-output") {
  await renderOutput();
} else if (mode === "inspect-mapping-detail") {
  await inspectMappingDetail();
} else if (mode === "apply") {
  await applyClickableMapping();
} else if (mode === "hyperlink-help") {
  await hyperlinkHelp();
}
