import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const inputPath = "C:/Users/tumsu/Downloads/AWS_Present_All.xlsx";
const outputPath = "C:/Users/tumsu/Downloads/AWS_Present_All_PainPoint_Mapped.xlsx";
const outputDir = "C:/365_project/TheCool18e/Dev/output/aws_painpoint_mapping";

const mode = process.argv[2] || "inspect";

const input = await FileBlob.load(inputPath);
const workbook = await SpreadsheetFile.importXlsx(input);

async function inspectWorkbook() {
  console.log("=== SHEETS ===");
  const sheets = await workbook.inspect({
    kind: "sheet",
    include: "id,name",
    maxChars: 6000,
  });
  console.log(sheets.ndjson);

  console.log("=== WORKBOOK SUMMARY ===");
  const summary = await workbook.inspect({
    kind: "workbook,sheet,table",
    maxChars: 12000,
    tableMaxRows: 8,
    tableMaxCols: 10,
    tableMaxCellChars: 120,
  });
  console.log(summary.ndjson);

  console.log("=== PAIN POINT MAPPING ===");
  const pain = await workbook.inspect({
    kind: "region",
    sheetId: "Pain Point Mapping",
    range: "A1:Z80",
    maxChars: 20000,
    tableMaxRows: 80,
    tableMaxCols: 26,
    tableMaxCellChars: 240,
  });
  console.log(pain.ndjson);
}

async function renderSheet(label = "before") {
  await fs.mkdir(outputDir, { recursive: true });
  const preview = await workbook.render({
    sheetName: "Pain Point Mapping",
    range: "A1:J22",
    scale: 1,
    format: "png",
  });
  const bytes = new Uint8Array(await preview.arrayBuffer());
  const previewPath = path.join(outputDir, `pain_point_mapping_${label}.png`);
  await fs.writeFile(previewPath, bytes);
  console.log(previewPath);
}

