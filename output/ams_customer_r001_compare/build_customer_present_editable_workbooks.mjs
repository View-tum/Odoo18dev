import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const presentDir = "C:/365_project/TheCool18e/Dev/output/AMS_PRESENT_CUSTOMER_TH";

function styleSheet(sheet, range, headerRange) {
  sheet.showGridLines = false;
  sheet.getRange(range).format = {
    font: { color: "#111827", size: 11 },
    wrapText: true,
    verticalAlignment: "top",
    borders: { preset: "all", style: "thin", color: "#CBD5E1" },
  };
  sheet.getRange(headerRange).format = {
    fill: "#5B1747",
    font: { bold: true, color: "#FFFFFF", size: 11 },
    wrapText: true,
    verticalAlignment: "middle",
    horizontalAlignment: "center",
    borders: { preset: "all", style: "thin", color: "#FFFFFF" },
  };
}

async function exportWorkbook(workbook, path) {
  const xlsx = await SpreadsheetFile.exportXlsx(workbook);
  await xlsx.save(path);
}

const startWb = Workbook.create();
const orderSheet = startWb.worksheets.add("01 ลำดับ Present");
const talkSheet = startWb.worksheets.add("02 คำพูดง่ายๆ");
const fileSheet = startWb.worksheets.add("03 รายการไฟล์");

orderSheet.getRange("A1:E1").values = [["ลำดับ", "ไฟล์ที่เปิด", "รูปแบบ", "ใช้พูดเรื่องอะไร", "คำพูดกับลูกค้า"]];
orderSheet.getRange("A2:E7").values = [
  [1, "01_Dashboard_AMS_เราช่วยอะไร.html / .xlsx", "HTML + Excel แก้ไขได้", "ภาพรวมว่าเราจะเข้ามาช่วยอะไร", "เราจะช่วยจัด requirement ให้เป็น flow เดียวกัน ลดงานซ้ำ และแยกให้ชัดว่าส่วนไหนใช้ Odoo ได้เลย ส่วนไหนต้องทำเพิ่ม"],
  [2, "02_Manday_และ_รายละเอียด_Request.xlsx", "Excel แก้ไขได้", "Manday ใช้ไปกับอะไร", "ตัวเลขนี้ใช้วางแผนและจัดลำดับงาน ยังไม่ใช่ราคาปิดสุดท้าย ต้องยืนยัน scope ก่อน"],
  [3, "03_Mapping_44_Request_กับ_Flow.xlsx / .drawio", "Excel + Draw.io แก้ไขได้", "Mapping request ไป flow และแยก standard/custom", "44 ข้อคือ request จริง ส่วน 24 จุดเป็นข้อมูลประกอบจาก blueprint/note เพื่อให้ flow ครบ"],
  [4, "04_Workflow_Business_Flow_AMS.drawio", "Draw.io แก้ไขได้", "Business flow ราย module", "เราจะไล่ flow จากต้นจนจบ เพื่อดูว่าใครทำอะไร เอกสารไหนเกิดตรงไหน และจุดไหนต้องตัดสินใจร่วมกัน"],
  [5, "05_สรุปปิดการนำเสนอ_และ_Action_Next.html / .xlsx", "HTML + Excel แก้ไขได้", "ปิด meeting และ next step", "หลังจากวันนี้เราจะขอ confirm scope, ตัวอย่างเอกสาร, report format และไฟล์/API ที่ต้องเชื่อม"],
  [6, "99_ภาพ_Blueprint_ต้นฉบับ_ลูกค้า.jpg", "Reference", "เปิดเทียบกับภาพลูกค้าเมื่อจำเป็น", "ใช้เป็นภาพอ้างอิง ไม่ใช่ไฟล์หลักสำหรับ present"],
];

talkSheet.getRange("A1:C1").values = [["หัวข้อ", "คำพูดแนะนำ", "หมายเหตุ"]];
talkSheet.getRange("A2:C9").values = [
  ["เริ่มประชุม", "วันนี้เราจะดูร่วมกันว่า AMS จะใช้ Odoo ช่วยลดงานซ้ำและทำให้ flow ชัดขึ้นได้ตรงไหน", "เริ่มด้วยภาษาง่าย ไม่ technical"],
  ["Standard First", "เราจะเริ่มจากสิ่งที่ Odoo ทำได้อยู่แล้วก่อน แล้วค่อยดูเฉพาะจุดที่ต้องทำเพิ่มจริง ๆ", "ลดความกังวลเรื่อง custom เยอะ"],
  ["44 Requests", "request ลูกค้าจริงมี 44 ข้อจากไฟล์ R001", "ต้องพูดให้ชัด"],
  ["24 Supporting Points", "อีก 24 จุดเป็นข้อมูลประกอบจาก blueprint และ note เพื่อให้ flow ครบ ไม่ใช่ request เพิ่ม", "กันความเข้าใจผิด"],
  ["Manday", "Manday เป็นตัวช่วยวางแผนและจัด phase ยังไม่ใช่ quotation สุดท้าย", "ต้อง scope lock ก่อน"],
  ["Standard/Custom", "ในแต่ละ flow เราจะแยกให้เห็นว่าส่วนไหนใช้ standard และส่วนไหนต้อง report, integration หรือ custom", "ใช้คู่กับ mapping table"],
  ["ปิดประชุม", "สิ่งที่ต้องได้หลังประชุมคือ scope, priority, owner, sample document, report format และ UAT scenario", "ใช้ปิด action"],
  ["ข้อควรระวัง", "งานที่กระทบ stock, MRP และ accounting ต้องยืนยัน rule ก่อน custom", "เน้นความถูกต้องของระบบ"],
];

