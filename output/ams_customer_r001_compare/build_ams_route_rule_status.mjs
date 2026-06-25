import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const presentDir = "C:\\365_project\\TheCool18e\\Dev\\output\\AMS_PRESENT_CUSTOMER_TH";
const packageDir = "C:\\365_project\\TheCool18e\\Dev\\output\\ams_customer_r001_compare\\AMS_R001_COMPARE_PACKAGE";
const downloadDir = "C:\\Users\\tumsu\\Downloads";
const jsonPath = path.join(presentDir, "AMS_ROUTE_RULE_STATUS.json");
const outputName = "AMS_Route_Rule_Auto_PO_MO_Status.xlsx";
const previewName = "AMS_Route_Rule_Auto_PO_MO_Status_preview.png";

const data = JSON.parse(await fs.readFile(jsonPath, "utf8"));
const workbook = Workbook.create();

function title(sheet, text, endCol = "F") {
  const r = sheet.getRange(`A1:${endCol}1`);
  r.merge();
  r.values = [[text]];
  r.format = {
    fill: "#5B1747",
    font: { bold: true, color: "#FFFFFF", size: 16 },
    horizontalAlignment: "center",
    verticalAlignment: "middle",
  };
  r.format.rowHeightPx = 34;
}

function header(range, fill = "#0F766E") {
  range.format = {
    fill,
    font: { bold: true, color: "#FFFFFF" },
    wrapText: true,
    verticalAlignment: "middle",
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

const summary = workbook.worksheets.add("00 Summary");
title(summary, "AMS Route Rule / Auto PO / Auto MO Status", "F");
const summaryRows = [
  ["หัวข้อ", "สถานะ", "รายละเอียด"],
  ["Server", "RUNNING", data.url],
  ["Database", data.database, `Port ${data.server_port}`],
  ["MTO Route", data.mto_active ? "เปิดแล้ว" : "ยังไม่เปิด", "Replenish on Order (MTO)"],
  ["Auto MO", data.dryrun.auto_mo, "SO สินค้า FG ที่ตั้ง MTO + Manufacture สร้าง MO อัตโนมัติ"],
  ["Auto PO", data.dryrun.auto_po, "RM/Trading ที่ตั้ง Buy + MTO + Vendor สร้าง RFQ/PO อัตโนมัติ"],
  ["Vendor/Supplierinfo", `${data.counts.sellerinfo} รายการ`, "AMS Supplier Demo"],
  ["Reordering Rules", `${data.counts.orderpoints} รายการ`, "WH/Stock min 10 max 100"],
  ["Dry-run Evidence", data.dryrun.evidence, data.dryrun.note],
];
summary.getRange(`A3:C${summaryRows.length + 2}`).values = summaryRows;
header(summary.getRange("A3:C3"));
body(summary.getRange(`A4:C${summaryRows.length + 2}`));
summary.getRange("B5:B7").format.fill = "#DCFCE7";
widths(summary, [220, 230, 720, 24, 24, 24]);
summary.freezePanes.freezeRows(3);
summary.showGridLines = false;

const routes = workbook.worksheets.add("01 Route Rules");
title(routes, "Standard Odoo Route Rules ที่ใช้", "F");
const routeRows = [["Route", "Active", "Rule Action", "Operation Type", "Procure Method", "ใช้ทำอะไร"]];
for (const [key, route] of Object.entries(data.routes)) {
  for (const rule of route.rules) {
    const use = key === "manufacture" ? "สร้าง MO" : key === "buy" ? "สร้าง RFQ/PO" : "ผูก demand ตาม order";
    routeRows.push([route.name, route.active ? "Yes" : "No", rule[0], rule[1], rule[2], use]);
  }
}
routes.getRange(`A3:F${routeRows.length + 2}`).values = routeRows;
header(routes.getRange("A3:F3"));
body(routes.getRange(`A4:F${routeRows.length + 2}`));
widths(routes, [260, 80, 130, 180, 150, 260]);
routes.freezePanes.freezeRows(3);
routes.showGridLines = false;

const products = workbook.worksheets.add("02 Product Route");
title(products, "Product Route / Vendor / Reordering Rule", "F");
const productRows = [["Code", "Product", "Routes", "Vendor", "Orderpoint", "สรุป"]];
for (const p of data.products) {
  const isFg = p.code === "AMS.400";
  const ok = isFg
    ? p.routes.includes("Manufacture") && p.routes.includes("MTO")
    : p.routes.includes("Buy") && p.routes.includes("MTO") && p.vendors;
  productRows.push([
    p.code,
    p.name,
    p.routes,
    p.vendors,
    p.orderpoints,
    ok ? "พร้อมใช้งาน" : "ต้องตรวจเพิ่ม",
  ]);
}
products.getRange(`A3:F${productRows.length + 2}`).values = productRows;
header(products.getRange("A3:F3"));
body(products.getRange(`A4:F${productRows.length + 2}`));
widths(products, [130, 250, 300, 220, 330, 140]);
products.freezePanes.freezeRows(3);
products.showGridLines = false;

const guide = workbook.worksheets.add("03 วิธีทดสอบ");
title(guide, "วิธีทดสอบ Auto PO / Auto MO ใน Odoo", "D");
const guideRows = [
  ["ลำดับ", "ทดสอบ", "คาดหวัง", "หมายเหตุ"],
  [1, "สร้าง Sales Order สินค้า [AMS.400] AMS.400 REV 00", "Confirm SO แล้วระบบสร้าง MO อัตโนมัติ", "เกิดจาก MTO + Manufacture"],
  [2, "ดู Manufacturing Order ที่ origin เป็นเลข SO", "MO อยู่สถานะ Confirmed/Ready ตาม stock", "ระบบสร้างจาก procurement rule"],
  [3, "ถ้าวัตถุดิบ route Buy + MTO และมี Vendor", "ระบบสร้าง RFQ/PO อัตโนมัติ", "กรณี dry-run สร้าง P00006 แล้ว rollback"],
  [4, "ถ้าใช้ reorderpoint", "Scheduler/Replenishment สร้าง RFQ ตาม min/max", "ใช้สำหรับวาง stock policy"],
];
guide.getRange(`A3:D${guideRows.length + 2}`).values = guideRows;
header(guide.getRange("A3:D3"), "#334155");
body(guide.getRange(`A4:D${guideRows.length + 2}`));
widths(guide, [70, 430, 430, 520]);
guide.freezePanes.freezeRows(3);
guide.showGridLines = false;

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
  products: data.products.length,
}));
