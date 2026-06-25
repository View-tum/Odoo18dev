import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const inputPath = "C:/Users/tumsu/Downloads/AWS_Present_All_PainPoint_Mapped.xlsx";
const workDir = "C:/365_project/TheCool18e/Dev/output/aws_painpoint_mapping";
const packageDir = "C:/365_project/TheCool18e/Dev/output/AMS_PRESENT_CUSTOMER_TH/AWS_PainPoint_Reference_Package";
const referenceDir = path.join(packageDir, "reference_files");
const outputPath = path.join(packageDir, "AWS_Present_All_PainPoint_Mapped_With_References.xlsx");
const downloadCopyPath = "C:/Users/tumsu/Downloads/AWS_Present_All_PainPoint_Mapped_With_References.xlsx";

const mode = process.argv[2] || "inspect";

const referenceFiles = [
  {
    no: 1,
    source: "C:/Users/tumsu/Downloads/AMS_Workflow ERP.xlsx",
    fileName: "01_AMS_Workflow_ERP.xlsx",
    title: "AMS Workflow ERP.xlsx",
    type: "ไฟล์ลูกค้า",
    origin: "AMS workflow เดิม",
    usedFor: "Business flow เดิมของ AMS และจุดงานที่ยังทำ manual",
    painPoints: "1, 4, 5, 6",
    evidence: "ใช้ดู flow วัตถุดิบ, SO, WO, FG, tag/QR และเอกสารที่เกิดในงานจริง",
    standardVsPain: "ใช้เป็นหลักฐานว่า Odoo standard จะรับ flow ไหนได้ และจุดไหนต้องเพิ่ม automation/report",
  },
  {
    no: 2,
    source: "C:/Users/tumsu/Downloads/Requirement on New System_R001.xlsx",
    fileName: "02_Requirement_on_New_System_R001.xlsx",
    title: "Requirement on New System_R001.xlsx",
    type: "ไฟล์ลูกค้า",
    origin: "R001 requirement",
    usedFor: "44 requests และ pain point ที่ลูกค้าแจ้ง",
    painPoints: "1, 3, 10, 11, 12",
    evidence: "ใช้ยืนยัน requirement ด้าน forecast, report, approval, budget และ cost/accounting",
    standardVsPain: "ใช้เทียบว่า requirement ใดเป็น standard configuration และใดเป็น custom scope",
  },
  {
    no: 3,
    source: "C:/Users/tumsu/Downloads/S__51593240.jpg",
    fileName: "03_TFI_business_blueprint_22042024.jpg",
    title: "TFI business blueprint 22/04/2024",
    type: "ไฟล์ลูกค้า",
    origin: "Blueprint ภาพรวมจากลูกค้า",
    usedFor: "Flow ใหญ่ตั้งแต่ขาย, ซื้อ, คลัง, ผลิต, QC, FG, จัดส่ง, บัญชี",
    painPoints: "1-9, 12",
    evidence: "ใช้ดูตำแหน่ง block เช่น Quotation, BOM, Run Cost, PR/PO, QC, COA, PI, IV, RE",
    standardVsPain: "ใช้เป็นภาพหลักตอนอธิบายว่า block สีไหน Odoo standard รองรับ และสีไหนต้อง custom",
  },
  {
    no: 4,
    source: "C:/365_project/TheCool18e/Dev/output/AMS_PRESENT_CUSTOMER_TH/04A_Client_Original_Flow_Standard_vs_Custom.drawio",
    fileName: "04A_Client_Original_Flow_Standard_vs_Custom.drawio",
    title: "04A Client Original Flow - Standard vs Custom",
    type: "ไฟล์ที่เราทำเพิ่ม",
    origin: "ทำจาก AMS original flow",
    usedFor: "แผนภาพแก้ไขได้ที่ mapping AMS flow เดิมกับ Odoo standard/custom",
    painPoints: "1-12",
    evidence: "สีเขียว = standard/configuration, สีส้ม = custom/report/API/approval เพิ่ม",
    standardVsPain: "ใช้ present ตรงว่าทำด้วย Odoo standard ได้ตรงไหน และต้อง custom เพราะอะไร",
  },
  {
    no: 5,
    source: "C:/365_project/TheCool18e/Dev/output/AMS_PRESENT_CUSTOMER_TH/04B_TFI_Blueprint_Standard_vs_Custom_OPENABLE.drawio",
    fileName: "04B_TFI_Blueprint_Standard_vs_Custom_OPENABLE.drawio",
    title: "04B TFI Blueprint - Standard vs Custom",
    type: "ไฟล์ที่เราทำเพิ่ม",
    origin: "ทำจาก TFI blueprint ภาพลูกค้า",
    usedFor: "แผนภาพ editable ที่ overlay สี standard/custom บน blueprint ลูกค้าแบบเป๊ะตามภาพ",
    painPoints: "1-12",
    evidence: "ใช้เปิดใน draw.io เพื่อแก้ไขตำแหน่งสี block หรือคำอธิบายต่อหน้าลูกค้า",
    standardVsPain: "ใช้ยืนยันว่าการ mapping ไม่ได้เปลี่ยน flow ลูกค้า แต่เติมมุม Odoo standard/custom เข้าไป",
  },
  {
    no: 6,
    source: "C:/365_project/TheCool18e/Dev/output/ams_customer_r001_compare/AMS_R001_COMPARE_PACKAGE/04B_TFI_Blueprint_Standard_vs_Custom.xlsx",
    fileName: "04B_TFI_Blueprint_Standard_vs_Custom.xlsx",
    title: "04B TFI Blueprint Mapping Table",
    type: "ไฟล์ที่เราทำเพิ่ม",
    origin: "สรุปจาก 04B draw.io",
    usedFor: "ตาราง mapping block ใน blueprint กับ module, standard/custom และเหตุผล",
    painPoints: "1-12",
    evidence: "ใช้ดูรายละเอียดราย block แทนการดูเฉพาะรูป",
    standardVsPain: "ใช้ตอบคำถามเชิงลึกว่าทำไม block นั้น standard หรือ custom",
  },
  {
    no: 7,
    source: "C:/365_project/TheCool18e/Dev/output/AMS_PRESENT_CUSTOMER_TH/AMS_Route_Rule_Auto_PO_MO_Status.xlsx",
    fileName: "07_AMS_Route_Rule_Auto_PO_MO_Status.xlsx",
    title: "AMS Route Rule Auto PO/MO Status",
    type: "ไฟล์ที่เราทำเพิ่ม",
    origin: "Odoo setup/status",
    usedFor: "หลักฐานการวาง route rule เพื่อ auto PO/MO ตาม flow",
    painPoints: "3, 4, 5",
    evidence: "ใช้ดู route, replenishment และ automation ที่ลด manual click",
    standardVsPain: "ใช้แยกว่า auto PO/MO เป็น standard/configuration ส่วน approval/report เฉพาะทางอาจต้อง custom",
  },
  {
    no: 8,
    source: "C:/365_project/TheCool18e/Dev/output/AMS_PRESENT_CUSTOMER_TH/AMS_WorkOrder_Cost_Dashboard_Odoo.xlsx",
    fileName: "08_AMS_WorkOrder_Cost_Dashboard_Odoo.xlsx",
    title: "AMS Work Order Cost Dashboard Odoo",
    type: "ไฟล์ที่เราทำเพิ่ม",
    origin: "Odoo work order/cost design",
    usedFor: "ตัวอย่าง WO, cost, WIP, variance และ dashboard ที่ลูกค้าอยากเห็น",
    painPoints: "2, 5, 12",
    evidence: "ใช้ดูตัวอย่างต้นทุนจาก BOM/WO/stock valuation ที่วิ่งเข้า dashboard",
    standardVsPain: "ใช้แยกว่า Odoo มี cost base อยู่แล้ว แต่ report layout/KPI เฉพาะ AMS ต้องทำเพิ่ม",
  },
  {
    no: 9,
    source: "C:/365_project/TheCool18e/Dev/output/AMS_PRESENT_CUSTOMER_TH/02_Manday_และ_รายละเอียด_Request.xlsx",
    fileName: "09_Manday_และ_รายละเอียด_Request.xlsx",
    title: "Manday และรายละเอียด Request",
    type: "ไฟล์ที่เราทำเพิ่ม",
    origin: "สรุป scope/estimate",
    usedFor: "Manday, scope, standard/custom และลำดับงาน",
    painPoints: "1-12",
    evidence: "ใช้ประกอบตอนลูกค้าถาม effort และลำดับ implement",
    standardVsPain: "ใช้เชื่อมจาก pain point ไป scope และ manday โดยไม่อธิบายเชิงเทคนิคเกินไป",
  },
  {
    no: 10,
    source: "C:/365_project/TheCool18e/Dev/output/AMS_PRESENT_CUSTOMER_TH/03_Mapping_44_Request_กับ_Flow.xlsx",
    fileName: "10_Mapping_44_Request_กับ_Flow.xlsx",
    title: "Mapping 44 Request กับ Flow",
    type: "ไฟล์ที่เราทำเพิ่ม",
    origin: "สรุปจาก R001 + flow",
    usedFor: "ตารางเทียบ 44 request กับ flow/module/standard/custom",
    painPoints: "1-12",
    evidence: "ใช้ตอบว่า request แต่ละข้อไปอยู่ flow ไหน ไม่ได้เพิ่มเองนอก requirement",
    standardVsPain: "ใช้เป็นไฟล์กลางเวลาต้อง drill down จาก pain point ไป request รายข้อ",
  },
];

