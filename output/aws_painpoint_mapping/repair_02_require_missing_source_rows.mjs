import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const outputDir = "C:/365_project/TheCool18e/Dev/output/aws_painpoint_mapping";
const originalPath = "C:/Users/tumsu/Downloads/Requirement on New System_R001.xlsx";
const workbookPath = "C:/Users/tumsu/Desktop/AMS_Present/ams_source_files/02_Require.xlsx";
const fallbackPath = "C:/Users/tumsu/Desktop/AMS_Present/ams_source_files/02_Require_FIXED.xlsx";
const renderPath = path.join(outputDir, "02_Require_repaired_missing_rows_preview.png");
const today = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
const backupPath = path.join(outputDir, `02_Require_before_missing_rows_repair_${today}.xlsx`);

const plainSolutions = new Map([
  [6, "Odoo ช่วยแยกรายงานรายได้ ค่าใช้จ่าย และกำไรตามหน่วยธุรกิจหรือสาขาได้ ทำให้ผู้บริหารเห็นผลประกอบการของแต่ละส่วนงานชัดเจนขึ้น"],
  [7, "Odoo รวมข้อมูลบัญชี ขาย ซื้อ และสต็อกไว้ในระบบเดียว จึงนำตัวเลขมาทำรายงานวิเคราะห์การเงิน เช่น อัตราส่วนทางการเงิน สภาพคล่อง และ EBITDA ได้ง่ายขึ้น"],
  [8, "Odoo รองรับการทำงานหลายบริษัทและดึงรายงานจากแต่ละบริษัทมาดูร่วมกันได้ ส่วนรายงาน consolidation แบบซับซ้อนสามารถต่อยอดเป็นรายงานเฉพาะของ AMS ได้"],
  [9, "Odoo ช่วยนำรายการเดินบัญชีธนาคารมาเทียบกับรายการรับจ่ายในระบบ ลดงานตรวจมือและช่วยให้ปิดบัญชีธนาคารได้เร็วขึ้น"],
  [10, "Odoo มีข้อมูลลูกหนี้ เจ้าหนี้ เงินรับ เงินจ่าย และเงื่อนไขเครดิตอยู่ในระบบ จึงใช้ทำภาพรวมกระแสเงินสดล่วงหน้าได้ และสามารถต่อยอด dashboard ให้ตรงรูปแบบ AMS"],
  [11, "Odoo ช่วยควบคุมงบประมาณตามแผนก โครงการ หรือหน่วยธุรกิจได้ ถ้าต้องการบล็อกไม่ให้ขอซื้อ/สั่งซื้อเกินงบ สามารถตั้งขั้นตอนอนุมัติเพิ่มได้"],
  [12, "Odoo ช่วยติดตามงบลงทุนเป็นโครงการ เห็นวงเงินที่อนุมัติ ใช้ไปแล้ว และคงเหลือ ทำให้ควบคุมค่าใช้จ่ายลงทุนได้เป็นระบบ"],
  [13, "Odoo เก็บต้นทุนซื้อ ผลิต และสต็อกต่อเนื่องกัน ทำให้เห็นความต่างของต้นทุนจริงกับต้นทุนมาตรฐาน และนำไปทำรายงาน cost variance ได้"],
  [14, "Odoo มีข้อมูลต้นทุนและมูลค่าสต็อกจากการรับของ ผลิต และขาย จึงใช้เป็นฐานในการกระจายผลต่างต้นทุนไปที่ COGS, Inventory และ WIP ได้"],
  [15, "Odoo ติดตามงานผลิต วัตถุดิบที่เบิก และสินค้าที่อยู่ระหว่างผลิตได้ ทำให้เห็นจำนวนและมูลค่า WIP แม้ต้องออกแบบรายงานให้ตรงวิธีดูของ AMS เพิ่มเติม"],
  [16, "Odoo ช่วยรวมข้อมูลบัญชี ภาษี ทรัพย์สิน งบประมาณ และรายงานผู้บริหารไว้ในระบบเดียว แล้วเลือกต่อยอดรายงานเฉพาะที่ AMS ต้องใช้จริง"],
  [25, "Odoo ช่วยติดตามใบเสนอราคาตั้งแต่เสนอจนปิดการขาย ทำให้เห็นอัตราชนะงาน เหตุผลที่ชนะ/แพ้ และประสิทธิภาพของฝ่ายขายได้"],
  [26, "Odoo สามารถเชื่อมข้อมูลใบสั่งซื้อจากลูกค้าเข้ากับ Sale Order, แผนผลิต และความต้องการวัตถุดิบ ช่วยลดการกรอกซ้ำและลดโอกาสผิดพลาด"],
  [27, "Odoo ช่วยเทียบสิ่งที่ลูกค้าต้องการกับของที่ส่งจริง ทำให้เห็นปัญหาส่งไม่ครบ ส่งช้า หรือส่งไม่ตรงตามแผนได้ชัดเจน"],
  [28, "Odoo ช่วยแยกยอดขายและกำไรขั้นต้นตามหน่วยธุรกิจ ทำให้ผู้บริหารเห็นว่าส่วนงานใดทำกำไรดีหรือควรปรับปรุง"],
  [29, "Odoo ช่วยแยกยอดขายและกำไรตามสาขา ทำให้ดูผลประกอบการรายพื้นที่หรือรายสาขาได้จากข้อมูลเดียวกัน"],
  [30, "Odoo ใช้ข้อมูล forecast และคำสั่งขายเพื่อช่วยวางแผนความต้องการวัตถุดิบล่วงหน้า ทำให้จัดซื้อและผลิตเตรียมตัวได้เร็วขึ้น"],
  [31, "Odoo ช่วยควบคุมเงื่อนไขการขาย เช่น MOQ, หน่วยนับ, BOM และข้อมูลจัดซื้อที่เกี่ยวข้อง เพื่อลดปัญหาขายผิดหน่วยหรือสั่งผลิตผิดเงื่อนไข"],
  [32, "Odoo มีข้อมูลลูกค้า ราคา และข้อตกลงการขายเป็นฐานให้ใช้งานได้ ส่วนสัญญากรอบตามหน่วยธุรกิจสามารถออกแบบหน้าจอ/รายงานให้ตรงวิธีทำงานของ AMS"],
  [33, "Odoo ช่วยเก็บข้อมูลลูกค้า กิจกรรมการขาย ประวัติการติดต่อ และข้อมูลสำคัญของลูกค้าไว้ที่เดียว ทำให้ฝ่ายขายและผู้บริหารเห็นภาพลูกค้าครบขึ้น"],
  [34, "Odoo ช่วยรวมงานขาย ตั้งแต่ข้อมูลลูกค้า ใบเสนอราคา คำสั่งขาย การส่งของ และกำไร ทำให้ลดงาน Excel และติดตามงานขายได้จากระบบเดียว"],
  [37, "Odoo ช่วยเปรียบเทียบราคาและเงื่อนไขจากผู้ขายหลายราย ทำให้เลือกผู้ขายได้มีเหตุผลมากขึ้น ทั้งราคา คุณภาพ เครดิต และระยะเวลาส่งมอบ"],
  [38, "Odoo เก็บประวัติผู้ขาย ราคา การส่งมอบ และเอกสารจัดซื้อ ทำให้ทำ supplier evaluation ได้จากข้อมูลจริงในระบบ"],
  [39, "Odoo ช่วยดึงข้อมูลการส่งตรงเวลา ราคา และเงื่อนไขเครดิตของผู้ขายมาใช้ประเมินผู้ขาย ลดการรวบรวมข้อมูลด้วยมือ"],
  [40, "Odoo เก็บประวัติราคาซื้อและต้นทุน ทำให้เห็นแนวโน้มต้นทุนขึ้นลง และใช้วิเคราะห์ผลกระทบต่อต้นทุนสินค้าได้"],
  [41, "Odoo เชื่อมข้อมูลขาย แผนผลิต สต็อก และข้อมูลผู้ขาย ทำให้ระบบช่วยคำนวณว่าควรซื้ออะไร ปริมาณเท่าไร และต้องเผื่อ lead time อย่างไร"],
  [42, "Odoo ช่วยทำขั้นตอนขอซื้อและสั่งซื้อพร้อมอนุมัติ ลดการอนุมัตินอกระบบ และทำให้เห็นเหตุผลประกอบก่อนออก PO"],
  [43, "Odoo รองรับข้อตกลงกับผู้ขาย เช่น ราคา เงื่อนไข และระยะเวลาที่ตกลงไว้ ช่วยให้จัดซื้ออ้างอิงเงื่อนไขเดิมได้ถูกต้อง"],
  [44, "Odoo ช่วยรวมงานจัดซื้อ ผู้ขาย ราคา อนุมัติ และรับของไว้ในระบบเดียว ทำให้ฝ่ายจัดซื้อและบัญชีตรวจสอบเอกสารต่อกันได้ง่ายขึ้น"],
  [47, "Odoo ช่วยควบคุมสต็อกตาม Lot/Batch ได้ ทำให้รู้ว่าวัตถุดิบหรือสินค้าล็อตไหนเข้าเมื่อไร ใช้ไปที่ไหน และเหลือเท่าไร"],
  [48, "Odoo รองรับการจัดเก็บตามคลัง ชั้นวาง หรือ location ทำให้ค้นหาของง่ายขึ้นและลดปัญหาสต็อกไม่ตรงตำแหน่ง"],
  [49, "Odoo ใช้ Barcode ช่วยรับของ เบิกของ ย้ายของ ผลิต และส่งของ ลดการคีย์มือและลดโอกาสหยิบผิดหรือบันทึกผิด"],
  [50, "Odoo เชื่อมข้อมูลสต็อก แผนผลิต คำสั่งขาย และคำสั่งซื้อ ทำให้เห็นของขาด ของเกิน ของช้า และสินค้าไม่เคลื่อนไหวได้เร็วขึ้น"],
  [51, "Odoo ตั้งจุดสั่งซื้อขั้นต่ำและปริมาณสั่งเติมได้ เมื่อสต็อกต่ำกว่าที่กำหนด ระบบช่วยเตือนหรือสร้างความต้องการจัดซื้อได้"],
  [52, "Odoo ช่วยติดตามงานจัดส่ง เส้นทาง และต้นทุนขนส่งเป็นข้อมูลกลาง ส่วน ticket driver evaluation หรือรูปแบบเฉพาะของ AMS สามารถต่อยอดรายงานได้"],
  [56, "Odoo เชื่อมคำสั่งขาย แผนผลิต สต็อก FG/WIP และการจัดซื้อ ทำให้วางแผนผลิตและวัตถุดิบได้ต่อเนื่องจากข้อมูลเดียวกัน"],
  [57, "Odoo ช่วยบันทึกวัตถุดิบเข้า ผลผลิตออก ของเสีย และเวลาที่ใช้ในงานผลิต ทำให้คุมต้นทุนและประสิทธิภาพการผลิตได้ชัดขึ้น"],
  [58, "Odoo ช่วยติดตามสถานะงานผลิตแต่ละขั้นตอน เช่น รอผลิต กำลังผลิต เสร็จแล้ว หรือรอตรวจคุณภาพ ทำให้เห็นงานค้างใน shop floor ได้"],
  [59, "Odoo มีข้อมูลเวลา เครื่องจักร งานผลิต และคุณภาพเป็นฐานให้คำนวณ OPE ได้ ส่วนสูตรหรือรูปแบบ dashboard ตามนิยาม AMS สามารถทำเพิ่มได้"],
  [60, "Odoo มีข้อมูลเครื่องจักร เวลาทำงาน downtime และคุณภาพงานผลิต จึงใช้วิเคราะห์ OEE และต่อยอด dashboard ผู้บริหารได้"],
  [61, "Odoo รองรับ BOM หลายชั้นและ routing การผลิต ทำให้เห็นว่าสินค้าหนึ่งตัวต้องใช้วัตถุดิบและผ่านขั้นตอนใดบ้าง"],
  [62, "Odoo เก็บ BOM และ routing เป็นข้อมูลกลางสำหรับใช้เสนอราคาและเตรียมเอกสาร PPAP ได้ ส่วนการจัดการ version ตามรูปแบบ AMS สามารถออกแบบเพิ่มได้"],
  [63, "Odoo ใช้ Barcode ติดตามงานผลิตแต่ละขั้นตอน ช่วยให้รู้ว่างานอยู่จุดไหน ใครทำ และใช้วัตถุดิบอะไรบ้าง"],
  [64, "Odoo เก็บข้อมูลส่งออก ตรวจคุณภาพ และรับคืนจากลูกค้า ทำให้ใช้วิเคราะห์ DPPM และปัญหาคืนสินค้าได้ โดยทำ dashboard ให้ตรง KPI ของ AMS ได้"],
]);