const sourceRows = [
  [
    "มาจาก Requirement R001 + Blueprint ฝ่ายขาย: SP / FA / Quotation / SO และ AMS original flow ช่วง Request FA Sample → Quotation → SO",
    "01 Block Mapping: SP, FA, QUO, SO_PLAN | 04B TFI Blueprint lane ขาย | AMS original flow กลุ่ม RFQ/Drawing/Quotation",
    "พูดว่า pain point นี้ไม่ได้มาจากเราเดา แต่เห็นจาก flow ก่อนขายของ AMS ที่มีเอกสารและ revision หลายจุดก่อนออก SO",
  ],
  [
    "มาจาก TFI Blueprint ช่วง BOM Option → Quotation → Create Product Code/BOM/Process → Run Cost",
    "01 Block Mapping: PCC_STEP, MACHINE, MO_PLAN, PRODUCT_CODE_ACC | 02 Custom Scope: PCC | 03 Standard Support: MRP/Work Center",
    "อธิบายว่า AMS ต้องรู้ cost ก่อน quote เพราะใน blueprint มี Run Cost ก่อนวนกลับไป approve/แก้ไข",
  ],
  [
    "มาจาก Requirement R001 เรื่อง forecast/PO/SO และจาก flow ลูกค้า: Customer PO/SO → Production Planning → MO/Delivery",
    "01 Block Mapping: SO_PLAN, SO_CP, MO_PLAN, FG_ISSUE_SO | 03 Standard Support: Sales + MRP, MPS/MRP route",
    "อธิบายว่าโจทย์คือ demand กับแผนผลิตต้องต่อกัน ไม่ใช่แค่เปิด SO แยกจากโรงงาน",
  ],
  [
    "มาจาก flow วัตถุดิบใน TFI Blueprint: PR/RFQ/PO → รับวัตถุดิบ → พิมพ์ Tag → จ่ายวัตถุดิบ และจุด check stock/shortage ใน AMS flow",
    "01 Block Mapping: PR_RM_SALE, PR_COLLECT, PO, RM_RECEIVE, RM_ISSUE | 03 Standard Support: Inventory + Purchase + MRP",
    "พูดว่า pain point นี้เห็นจากหลายจุดที่ต้องรู้ RM ก่อนผลิต ถ้ารู้ช้าจะเปิดซื้อช้าและกระทบวันส่ง",
  ],
  [
    "มาจาก flow ผลิตของลูกค้า: กำหนดเครื่องผลิต → ผลิตตามแผน → ผลิตเสร็จ → แก้ไข/รับเข้า FG และ AMS original flow ที่มี WO/Production Daily",
    "01 Block Mapping: MACHINE, MO_PLAN, PROD_DONE, REWORK, PI | 03 Standard Support: MO/WO/Shop Floor",
    "อธิบายว่าฝ่ายขายตอบลูกค้าไม่ได้ถ้า SO ไม่เชื่อม MO/WO/QC/FG เป็นสถานะเดียวกัน",
  ],
  [
    "มาจากการใช้ Tag/QR/Lot ใน flow ลูกค้า: รับวัตถุดิบ, พิมพ์ Tag รับ, จ่ายวัตถุดิบ, พิมพ์ Tag สินค้า, รับสินค้าเข้าคลัง, จ่ายตาม SO",
    "01 Block Mapping: TAG_IN, TAG_CP, FG_TAG, RM_RECEIVE, RM_ISSUE, PI, FG_ISSUE_SO | 03 Standard Support: Lot/Serial + Stock Moves",
    "พูดว่า traceability ไม่ได้เป็น feature เสริมลอย ๆ แต่ผูกกับทุกจุดที่ลูกค้ามี tag/lot/stock movement อยู่แล้ว",
  ],
  [
    "มาจาก lane ควบคุมคุณภาพใน TFI Blueprint: ตรวจสอบสินค้าตามข้อกำหนด → ผ่าน QC? → COA/แก้ไข",
    "01 Block Mapping: QC_SPEC, QC_DECISION, COA, REWORK | 02 Custom Scope: COA | 03 Standard Support: Quality Checks",
    "อธิบายว่า standard เก็บผลตรวจได้ แต่ COA/KPI defect ตามรูปแบบ AMS ต้องแยก scope ให้ชัด",
  ],
  [
    "มาจาก flow คลังสินค้าสำเร็จรูป/จัดส่ง: รับสินค้าเข้าคลัง (PI), จ่ายสินค้าตาม SO, ตรวจสอบก่อนแพ็ค, ใบกำกับภาษี",
    "01 Block Mapping: PI, FG_ISSUE_SO, PACK_CHECK, IV | 03 Standard Support: Delivery Order + Quality before delivery",
    "พูดว่า KPI ส่งช้า/ส่งไม่ครบมาจากจุดส่งของจริงใน blueprint ไม่ใช่ report ที่คิดเพิ่มเอง",
  ],
  [
    "มาจาก flow การเงิน/บัญชีของ AMS: ใบกำกับภาษี, วางบิล, ใบเสร็จ และ payment/AP-AR ใน blueprint",
    "01 Block Mapping: IV, BI, RE, PS | 03 Standard Support: Customer Invoice, Payment, Bank Reconciliation, Accounting",
    "อธิบายว่า Odoo จะเชื่อม Delivery → Invoice → Payment เพื่อลดการทำซ้ำของบัญชี",
  ],
  [
    "มาจาก Requirement R001 หมวดรายงาน/การดูข้อมูลแยกมิติ และต้องผูกตั้งแต่เอกสารต้นทางใน AMS",
    "Pain Point Mapping เดิม row 10 + 00 Summary 44 Requests | ใช้ร่วมกับ Sales/Purchase/Inventory/MRP/Accounting dimensions",
    "พูดว่าเรื่อง BU/Branch/Customer/Product ไม่ใช่ flow block เดี่ยว แต่เป็นมิติข้อมูลที่ต้องบังคับตั้งแต่ต้นทาง",
  ],
  [
    "มาจาก Requirement R001 เรื่อง control/approval/budget ซึ่งไม่แสดงเป็นกล่องหลักใน TFI Blueprint แต่เป็น pain point การควบคุมก่อน PR/PO",
    "Pain Point Mapping เดิม row 11 | 02 Custom Scope แนว approval/form | Standard base: Analytic Budget",
    "อธิบายว่า Odoo standard ดู budget ได้ แต่ถ้าจะ hard lock ไม่ให้เกินงบ ต้อง confirm custom scope",
  ],
  [
    "มาจาก TFI Blueprint ช่วง Run Cost + ผลิตตามแผน/ผลิตเสร็จ/รับเข้า FG และ Requirement R001 หมวด cost/accounting",
    "01 Block Mapping: MO_PLAN, PROD_DONE, PI, PD, RR | 03 Standard Support: MO Cost, Stock Valuation, Accounting",
    "พูดว่า cost variance/WIP กระทบ stock และบัญชี จึงต้อง design logic ให้ชัดก่อนทำ report/wizard",
  ],
];