fileSheet.getRange("A1:D1").values = [["ไฟล์", "แก้ไขได้ไหม", "ใช้สำหรับ", "หมายเหตุ"]];
fileSheet.getRange("A2:D12").values = [
  ["00_เริ่มที่นี่_AMS_PRESENT_ลูกค้า.html", "แก้ได้ด้วย editor/HTML", "หน้าเปิด package", "ใช้เปิดจริงใน browser"],
  ["00_เริ่มที่นี่_AMS_PRESENT_ลูกค้า.xlsx", "Excel แก้ไขได้", "ลำดับ present และคำพูด", "ไฟล์นี้"],
  ["01_Dashboard_AMS_เราช่วยอะไร.xlsx", "Excel แก้ไขได้", "แก้ dashboard", "ใช้คู่กับ HTML"],
  ["02_Manday_และ_รายละเอียด_Request.xlsx", "Excel แก้ไขได้", "Manday และ detail request", "ไฟล์หลัก"],
  ["03_Mapping_44_Request_กับ_Flow.xlsx", "Excel แก้ไขได้", "Mapping รายข้อ", "มี 44+24"],
  ["03A_Mapping_Standard_Custom_By_Flow.drawio", "Draw.io แก้ไขได้", "ภาพ mapping standard/custom ราย flow", "เปิดใน diagrams.net"],
  ["04_Workflow_Business_Flow_AMS.drawio", "Draw.io แก้ไขได้", "Workflow/business flow", "11 หน้า"],
  ["05_สรุปปิดการนำเสนอ_และ_Action_Next.xlsx", "Excel แก้ไขได้", "ปิด meeting/next step", "ใช้แก้ action list"],
  ["05_สรุปปิดการนำเสนอ_และ_Action_Next.html", "แก้ได้ด้วย editor/HTML", "หน้าอ่านปิด meeting", "ใช้เปิดจริงใน browser"],
  ["README_ลำดับเปิดไฟล์.txt", "Text แก้ไขได้", "ลำดับเปิดแบบสั้น", "ใช้กับ File Explorer"],
  ["99_ภาพ_Blueprint_ต้นฉบับ_ลูกค้า.jpg", "รูปอ้างอิง", "reference", "ไม่ใช่ไฟล์แก้ flow"],
];

styleSheet(orderSheet, "A1:E7", "A1:E1");
styleSheet(talkSheet, "A1:C9", "A1:C1");
styleSheet(fileSheet, "A1:D12", "A1:D1");
orderSheet.getRange("A:A").format.columnWidthPx = 60;
orderSheet.getRange("B:B").format.columnWidthPx = 280;
orderSheet.getRange("C:C").format.columnWidthPx = 170;
orderSheet.getRange("D:E").format.columnWidthPx = 330;
talkSheet.getRange("A:A").format.columnWidthPx = 170;
talkSheet.getRange("B:B").format.columnWidthPx = 520;
talkSheet.getRange("C:C").format.columnWidthPx = 240;
fileSheet.getRange("A:A").format.columnWidthPx = 340;
fileSheet.getRange("B:B").format.columnWidthPx = 150;
fileSheet.getRange("C:D").format.columnWidthPx = 260;
for (const sheet of [orderSheet, talkSheet, fileSheet]) {
  const used = sheet.getUsedRange();
  used.format.rowHeightPx = 58;
  sheet.getRange("A1:Z1").format.rowHeightPx = 38;
}
orderSheet.tables.add("A1:E7", true, "PresentOrder");
talkSheet.tables.add("A1:C9", true, "SimpleTalkTrack");
fileSheet.tables.add("A1:D12", true, "EditableFileList");
await exportWorkbook(startWb, `${presentDir}/00_เริ่มที่นี่_AMS_PRESENT_ลูกค้า.xlsx`);

const closeWb = Workbook.create();
const closeSheet = closeWb.worksheets.add("01 สรุปปิด Meeting");
const confirmSheet = closeWb.worksheets.add("02 สิ่งที่ต้อง Confirm");
const nextSheet = closeWb.worksheets.add("03 Next Step");

