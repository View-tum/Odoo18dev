import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const presentDir = "C:\\365_project\\TheCool18e\\Dev\\output\\AMS_PRESENT_CUSTOMER_TH";
const packageDir = "C:\\365_project\\TheCool18e\\Dev\\output\\ams_customer_r001_compare\\AMS_R001_COMPARE_PACKAGE";
const downloadDir = "C:\\Users\\tumsu\\Downloads";
const jsonPath = path.join(presentDir, "AMS_WORKORDER_COST_STATUS.json");
const outputName = "AMS_WorkOrder_Cost_Dashboard_Odoo.xlsx";
const previewName = "AMS_WorkOrder_Cost_Dashboard_Odoo_preview.png";

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

function section(range, fill = "#0F766E") {
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
  range.format = {
    wrapText: true,
    verticalAlignment: "top",
  };
  range.format.borders = { preset: "all", style: "thin", color: "#E2E8F0" };
}

function widths(sheet, px) {
  px.forEach((w, index) => {
    const col = String.fromCharCode(65 + index);
    sheet.getRange(`${col}:${col}`).format.columnWidthPx = w;
  });
}

function number(range, format = "#,##0.00") {
  range.format.numberFormat = format;
  range.format.horizontalAlignment = "right";
}

function statusFill(range, status) {
  range.format.fill = status === "Done" || status === "ผ่าน" || status === "posted" || status === "done" ? "#DCFCE7" : "#FEF3C7";
}

const summary = workbook.worksheets.add("00 Summary");
title(summary, "AMS Work Order + Cost + Odoo Dashboard Evidence", "H");
const summaryRows = [
  ["หัวข้อ", "สถานะ", "รายละเอียด", "Odoo Record"],
  ["Database", "Done", data.database, data.url],
  ["Standard First", "Done", "ใช้ standard Odoo MRP / Work Order / Stock Valuation / Accounting ไม่ติดตั้ง custom module", `Custom installed: ${data.installed_custom_modules.length}`],
  ["Auto MO", "Done", "Sales Order สร้าง Manufacturing Order ผ่าน route MTO + Manufacture", data.flow.manufacturing_order],
  ["Work Order", "Done", `ปิด Work Order ครบ ${data.flow.workorders.length} ขั้น`, "Manufacturing > Operations > Work Orders"],
  ["Cost Structure", "Done", `Raw material ${data.cost_config.component_cost} + Work center ${data.flow.mo_workcenter_cost_total} = FG cost ${data.product.standard_price}`, "Product > AMS.400 > Cost Structure"],
  ["Stock Valuation", "Done", "MO และ Delivery มี stock valuation layer จริง", "Inventory > Reporting > Valuation"],
  ["Invoice", data.flow.invoices[0]?.state || "N/A", `${data.flow.invoices[0]?.name || ""} amount ${data.flow.invoices[0]?.amount_total || ""}`, "Accounting > Customers > Invoices"],
];
summary.getRange(`A3:D${summaryRows.length + 2}`).values = summaryRows;
section(summary.getRange("A3:D3"));
body(summary.getRange(`A4:D${summaryRows.length + 2}`));
for (let row = 4; row <= summaryRows.length + 2; row += 1) {
  statusFill(summary.getRange(`B${row}`), summary.getRange(`B${row}`).values?.[0]?.[0]);
}
const cardRows = [
  ["ยอดขาย SO", data.flow.sale_order, data.flow.sale_state],
  ["MO ที่ผลิตจริง", data.flow.manufacturing_order, data.flow.mo_state],
  ["ต้นทุน FG/หน่วย", data.product.standard_price, "จาก BOM + Work Center"],
  ["ต้นทุน Work Center", data.flow.mo_workcenter_cost_total, "รวม WO 21 ขั้น"],
  ["Invoice", data.flow.invoices[0]?.name || "", data.flow.invoices[0]?.state || ""],
];
summary.getRange("F3:H7").values = cardRows;
body(summary.getRange("F3:H7"));
summary.getRange("F3:F7").format = { fill: "#F8FAFC", font: { bold: true }, wrapText: true };
number(summary.getRange("G5:G6"));
widths(summary, [190, 120, 520, 330, 30, 190, 180, 260]);
summary.freezePanes.freezeRows(3);
summary.showGridLines = false;