const painPointReferences = [
  {
    row: 9,
    files: "02_Requirement_on_New_System_R001.xlsx; 03_TFI_business_blueprint_22042024.jpg; 04A_Client_Original_Flow_Standard_vs_Custom.drawio",
    where: "R001 + ฝ่ายขายใน blueprint: SP / FA / Quotation / SO และ flow Request FA Sample -> Quotation -> SO",
    path: "reference_files\\02_Requirement_on_New_System_R001.xlsx | reference_files\\03_TFI_business_blueprint_22042024.jpg",
    note: "เปิด R001 ก่อน แล้วเปิดรูป blueprint เพื่อชี้ให้เห็นว่าเอกสารก่อนขายกระจายหลายจุดจริง",
  },
  {
    row: 10,
    files: "03_TFI_business_blueprint_22042024.jpg; 04B_TFI_Blueprint_Standard_vs_Custom_OPENABLE.drawio; 08_AMS_WorkOrder_Cost_Dashboard_Odoo.xlsx",
    where: "BOM Option -> Quotation -> Create Product Code/BOM/Process -> Run Cost",
    path: "reference_files\\03_TFI_business_blueprint_22042024.jpg | reference_files\\08_AMS_WorkOrder_Cost_Dashboard_Odoo.xlsx",
    note: "ใช้ blueprint ชี้ Run Cost แล้วใช้ไฟล์ cost dashboard อธิบายแนวทาง Odoo",
  },
  {
    row: 11,
    files: "02_Requirement_on_New_System_R001.xlsx; 03_TFI_business_blueprint_22042024.jpg; 07_AMS_Route_Rule_Auto_PO_MO_Status.xlsx",
    where: "Customer PO/SO -> Production Planning -> MO/Delivery และ requirement เรื่อง forecast/PO/SO",
    path: "reference_files\\02_Requirement_on_New_System_R001.xlsx | reference_files\\07_AMS_Route_Rule_Auto_PO_MO_Status.xlsx",
    note: "เปิด requirement เพื่อยืนยันโจทย์ แล้วเปิด route rule เพื่อบอกว่ามี standard automation รองรับ",
  },
  {
    row: 12,
    files: "01_AMS_Workflow_ERP.xlsx; 03_TFI_business_blueprint_22042024.jpg; 07_AMS_Route_Rule_Auto_PO_MO_Status.xlsx",
    where: "PR/RFQ/PO -> Receive RM -> Print Tag -> Issue RM และ stock shortage check",
    path: "reference_files\\01_AMS_Workflow_ERP.xlsx | reference_files\\03_TFI_business_blueprint_22042024.jpg",
    note: "ใช้ flow วัตถุดิบให้เห็นว่าถ้า MRP รู้ช้า PR/PO จะช้าตาม",
  },
  {
    row: 13,
    files: "03_TFI_business_blueprint_22042024.jpg; 08_AMS_WorkOrder_Cost_Dashboard_Odoo.xlsx",
    where: "กำหนดเครื่องผลิต -> ผลิตตามแผน -> ผลิตเสร็จ -> รับเข้า FG/แก้ไข และ WO/Production Daily",
    path: "reference_files\\03_TFI_business_blueprint_22042024.jpg | reference_files\\08_AMS_WorkOrder_Cost_Dashboard_Odoo.xlsx",
    note: "ใช้ WO/cost dashboard อธิบายว่าการผลิตต้องเห็นสถานะ real-time",
  },
  {
    row: 14,
    files: "01_AMS_Workflow_ERP.xlsx; 03_TFI_business_blueprint_22042024.jpg; 04A_Client_Original_Flow_Standard_vs_Custom.drawio",
    where: "Tag/QR/Lot: receive RM, issue RM, FG tag, PI, issue by SO",
    path: "reference_files\\01_AMS_Workflow_ERP.xlsx | reference_files\\04A_Client_Original_Flow_Standard_vs_Custom.drawio",
    note: "ชี้ว่า traceability มาจาก tag/lot ทุก stock movement ไม่ใช่ feature ที่คิดเพิ่มเอง",
  },
  {
    row: 15,
    files: "03_TFI_business_blueprint_22042024.jpg; 04B_TFI_Blueprint_Standard_vs_Custom_OPENABLE.drawio",
    where: "QC spec -> ผ่าน QC? -> COA/แก้ไข",
    path: "reference_files\\03_TFI_business_blueprint_22042024.jpg | reference_files\\04B_TFI_Blueprint_Standard_vs_Custom_OPENABLE.drawio",
    note: "ใช้ 04B ชี้สี standard/custom ตรง QC และ COA",
  },
  {
    row: 16,
    files: "03_TFI_business_blueprint_22042024.jpg; 04B_TFI_Blueprint_Standard_vs_Custom.xlsx",
    where: "PI -> จ่ายสินค้าตาม SO -> ตรวจสอบก่อนแพ็ค -> IV",
    path: "reference_files\\03_TFI_business_blueprint_22042024.jpg | reference_files\\04B_TFI_Blueprint_Standard_vs_Custom.xlsx",
    note: "ใช้ block mapping เพื่ออธิบาย KPI ส่งช้า/ส่งไม่ครบที่มาจากจุดส่งของจริง",
  },
  {
    row: 17,
    files: "03_TFI_business_blueprint_22042024.jpg; 02_Requirement_on_New_System_R001.xlsx",
    where: "IV, BI, RE, AP/AR payment และ bank reconciliation",
    path: "reference_files\\03_TFI_business_blueprint_22042024.jpg | reference_files\\02_Requirement_on_New_System_R001.xlsx",
    note: "ใช้ flow บัญชีปิดท้ายว่าระบบต้องเชื่อม Delivery -> Invoice -> Payment",
  },
  {
    row: 18,
    files: "02_Requirement_on_New_System_R001.xlsx; 10_Mapping_44_Request_กับ_Flow.xlsx",
    where: "Requirement ด้าน report และมิติ BU/Branch/Customer/Product",
    path: "reference_files\\02_Requirement_on_New_System_R001.xlsx | reference_files\\10_Mapping_44_Request_กับ_Flow.xlsx",
    note: "อธิบายว่ามิติรายงานต้องเก็บตั้งแต่เอกสารต้นทาง ไม่ใช่แค่ทำ report ตอนท้าย",
  },
  {
    row: 19,
    files: "02_Requirement_on_New_System_R001.xlsx; 09_Manday_และ_รายละเอียด_Request.xlsx",
    where: "Requirement control/approval/budget ก่อน PR/PO",
    path: "reference_files\\02_Requirement_on_New_System_R001.xlsx | reference_files\\09_Manday_และ_รายละเอียด_Request.xlsx",
    note: "ใช้บอกว่า standard มี budget view แต่ hard lock/approval เฉพาะทางต้องแยก custom",
  },
  {
    row: 20,
    files: "03_TFI_business_blueprint_22042024.jpg; 08_AMS_WorkOrder_Cost_Dashboard_Odoo.xlsx",
    where: "Run Cost + MO/WO + ผลิตเสร็จ + รับเข้า FG + accounting cost",
    path: "reference_files\\03_TFI_business_blueprint_22042024.jpg | reference_files\\08_AMS_WorkOrder_Cost_Dashboard_Odoo.xlsx",
    note: "ใช้ cost dashboard อธิบาย WIP/variance/valuation ที่ต้องเชื่อม stock และบัญชี",
  },
];