function normalize(value) {
  if (value === null || value === undefined) return "";
  return String(value).replace(/\s+/g, " ").trim();
}

await fs.mkdir(outputDir, { recursive: true });
await fs.copyFile(workbookPath, backupPath);

const originalInput = await FileBlob.load(originalPath);
const currentInput = await FileBlob.load(workbookPath);
const originalWorkbook = await SpreadsheetFile.importXlsx(originalInput);
const currentWorkbook = await SpreadsheetFile.importXlsx(currentInput);
const originalSheet = originalWorkbook.worksheets.getItemAt(0);
const currentSheet = currentWorkbook.worksheets.getItemAt(0);

const originalValues = originalSheet.getRange("A1:D80").values;
const currentValues = currentSheet.getRange("A1:D80").values;
const repaired = [];
const mismatches = [];

for (let i = 0; i < originalValues.length; i += 1) {
  const rowNo = i + 1;
  const originalRow = originalValues[i] || [];
  const currentRow = currentValues[i] || [];
  const sourceNo = normalize(originalRow[0]);
  const sourceReq = normalize(originalRow[1]);
  if (sourceNo === "" && sourceReq === "") continue;

  const currentNo = normalize(currentRow[0]);
  const currentReq = normalize(currentRow[1]);
  if (sourceReq !== "" && (currentNo !== sourceNo || currentReq !== sourceReq)) {
    currentSheet.getRange(`A${rowNo}:C${rowNo}`).values = [[originalRow[0] ?? null, originalRow[1] ?? null, originalRow[2] ?? null]];
    if (plainSolutions.has(rowNo)) {
      currentSheet.getRange(`D${rowNo}`).values = [[plainSolutions.get(rowNo)]];
    }
    repaired.push({
      row: rowNo,
      no: sourceNo,
      requirement: sourceReq,
      previousNo: currentNo,
      previousRequirement: currentReq,
    });
  }
}