const wo = workbook.worksheets.add("01 WO Cost");
title(wo, "Work Order Cost ที่ตั้งจริงใน Odoo", "H");
const woRows = [["Seq", "Operation", "Work Center", "Actual Minutes", "Cost / Hour", "Cost Formula", "State", "Odoo Cost"]];
data.flow.workorders.forEach((row, index) => {
  woRows.push([index + 1, row.name, row.workcenter, row.duration, row.costs_hour, null, row.state, row.actual_cost]);
});
wo.getRange(`A3:H${woRows.length + 2}`).values = woRows;
for (let row = 4; row <= woRows.length + 2; row += 1) {
  wo.getRange(`F${row}`).formulas = [[`=D${row}*E${row}/60`]];
}
const totalRow = woRows.length + 3;
wo.getRange(`A${totalRow}:E${totalRow}`).merge();
wo.getRange(`A${totalRow}`).values = [["รวมต้นทุน Work Center"]];
wo.getRange(`F${totalRow}`).formulas = [[`=SUM(F4:F${totalRow - 1})`]];
wo.getRange(`H${totalRow}`).formulas = [[`=SUM(H4:H${totalRow - 1})`]];
section(wo.getRange("A3:H3"), "#334155");
body(wo.getRange(`A4:H${totalRow}`));
wo.getRange(`A${totalRow}:H${totalRow}`).format = { fill: "#FEF3C7", font: { bold: true }, wrapText: true };
number(wo.getRange(`D4:F${totalRow}`));
number(wo.getRange(`H4:H${totalRow}`));
widths(wo, [70, 250, 150, 120, 120, 130, 100, 120]);
wo.freezePanes.freezeRows(3);
wo.showGridLines = false;

const bom = workbook.worksheets.add("02 BOM Cost");
title(bom, "BOM / Product Cost จาก Master Data Odoo", "H");
const compRows = [["Code", "Component", "Qty", "UoM", "Unit Cost", "Line Cost", "Cost Method", "Valuation"]];
data.cost_config.components.forEach((row) => {
  compRows.push([row.code, row.product, row.qty, row.uom, row.unit_cost, null, row.cost_method, row.valuation]);
});
bom.getRange(`A3:H${compRows.length + 2}`).values = compRows;
for (let row = 4; row <= compRows.length + 2; row += 1) {
  bom.getRange(`F${row}`).formulas = [[`=C${row}*E${row}`]];
}
const bomTotalRow = compRows.length + 3;
bom.getRange(`A${bomTotalRow}:E${bomTotalRow}`).merge();
bom.getRange(`A${bomTotalRow}`).values = [["รวมต้นทุนวัตถุดิบ"]];
bom.getRange(`F${bomTotalRow}`).formulas = [[`=SUM(F4:F${bomTotalRow - 1})`]];
bom.getRange(`A${bomTotalRow + 2}:E${bomTotalRow + 2}`).merge();
bom.getRange(`A${bomTotalRow + 2}`).values = [["รวมต้นทุน Work Order"]];
bom.getRange(`F${bomTotalRow + 2}`).formulas = [[`='01 WO Cost'!F${totalRow}`]];
bom.getRange(`A${bomTotalRow + 3}:E${bomTotalRow + 3}`).merge();
bom.getRange(`A${bomTotalRow + 3}`).values = [["ต้นทุน FG ต่อหน่วยตาม Odoo"]];
bom.getRange(`F${bomTotalRow + 3}`).formulas = [[`=F${bomTotalRow}+F${bomTotalRow + 2}`]];
bom.getRange(`G${bomTotalRow + 3}:H${bomTotalRow + 3}`).merge();
bom.getRange(`G${bomTotalRow + 3}`).values = [[`Odoo standard_price = ${data.product.standard_price}`]];
section(bom.getRange("A3:H3"), "#334155");
body(bom.getRange(`A4:H${bomTotalRow + 3}`));
bom.getRange(`A${bomTotalRow}:H${bomTotalRow + 3}`).format = { fill: "#F8FAFC", font: { bold: true }, wrapText: true };
number(bom.getRange(`C4:C${bomTotalRow}`), "#,##0.00");
number(bom.getRange(`E4:F${bomTotalRow + 3}`));
widths(bom, [110, 270, 80, 90, 110, 120, 130, 160]);
bom.freezePanes.freezeRows(3);
bom.showGridLines = false;