async function applyPainPointSourceMapping() {
  const sheet = workbook.worksheets.getItem("Pain Point Mapping");
  sheet.showGridLines = false;

  sheet.getRange("A3:I3").merge();
  sheet.getRange("A3").values = [[
    "แหล่งที่ใช้ยืนยันว่า pain point มาจากข้อมูล AMS จริง: Requirement on New System_R001.xlsx (44 requests) + TFI business blueprint 22/04/2024 + AMS original customer flow + 01 Block Mapping ในไฟล์นี้",
  ]];
  sheet.getRange("A3:I3").format = {
    fill: "#FFF7ED",
    font: { bold: true, color: "#7C2D12" },
    wrapText: true,
    borders: { preset: "outside", style: "thin", color: "#FDBA74" },
  };
  sheet.getRange("A3").format = {
    fill: "#FFF7ED",
    font: { bold: true, color: "#7C2D12" },
    wrapText: true,
    verticalAlignment: "middle",
    borders: { preset: "outside", style: "thin", color: "#FDBA74" },
  };

  sheet.getRange("G8:I8").values = [[
    "ที่มาจากข้อมูล AMS",
    "หลักฐาน / Block ที่อ้างอิง",
    "วิธีอธิบายตอน Present",
  ]];
  sheet.getRange("A7:I7").values = [[
    "Source",
    "R001 44 requests",
    "TFI Blueprint 22/04/2024",
    "AMS original flow",
    "01 Block Mapping",
    "Custom/Standard scope",
    "คอลัมน์ G = มาจากข้อมูลลูกค้าตรงไหน",
    "คอลัมน์ H = หลักฐานที่โยงกลับได้",
    "คอลัมน์ I = ประโยคใช้ present",
  ]];
  sheet.getRange("G9:I20").values = sourceRows;

  sheet.getRange("G8:I8").format = {
    fill: "#6B0F3F",
    font: { bold: true, color: "#FFFFFF" },
    wrapText: true,
    horizontalAlignment: "center",
    verticalAlignment: "middle",
    borders: { preset: "all", style: "thin", color: "#FFFFFF" },
  };
  sheet.getRange("G9:G20").format = {
    fill: "#FEF3C7",
    font: { color: "#111827" },
    wrapText: true,
    verticalAlignment: "top",
    borders: { preset: "all", style: "thin", color: "#93C5FD" },
  };
  sheet.getRange("H9:H20").format = {
    fill: "#EEF2FF",
    font: { color: "#111827" },
    wrapText: true,
    verticalAlignment: "top",
    borders: { preset: "all", style: "thin", color: "#93C5FD" },
  };
  sheet.getRange("I9:I20").format = {
    fill: "#ECFDF5",
    font: { color: "#111827" },
    wrapText: true,
    verticalAlignment: "top",
    borders: { preset: "all", style: "thin", color: "#93C5FD" },
  };

  sheet.getRange("A8:I20").format.borders = { preset: "all", style: "thin", color: "#38BDF8" };
  sheet.getRange("A8:I8").format = {
    fill: "#6B0F3F",
    font: { bold: true, color: "#FFFFFF" },
    wrapText: true,
    horizontalAlignment: "center",
    verticalAlignment: "middle",
    borders: { preset: "all", style: "thin", color: "#FFFFFF" },
  };

  sheet.getRange("A1:I1").format = {
    fill: "#6B0F3F",
    font: { bold: true, color: "#FFFFFF", size: 15 },
    horizontalAlignment: "center",
    verticalAlignment: "middle",
  };
  sheet.getRange("A2:I2").format = {
    fill: "#FCE4D6",
    font: { bold: true, color: "#1F2937" },
    wrapText: true,
    verticalAlignment: "middle",
  };
  sheet.getRange("A5:I6").format = {
    wrapText: true,
    horizontalAlignment: "center",
    verticalAlignment: "middle",
  };
  sheet.getRange("A7:I7").format = {
    fill: "#FFF7ED",
    font: { bold: true, color: "#7C2D12" },
    wrapText: true,
    horizontalAlignment: "center",
    verticalAlignment: "middle",
    borders: { preset: "all", style: "thin", color: "#FDBA74" },
  };

  sheet.getRange("A:A").format.columnWidth = 6;
  sheet.getRange("B:B").format.columnWidth = 34;
  sheet.getRange("C:C").format.columnWidth = 38;
  sheet.getRange("D:D").format.columnWidth = 32;
  sheet.getRange("E:E").format.columnWidth = 36;
  sheet.getRange("F:F").format.columnWidth = 25;
  sheet.getRange("G:G").format.columnWidth = 45;
  sheet.getRange("H:H").format.columnWidth = 43;
  sheet.getRange("I:I").format.columnWidth = 42;
  sheet.getRange("A1:I1").format.rowHeight = 30;
  sheet.getRange("A2:I2").format.rowHeight = 62;
  sheet.getRange("A3:I3").format.rowHeight = 52;
  sheet.getRange("A7:I7").format.rowHeight = 30;
  sheet.getRange("A8:I8").format.rowHeight = 34;
  sheet.getRange("A9:I20").format.rowHeight = 74;
  sheet.freezePanes.freezeRows(8);

  await fs.mkdir(outputDir, { recursive: true });
  await renderSheet("after");
  const errors = await workbook.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
    options: { useRegex: true, maxResults: 100 },
    summary: "final formula error scan",
  });
  console.log("=== FORMULA ERRORS ===");
  console.log(errors.ndjson);

  const output = await SpreadsheetFile.exportXlsx(workbook);
  await output.save(outputPath);
  console.log(outputPath);
}

if (mode === "inspect") {
  await inspectWorkbook();
} else if (mode === "render-before") {
  await renderSheet("before");
} else if (mode === "apply") {
  await applyPainPointSourceMapping();
}