async function ensureReferenceFiles() {
  await fs.mkdir(referenceDir, { recursive: true });
  for (const ref of referenceFiles) {
    try {
      await fs.access(ref.source);
      await fs.copyFile(ref.source, path.join(referenceDir, ref.fileName));
      ref.copyStatus = "Copied";
    } catch {
      ref.copyStatus = "Missing source";
    }
  }

  const readme = [
    "AMS Pain Point Reference Package",
    "",
    "วิธีใช้:",
    "1. เปิดไฟล์ AWS_Present_All_PainPoint_Mapped_With_References.xlsx",
    "2. ไปที่ sheet Pain Point Mapping เพื่อดู pain point และไฟล์อ้างอิงรายข้อ",
    "3. ไปที่ sheet 05 Reference Files เพื่อดูรายชื่อไฟล์ต้นทางทั้งหมด",
    "4. เปิดไฟล์จริงจากโฟลเดอร์ reference_files เมื่อลูกค้าขอดูหลักฐาน",
    "",
    "หมายเหตุ:",
    "- ไฟล์ลูกค้าเดิมถูก copy มาไว้ในแพ็กนี้เพื่อให้ตรวจสอบย้อนหลังได้",
    "- ไฟล์ draw.io เป็นไฟล์แก้ไขได้ ใช้เปิดผ่าน diagrams.net/draw.io",
  ].join("\r\n");
  await fs.writeFile(path.join(packageDir, "README_เปิดไฟล์อ้างอิง.txt"), readme, "utf8");
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

async function inspectWorkbook(workbook) {
  const summary = await workbook.inspect({
    kind: "workbook,sheet,table",
    maxChars: 12000,
    tableMaxRows: 10,
    tableMaxCols: 12,
    tableMaxCellChars: 140,
  });
  console.log(summary.ndjson);

  const pain = await workbook.inspect({
    kind: "region",
    sheetId: "Pain Point Mapping",
    range: "A1:M24",
    maxChars: 18000,
    tableMaxRows: 24,
    tableMaxCols: 13,
    tableMaxCellChars: 200,
  });
  console.log(pain.ndjson);
}

async function renderWorkbook(workbook, label) {
  await fs.mkdir(workDir, { recursive: true });
  const painPreview = await workbook.render({
    sheetName: "Pain Point Mapping",
    range: "A1:M22",
    scale: 1,
    format: "png",
  });
  await fs.writeFile(
    path.join(workDir, `pain_point_mapping_${label}.png`),
    new Uint8Array(await painPreview.arrayBuffer()),
  );

  try {
    const refPreview = await workbook.render({
      sheetName: "05 Reference Files",
      range: "A1:J18",
      scale: 1,
      format: "png",
    });
    await fs.writeFile(
      path.join(workDir, `reference_files_${label}.png`),
      new Uint8Array(await refPreview.arrayBuffer()),
    );
  } catch {
  }
}

async function applyReferenceMapping(workbook) {
  await ensureReferenceFiles();

  const painSheet = workbook.worksheets.getItem("Pain Point Mapping");
  painSheet.showGridLines = false;

  painSheet.getRange("J8:M8").values = [[
    "ไฟล์อ้างอิงให้ลูกค้าเปิดดู",
    "จุดที่ต้องให้ดูในไฟล์",
    "Path ในแพ็ก",
    "วิธีใช้ตอนลูกค้าถาม",
  ]];
  styleHeader(painSheet.getRange("J8:M8"));

  for (const item of painPointReferences) {
    painSheet.getRange(`J${item.row}:M${item.row}`).values = [[
      item.files,
      item.where,
      item.path,
      item.note,
    ]];
  }
  styleBody(painSheet.getRange("J9:M20"));
  painSheet.getRange("J:J").format.columnWidth = 42;
  painSheet.getRange("K:K").format.columnWidth = 46;
  painSheet.getRange("L:L").format.columnWidth = 42;
  painSheet.getRange("M:M").format.columnWidth = 44;
  painSheet.getRange("A9:M20").format.rowHeight = 88;

  const refSheet = workbook.worksheets.getOrAdd("05 Reference Files");
  refSheet.showGridLines = false;
  refSheet.getRange("A1:J40").clear({ applyTo: "all" });

  refSheet.getRange("A1:J1").merge();
  refSheet.getRange("A1").values = [["ไฟล์อ้างอิงที่ใช้ยืนยัน Pain Point Mapping"]];
  refSheet.getRange("A1:J1").format = {
    fill: "#6B0F3F",
    font: { bold: true, color: "#FFFFFF", size: 16 },
    horizontalAlignment: "center",
    verticalAlignment: "middle",
    borders: { preset: "outside", style: "thin", color: "#6B0F3F" },
  };

  refSheet.getRange("A2:J3").merge();
  refSheet.getRange("A2").values = [[
    "Sheet นี้ใช้ตอบลูกค้าว่า pain point แต่ละข้ออ้างอิงจากไฟล์ไหน ไม่ได้คิดขึ้นมาเอง: ไฟล์ลูกค้าเดิมอยู่ในโฟลเดอร์ reference_files และไฟล์ที่เราทำเพิ่มใช้แสดงการ mapping กับ Odoo standard/custom",
  ]];
  refSheet.getRange("A2:J3").format = {
    fill: "#FFF7ED",
    font: { bold: true, color: "#7C2D12" },
    wrapText: true,
    verticalAlignment: "middle",
    borders: { preset: "outside", style: "thin", color: "#FDBA74" },
  };

  refSheet.getRange("A5:J5").values = [[
    "No.",
    "ไฟล์อ้างอิง",
    "ประเภทไฟล์",
    "ที่มา",
    "ใช้ยืนยันเรื่องอะไร",
    "Pain Point ที่เกี่ยวข้อง",
    "จุดที่ใช้เป็นหลักฐาน",
    "Standard vs Pain Point ใช้อย่างไร",
    "Path ในแพ็ก",
    "สถานะไฟล์",
  ]];
  styleHeader(refSheet.getRange("A5:J5"));

  const refRows = referenceFiles.map((ref) => [
    ref.no,
    ref.title,
    ref.type,
    ref.origin,
    ref.usedFor,
    ref.painPoints,
    ref.evidence,
    ref.standardVsPain,
    `reference_files\\${ref.fileName}`,
    ref.copyStatus || "Copied",
  ]);
  refSheet.getRangeByIndexes(5, 0, refRows.length, 10).values = refRows;
  styleBody(refSheet.getRangeByIndexes(5, 0, refRows.length, 10));

  refSheet.getRange("A:A").format.columnWidth = 6;
  refSheet.getRange("B:B").format.columnWidth = 36;
  refSheet.getRange("C:C").format.columnWidth = 18;
  refSheet.getRange("D:D").format.columnWidth = 24;
  refSheet.getRange("E:E").format.columnWidth = 42;
  refSheet.getRange("F:F").format.columnWidth = 20;
  refSheet.getRange("G:G").format.columnWidth = 46;
  refSheet.getRange("H:H").format.columnWidth = 44;
  refSheet.getRange("I:I").format.columnWidth = 42;
  refSheet.getRange("J:J").format.columnWidth = 16;
  refSheet.getRange("A1:J1").format.rowHeight = 34;
  refSheet.getRange("A2:J3").format.rowHeight = 42;
  refSheet.getRange("A5:J5").format.rowHeight = 36;
  refSheet.getRangeByIndexes(5, 0, refRows.length, 10).format.rowHeight = 72;
  refSheet.freezePanes.freezeRows(5);

  const errors = await workbook.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
    options: { useRegex: true, maxResults: 100 },
    summary: "final formula error scan",
  });
  console.log("=== FORMULA ERRORS ===");
  console.log(errors.ndjson);

  await renderWorkbook(workbook, "with_references");

  const output = await SpreadsheetFile.exportXlsx(workbook);
  await output.save(outputPath);
  await output.save(downloadCopyPath);
  console.log(outputPath);
  console.log(downloadCopyPath);
}

const importPath = mode === "inspect-output" ? outputPath : inputPath;
const input = await FileBlob.load(importPath);
const workbook = await SpreadsheetFile.importXlsx(input);

if (mode === "inspect" || mode === "inspect-output") {
  await inspectWorkbook(workbook);
  await renderWorkbook(workbook, "before_references");
} else if (mode === "apply") {
  await applyReferenceMapping(workbook);
}