const evidence = workbook.worksheets.add("03 Evidence");
title(evidence, "Odoo Evidence: เอกสารและ Valuation ที่เกิดจริง", "H");
const docRows = [
  ["ประเภท", "เลขที่", "สถานะ", "รายละเอียด"],
  ["Sales Order", data.flow.sale_order, data.flow.sale_state, "จุดเริ่ม demand จากลูกค้า"],
  ["Manufacturing Order", data.flow.manufacturing_order, data.flow.mo_state, `Origin ${data.flow.mo_origin}, Lot ${data.flow.finished_lot}`],
  ["RFQ / PO Auto", data.flow.purchase_orders.map((po) => po.name).join(", "), data.flow.purchase_orders.map((po) => po.state).join(", "), "เกิดจาก Buy + MTO ของวัตถุดิบ"],
  ["Delivery", data.flow.deliveries.map((pick) => pick.name).join(", "), data.flow.deliveries.map((pick) => pick.state).join(", "), "ส่งสินค้า FG หลังผลิตเสร็จ"],
  ["Invoice", data.flow.invoices.map((inv) => inv.name).join(", "), data.flow.invoices.map((inv) => inv.state).join(", "), `Amount ${data.flow.invoices[0]?.amount_total || ""}`],
];
evidence.getRange(`A3:D${docRows.length + 2}`).values = docRows;
section(evidence.getRange("A3:D3"));
body(evidence.getRange(`A4:D${docRows.length + 2}`));
const svlStart = docRows.length + 5;
evidence.getRange(`A${svlStart}:G${svlStart}`).values = [["Reference", "Product", "Qty", "Unit Cost", "Value", "ความหมาย", "เข้า Dashboard/Report"]];
data.flow.valuation_layers.forEach((row, index) => {
  const excelRow = svlStart + 1 + index;
  const meaning = row.reference === data.flow.manufacturing_order && row.quantity > 0
    ? "ผลิตสินค้า FG พร้อมต้นทุนรวม"
    : row.reference === data.flow.manufacturing_order
      ? "ตัดวัตถุดิบเข้า MO"
      : "ตัด FG ตอนส่งของ";
  evidence.getRange(`A${excelRow}:G${excelRow}`).values = [[row.reference, row.product, row.quantity, row.unit_cost, row.value, meaning, "Inventory > Reporting > Valuation"]];
});
section(evidence.getRange(`A${svlStart}:G${svlStart}`), "#334155");
body(evidence.getRange(`A${svlStart + 1}:G${svlStart + data.flow.valuation_layers.length}`));
number(evidence.getRange(`C${svlStart + 1}:E${svlStart + data.flow.valuation_layers.length}`));
widths(evidence, [150, 300, 90, 120, 120, 220, 300]);
evidence.freezePanes.freezeRows(3);
evidence.showGridLines = false;

const guide = workbook.worksheets.add("04 Odoo Guide");
title(guide, "วิธีเปิดตรวจใน Odoo Dashboard / Report", "F");
const guideRows = [
  ["ลำดับ", "เปิดที่ไหนใน Odoo", "ค้นหาอะไร", "สิ่งที่ต้องอธิบายตอน present", "สถานะ"],
  [1, "Manufacturing > Operations > Manufacturing Orders", data.flow.manufacturing_order, "แสดงว่า SO สร้าง MO จริง และ MO ปิด done แล้ว", "Done"],
  [2, "Manufacturing > Operations > Work Orders", data.flow.manufacturing_order, "แสดง 21 work orders พร้อม duration และ work center", "Done"],
  [3, "Product > AMS.400 > Cost Structure", data.product.code, "อธิบายต้นทุนรวม = วัตถุดิบ + เวลา work center", "Done"],
  [4, "Inventory > Reporting > Valuation", data.flow.manufacturing_order, "เห็น raw material ติดลบ, FG รับเข้าด้วย unit cost 1,559", "Done"],
  [5, "Inventory > Reporting > Valuation", data.flow.deliveries[0]?.name || "", "เห็น FG ตัดออกจากคลังด้วย cost เดียวกัน", "Done"],
  [6, "Accounting > Customers > Invoices", data.flow.invoices[0]?.name || "", "ใบแจ้งหนี้ posted เพื่อปิด flow sale-to-invoice", data.flow.invoices[0]?.state || ""],
];
guide.getRange(`A3:E${guideRows.length + 2}`).values = guideRows;
section(guide.getRange("A3:E3"));
body(guide.getRange(`A4:E${guideRows.length + 2}`));
widths(guide, [70, 340, 180, 520, 120]);
guide.freezePanes.freezeRows(3);
guide.showGridLines = false;