for (let i = 0; i < originalValues.length; i += 1) {
  const rowNo = i + 1;
  const originalRow = originalValues[i] || [];
  const currentRow = currentSheet.getRange(`A${rowNo}:D${rowNo}`).values[0] || [];
  const sourceNo = normalize(originalRow[0]);
  const sourceReq = normalize(originalRow[1]);
  if (sourceNo === "" && sourceReq === "") continue;
  const currentNo = normalize(currentRow[0]);
  const currentReq = normalize(currentRow[1]);
  if (sourceNo !== currentNo || sourceReq !== currentReq) {
    mismatches.push({ row: rowNo, sourceNo, currentNo, sourceReq, currentReq });
  }
}

currentSheet.getRange("D1:D120").format.wrapText = true;
currentSheet.getRange("D1:D120").format.columnWidth = 74;
currentSheet.getRange("A1:D120").format.autofitRows();

const inspect = await currentWorkbook.inspect({
  kind: "table",
  sheetId: currentSheet.name,
  range: "A20:D65",
  include: "values",
  tableMaxRows: 46,
  tableMaxCols: 4,
  tableMaxCellChars: 100,
});

const errorScan = await currentWorkbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "final formula error scan",
});

const preview = await currentWorkbook.render({
  sheetName: currentSheet.name,
  range: "A20:D65",
  scale: 1,
  format: "png",
});
await fs.writeFile(renderPath, new Uint8Array(await preview.arrayBuffer()));

const output = await SpreadsheetFile.exportXlsx(currentWorkbook);
let savedPath = workbookPath;
try {
  await output.save(workbookPath);
} catch (error) {
  if (error?.code !== "EBUSY") throw error;
  await output.save(fallbackPath);
  savedPath = fallbackPath;
}

console.log(JSON.stringify({
  workbookPath: savedPath,
  intendedWorkbookPath: workbookPath,
  originalPath,
  backupPath,
  renderPath,
  repairedCount: repaired.length,
  repaired,
  remainingMismatchCount: mismatches.length,
  mismatches,
  inspectPreview: inspect.ndjson.split("\n").slice(0, 8).join("\n"),
  errorScan: errorScan.ndjson,
}, null, 2));