closeSheet.getRange("A1:C1").values = [["หัวข้อ", "ข้อความสำหรับพูด", "หมายเหตุ"]];
closeSheet.getRange("A2:C6").values = [
  ["สรุปภาพรวม", "Odoo standard รองรับ flow หลักได้หลายส่วน เช่น Sales, Purchase, Inventory, MRP, Quality และ Accounting", "พูดให้เห็นว่าไม่ต้อง custom ทั้งหมด"],
  ["จุดที่ต้องทำเพิ่ม", "บางจุดเป็นรูปแบบเฉพาะของ AMS เช่น API, report format, COA, DPPM/OEE/OPE, Budget hard lock, Netting, Multi Ledger และ WIP/valuation", "ต้องขอ rule/sample"],
  ["เหตุผลที่ต้อง confirm", "ถ้าเกี่ยวกับ stock, MRP หรือ accounting ต้องออกแบบให้ถูกก่อน เพื่อไม่กระทบการทำงานจริงและการปิดบัญชี", "เน้นความเสี่ยง"],
  ["สิ่งที่ต้องได้หลังประชุม", "ยืนยัน scope, priority, owner, sample document, report format, file/API format และ UAT scenario", "ใช้เป็น action list"],
  ["ประโยคปิด", "หลังจากได้ข้อมูลยืนยัน เราจะปรับ scope, Manday และแผน UAT ให้ชัดขึ้นก่อนเข้าสู่ขั้นตอนถัดไป", "ปิดให้ไปต่อ"],
];

confirmSheet.getRange("A1:D1").values = [["ลำดับ", "เรื่องที่ต้อง Confirm", "ตัวอย่างข้อมูลที่ต้องขอ", "Owner ลูกค้า"]];
confirmSheet.getRange("A2:D9").values = [
  [1, "Scope P1/P2/Future", "รายการ 44 request ที่ต้อง go-live phase แรก", ""],
  [2, "เอกสารจริง", "COA, Tax invoice, BI, PI, PD, RR, PS, RE", ""],
  [3, "สูตร KPI", "DPPM, OEE/OPE, delivery performance", ""],
  [4, "Forecast/API", "Excel/API/EDI sample และรอบ update", ""],
  [5, "Budget Control", "ต้อง warning หรือ hard block", ""],
  [6, "Customer Supplied Material", "ต้องเข้ามูลค่า stock หรือ off-balance", ""],
  [7, "WIP/Cost/Variance", "valuation method และ posting rule", ""],
  [8, "Legacy Data", "Access/BP Soft/Express/Excel ตัวไหนต้อง migrate", ""],
];

nextSheet.getRange("A1:D1").values = [["Step", "สิ่งที่ทำ", "Output", "สถานะ"]];
nextSheet.getRange("A2:D6").values = [
  [1, "ลูกค้า confirm scope และ priority", "Scope P1/P2/Future", "Open"],
  [2, "ทีมเราแยกงาน Standard / Report / Integration / Custom", "Scope breakdown", "Open"],
  [3, "ทำ workshop ราย flow", "Rule และ owner ที่ชัดเจน", "Open"],
  [4, "ปรับ Manday หลัง scope ชัดขึ้น", "Revised manday", "Open"],
  [5, "เตรียม UAT scenario ตาม workflow", "UAT scenario list", "Open"],
];

styleSheet(closeSheet, "A1:C6", "A1:C1");
styleSheet(confirmSheet, "A1:D9", "A1:D1");
styleSheet(nextSheet, "A1:D6", "A1:D1");
closeSheet.getRange("A:A").format.columnWidthPx = 180;
closeSheet.getRange("B:B").format.columnWidthPx = 620;
closeSheet.getRange("C:C").format.columnWidthPx = 220;
confirmSheet.getRange("A:A").format.columnWidthPx = 60;
confirmSheet.getRange("B:C").format.columnWidthPx = 360;
confirmSheet.getRange("D:D").format.columnWidthPx = 180;
nextSheet.getRange("A:A").format.columnWidthPx = 70;
nextSheet.getRange("B:C").format.columnWidthPx = 360;
nextSheet.getRange("D:D").format.columnWidthPx = 150;
for (const sheet of [closeSheet, confirmSheet, nextSheet]) {
  const used = sheet.getUsedRange();
  used.format.rowHeightPx = 58;
  sheet.getRange("A1:Z1").format.rowHeightPx = 38;
}
closeSheet.tables.add("A1:C6", true, "ClosingTalk");
confirmSheet.tables.add("A1:D9", true, "ConfirmList");
nextSheet.tables.add("A1:D6", true, "NextSteps");
await exportWorkbook(closeWb, `${presentDir}/05_สรุปปิดการนำเสนอ_และ_Action_Next.xlsx`);

console.log(JSON.stringify({
  start: `${presentDir}/00_เริ่มที่นี่_AMS_PRESENT_ลูกค้า.xlsx`,
  closing: `${presentDir}/05_สรุปปิดการนำเสนอ_และ_Action_Next.xlsx`,
}, null, 2));