const standard = workbook.worksheets.add("05 Standard vs Pain");
title(standard, "Standard vs Pain Point สำหรับ Work Order + Cost", "F");
const stdRows = [
  ["หัวข้อ", "Standard Odoo รองรับ", "Pain Point เดิม", "สิ่งที่ config แล้ว", "ต้อง Custom ไหม"],
  ["Work Order", "MRP Work Orders + Work Centers + Operations", "เดิม flow มีขั้นตอนผลิต แต่ยังไม่เห็นต้นทุนรายขั้น", "สร้าง WO 21 ขั้นตาม BOM/Routing และปิด done", "ไม่ต้อง custom"],
  ["Machine/Labor Cost", "Work Center Cost per Hour + Operation Duration", "Work Center cost เป็น 0 ทำให้ต้นทุนผลิตไม่สะท้อนจริง", "ตั้ง cost/hour และเวลาแต่ละ operation", "ไม่ต้อง custom"],
  ["BOM Cost", "BOM Cost Structure / button_bom_cost", "FG มีแค่ raw cost 314 ยังไม่รวม WO", "คำนวณ FG cost เป็น 1,559", "ไม่ต้อง custom"],
  ["Stock Valuation", "Stock Valuation Layer จาก MO และ Delivery", "ไม่เห็นหลักฐาน cost ใน report", "SVL แสดง FG รับเข้าและตัดออกที่ 1,559", "ไม่ต้อง custom"],
  ["Odoo Dashboard", "Inventory Valuation / Manufacturing reports / Accounting invoice", "ต้องมีจุดเปิดให้ลูกค้าดู", "เตรียม record และ menu guide แล้ว", "ไม่ต้อง custom"],
  ["Accounting Posting", "ถ้าใช้ automated valuation จะลง journal stock อัตโนมัติ", "DB demo ตอนนี้เป็น manual periodic", "แสดงต้นทุนใน SVL แล้ว; ถ้าลูกค้าต้องการลงบัญชีจริงต้อง set automated valuation + accounts", "อาจเป็น configuration เพิ่ม"],
];
standard.getRange(`A3:E${stdRows.length + 2}`).values = stdRows;
section(standard.getRange("A3:E3"));
body(standard.getRange(`A4:E${stdRows.length + 2}`));
widths(standard, [180, 330, 330, 360, 190]);
standard.freezePanes.freezeRows(3);
standard.showGridLines = false;

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "formula error scan",
});

const summaryInspect = await workbook.inspect({
  kind: "table",
  sheetId: "00 Summary",
  range: "A3:H10",
  include: "values,formulas",
  tableMaxRows: 12,
  tableMaxCols: 8,
});

for (const sheetName of ["00 Summary", "01 WO Cost", "02 BOM Cost", "03 Evidence", "04 Odoo Guide", "05 Standard vs Pain"]) {
  const preview = await workbook.render({ sheetName, autoCrop: "all", scale: 1, format: "png" });
  await fs.writeFile(path.join(presentDir, `${sheetName.replaceAll(" ", "_")}_workorder_cost_preview.png`), new Uint8Array(await preview.arrayBuffer()));
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
  inspect: summaryInspect.ndjson,
  workorders: data.flow.workorders.length,
  fgCost: data.product.standard_price,
}));
