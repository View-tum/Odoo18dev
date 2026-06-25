import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outDir = "C:/365_project/TheCool18e/Dev/output/ams_customer_r001_compare";
const packageDir = `${outDir}/AMS_R001_COMPARE_PACKAGE`;
const customerPath = "C:/Users/tumsu/Downloads/Requirement on New System_R001.xlsx";
const oursPath = "C:/365_project/TheCool18e/Dev/output/ams_workflow_editable_new/AMS_TH_PRESENT_PACKAGE/02_AMS_Workflow_Mapping_with_Manday.xlsx";
const blueprintImagePath = "C:/Users/tumsu/Downloads/S__51593240.jpg";
const outputXlsx = `${packageDir}/01_AMS_R001_Comparison_Manday_Sequence.xlsx`;
const guideMd = `${packageDir}/02_AMS_R001_Presentation_Guide_TH.md`;
const guideHtml = `${packageDir}/03_AMS_R001_Presentation_Guide_TH.html`;
const readmePath = `${packageDir}/00_README_START_HERE_TH.md`;
const previewPath = `${packageDir}/04_Manday_Summary_Preview.png`;
const imageCopyPath = `${packageDir}/05_TFI_Blueprint_Reference.jpg`;

const areaAliases = new Map([
  ["ACCOUNTING AND FINANCE", "Accounting & Finance"],
  ["ACCOUNTING AND FINANCE ", "Accounting & Finance"],
  ["Sale", "Sales"],
  ["Sale ", "Sales"],
  ["PROCUREMENT", "Procurement"],
  ["WAREHOUSE AND LOGISTIC", "Warehouse & Logistic"],
  ["MANUFACTURING", "Manufacturing"],
  ["SYSTEM", "System / Infrastructure"],
  ["Project Lead Time", "Project Timeline"],
  ["PROJECT COSTS", "Commercial / Cost"],
]);

const odooByArea = {
  "Accounting & Finance": {
    apps: "Accounting, Thai Localization, Budget, Project, Spreadsheet",
    models: "account.move, account.journal, account.report, account.analytic.account, account.budget",
  },
  Sales: {
    apps: "CRM, Sales, Sales Margin, MRP/Sales, Inventory",
    models: "crm.lead, sale.order, res.partner, product.template, stock.rule",
  },
  Procurement: {
    apps: "Purchase, Purchase Agreements, Approvals, Inventory, Vendor Pricelist",
    models: "purchase.order, purchase.requisition, approval.request, product.supplierinfo, stock.picking",
  },
  "Warehouse & Logistic": {
    apps: "Inventory, Barcode, Delivery, Fleet",
    models: "stock.picking, stock.move, stock.quant, stock.lot, delivery.carrier, fleet.vehicle",
  },
  Manufacturing: {
    apps: "MRP, Work Orders, Quality, Maintenance, Barcode MRP, PLM",
    models: "mrp.production, mrp.workorder, mrp.bom, mrp.routing.workcenter, quality.point, quality.check",
  },
  "System / Infrastructure": {
    apps: "Odoo.sh / cloud deployment / server operations",
    models: "Deployment architecture, backup, monitoring, user access",
  },
};

const customerSolutionNotes = new Map([
  ["Multi Company?", "ใช้ Multi-company ได้สำหรับแยกบริษัท/branch แต่ statutory consolidation ยังต้องออกแบบ consolidation/elimination เพิ่ม"],
  ["Only Cash flow Statement  but Aging is provided", "Odoo standard มี Cash Flow Statement และ Aging; ถ้าต้อง forecast จาก PR/PO/AP/AR ต้องทำ report/dashboard เพิ่ม"],
  ["Need Budget APP", "ใช้ Budget/Analytic Budget standard ก่อน ถ้าต้อง hard lock PR/PO เกินงบต้องเพิ่ม guard"],
  ["Need Project APP", "ใช้ Project + Analytic Account สำหรับ CAPEX/Investment tracking"],
  ["Customized", "ลูกค้าระบุว่าต้อง customize ต้องแตก business formula และ source data ก่อน estimate final"],
  ["Use Landed Cost to Allocate Variance", "Landed Cost standard ช่วย allocate landed cost เข้า inventory ได้ แต่ production variance to COG/WIP/FG ต้อง design เพิ่ม"],
  ["Use Action \"WIP\" to record WIP", "ถ้าใช้ WIP location/operation tracking ทำได้ด้วย MRP+Inventory; ถ้าไม่ใช้ stock location แต่ต้อง value WIP ตาม process ต้อง report/custom"],
  ["Ratio Analysis/Executive Summary", "ใช้ Accounting Report/Spreadsheet Dashboard ได้ แต่ executive pack เฉพาะบริษัทเป็น report configuration/custom dashboard"],
  ["Use CRM", "ใช้ CRM standard สำหรับ lead/opportunity/win-rate และเชื่อม quotation"],
  ["API ?", "ถ้าลูกค้าต้องรับ Customer PO/Forecast automotive จาก external file/API ต้องทำ import/integration เพิ่ม"],
  ["Module Inventory /Dashboard", "ใช้ Inventory/Sales data ทำ dashboard ได้ แต่สูตร non-fulfillment ต้องนิยาม KPI เพิ่ม"],
  ["MPS", "ใช้ MPS/MRP forecast เป็น standard แต่ format forecast import ต้องออกแบบ"],
  ["???", "ยังไม่ชัดเจน ต้องถาม scope เพิ่มใน workshop"],
  ["??? Web???", "CRM customer profile standard รองรับ notes/tags/activity; ถ้าต้อง web portal/customer 360 เพิ่มต้องออกแบบ"],
  ["RMA", "Odoo standard มี return flow; ถ้าต้อง RMA workflow/claim/DPPM dashboard ต้อง custom/report"],
  ["MTO?", "MTO route standard แต่ quotation BOM/PPAP revision control ต้อง design เพิ่ม"],
]);

function normalize(value) {
  return String(value ?? "").replace(/\s+/g, " ").trim();
}

function normalizeKey(value) {
  return normalize(value).toLowerCase();
}

function areaName(value) {
  const key = normalize(value);
  return areaAliases.get(key) ?? key;
}

function estimateFromFit(fit, solution, area, requirement, base) {
  const text = normalize(`${fit} ${solution} ${requirement}`).toLowerCase();
  if (base?.recommended) {
    let min = base.min;
    let max = base.max;
    let recommended = base.recommended;
    let category = base.category || "Existing estimate";
    let priority = base.priority || "Medium";
    let phase = base.phase || "P1";
    if (text.includes("api")) {
      min = Math.max(min, 8);
      max = Math.max(max, 18);
      recommended = Math.max(recommended, 12);
      category = "Integration / Import";
      priority = "High";
      phase = "P2";
    }
    if (text.includes("customized") && recommended < 8) {
      min = Math.max(min, 6);
      max = Math.max(max, 12);
      recommended = Math.max(recommended, 9);
      category = "Custom / Report";
      priority = "High";
      phase = "P2";
    }
    return { category, min, max, recommended, phase, priority };
  }
  if (text.includes("api")) return { category: "Integration / Import", min: 8, max: 18, recommended: 12, phase: "P2", priority: "High" };
  if (text.includes("customized") || text.includes("multi ledger")) return { category: "Custom / Design", min: 8, max: 18, recommended: 12, phase: "P2", priority: "High" };
  if (text.includes("dashboard") || text.includes("report") || text.includes("ratio") || text.includes("dppm") || text.includes("ope") || text.includes("oee")) return { category: "Report / KPI", min: 4, max: 8, recommended: 6, phase: "P2", priority: "High" };
  if (text.includes("budget") || text.includes("approval") || text.includes("lock")) return { category: "Config + Guard", min: 5, max: 10, recommended: 8, phase: "P2", priority: "High" };
  if (text.includes("project") || text.includes("mps") || text.includes("crm") || text.includes("landed cost")) return { category: "Standard / Config", min: 1, max: 4, recommended: 2.5, phase: "P1", priority: "Medium" };
  if (area === "System / Infrastructure" || area === "Commercial / Cost" || area === "Project Timeline") return { category: "Commercial / Infra Scope", min: 0, max: 0, recommended: 0, phase: "Commercial", priority: "Review" };
  return { category: "Clarification / Fit Check", min: 1, max: 3, recommended: 2, phase: "P1", priority: "Medium" };
}

function fitFromSolution(solution, customerYN, baseFit) {
  const text = normalize(solution).toLowerCase();
  if (customerYN === "N") return "Customer says No / Standard partial";
  if (text.includes("customized") || text.includes("api") || text.includes("???")) return "Need Clarification / Likely Custom";
  if (text.includes("need budget") || text.includes("need project") || text.includes("use crm") || text.includes("mps") || text.includes("landed cost")) return "Standard / Config";
  return baseFit || "Standard Fit Check";
}

function odooExplanation(area, requirement, solution) {
  const req = normalize(`${requirement} ${solution}`).toLowerCase();
  if (req.includes("consolidation")) return "Odoo standard รองรับ multi-company, inter-company และ reporting base; consolidation แบบ elimination/ownership/translation ต้องออกแบบ report/custom หรือ external consolidation";
  if (req.includes("cash flow forecast")) return "Odoo standard มี cash flow statement, AP/AR aging และ payment terms; forecast รวม PR/PO/AP/AR ต้องทำ spreadsheet/dashboard/custom report";
  if (req.includes("budget")) return "Odoo standard มี Analytic Budget/Budget APP; hard lock PR/PO เกินงบต้องเพิ่ม approval guard/constraint";
  if (req.includes("landed cost") || req.includes("cost variance")) return "Landed Cost เป็น standard สำหรับ allocate cost เข้า stock valuation; production variance allocation to COG/WIP/FG ต้อง design accounting rule เพิ่ม";
  if (req.includes("wip")) return "MRP/Inventory standard track WIP ผ่าน production moves/location/work order; WIP value by process without location ต้องทำ report/custom";
  if (req.includes("customer") && req.includes("po") && req.includes("api")) return "Sales/MRP standard รับ SO/forecast ได้; external Customer PO/forecast automotive ต้องทำ import/API mapping";
  if (req.includes("contract")) return "Purchase blanket agreement standard รองรับฝั่งซื้อ; sales framework by BU ต้องตรวจว่าใช้ Sales template/contract ได้หรือทำ custom contract model";
  if (req.includes("crm")) return "CRM/Contacts standard รองรับ profile, activities, tags, notes; customer 360/web portal เฉพาะทางเป็น custom/report";
  if (req.includes("supplier")) return "Purchase/Vendor Pricelist standard รองรับ vendor data; weighted supplier scorecard ต้องทำ KPI/report";
  if (req.includes("barcode")) return "Inventory Barcode และ Barcode MRP standard รองรับ scan receipt/delivery/operation; ถ้าฟอร์ม tag เฉพาะ legacy ต้องทำ report template";
  if (req.includes("ope") || req.includes("oee")) return "Work Orders/Maintenance/Quality มี source data; สูตร OPE/OEE ตามบริษัทต้องทำ dashboard/report";
  if (req.includes("dppm") || req.includes("rma")) return "Return/Quality data เป็น standard base; DPPM/RMA claim dashboard ต้อง custom/report";
  return `ใช้ ${odooByArea[area]?.apps ?? "Odoo standard apps"} เป็น baseline แล้วตรวจ requirement detail ใน workshop`;
}

function nextAction(fit, solution, area) {
  const text = normalize(`${fit} ${solution}`).toLowerCase();
  if (text.includes("???")) return "ต้องถาม requirement เพิ่มก่อนสรุปว่าจะ standard หรือ custom";
  if (text.includes("api")) return "เก็บ sample file/API spec, frequency, mapping field และ error handling";
  if (text.includes("customized")) return "ขอสูตร/ตัวอย่างรายงาน/owner และ acceptance criteria";
  if (fit.includes("Standard") || fit.includes("Config")) return "ตั้งค่า standard module + master data แล้วทำ UAT scenario";
  if (area === "System / Infrastructure") return "แยกเป็น infrastructure/commercial track ไม่รวมกับ functional manday";
  return "ยืนยัน business rule, source data และ owner ใน workshop";
}

async function importTable(path, sheetName, range) {
  const blob = await FileBlob.load(path);
  const workbook = await SpreadsheetFile.importXlsx(blob);
  return workbook.worksheets.getItem(sheetName).getRange(range).values;
}

function parseCustomerRows(values) {
  let currentArea = "";
  const requirements = [];
  const solutionOnly = [];
  for (let i = 0; i < values.length; i++) {
    const [a, b, c, d] = values[i];
    if (typeof a === "string" && normalize(a) && !Number.isFinite(Number(a)) && !["SOFTWARE", "COMPANY", "REQUIREMENT", "MODULE :"].includes(normalize(a))) {
      currentArea = areaName(a);
      continue;
    }
    if (typeof a === "number" && normalize(b)) {
      requirements.push({
        sourceRow: i + 1,
        area: currentArea,
        no: a,
        requirement: normalize(b),
        customerYN: normalize(c),
        customerSolution: normalize(d),
      });
      continue;
    }
    if (!normalize(a) && normalize(b) && currentArea) {
      solutionOnly.push({
        sourceRow: i + 1,
        area: currentArea,
        no: "",
        requirement: normalize(b),
        customerYN: normalize(c),
        customerSolution: normalize(d),
      });
      continue;
    }
    if (!normalize(a) && !normalize(b) && normalize(d) && currentArea) {
      solutionOnly.push({
        sourceRow: i + 1,
        area: currentArea,
        no: "",
        requirement: "Other solution note",
        customerYN: "",
        customerSolution: normalize(d),
      });
    }
  }
  return { requirements, solutionOnly };
}

function parseOurRows(values) {
  const map = new Map();
  const rows = [];
  for (const row of values.slice(1)) {
    if (!normalize(row[0]) || row[1] == null) continue;
    const item = {
      area: areaName(row[0]),
      no: Number(row[1]),
      requirement: normalize(row[2]),
      standardFunction: normalize(row[4]),
      apps: normalize(row[5]),
      models: normalize(row[6]),
      fit: normalize(row[7]),
      painPoint: normalize(row[8]),
      mandayCategory: normalize(row[10]),
      min: Number(row[11] ?? 0),
      max: Number(row[12] ?? 0),
      recommended: Number(row[13] ?? 0),
      phase: normalize(row[15]),
      priority: normalize(row[16]),
    };
    rows.push(item);
    map.set(`${item.area}#${item.no}`, item);
  }
  return { map, rows };
}

function buildComparison(customerRequirements, ourMap) {
  return customerRequirements.map((row, index) => {
    const base = ourMap.get(`${row.area}#${row.no}`);
    const estimate = estimateFromFit(base?.fit, row.customerSolution, row.area, row.requirement, base);
    const customerNote = customerSolutionNotes.get(row.customerSolution) || "";
    const fit = fitFromSolution(row.customerSolution, row.customerYN, base?.fit);
    return {
      sequence: index + 1,
      source: "R001 Requirement",
      area: row.area,
      no: row.no,
      requirement: row.requirement,
      customerYN: row.customerYN,
      customerSolution: row.customerSolution,
      ourMappedRequirement: base?.requirement || "ยังไม่มีใน mapping เดิม",
      ourFit: base?.fit || "New / Need Mapping",
      customerVsOurs: base ? "มีใน mapping เดิม แต่ต้องเพิ่มคำอธิบายจาก Solution ลูกค้า" : "ใหม่จากลูกค้า ต้อง map เพิ่ม",
      odooStandard: odooExplanation(row.area, row.requirement, row.customerSolution),
      apps: base?.apps || odooByArea[row.area]?.apps || "",
      models: base?.models || odooByArea[row.area]?.models || "",
      standardCustomDecision: fit,
      gapToAdd: customerNote || nextAction(fit, row.customerSolution, row.area),
      nextAction: nextAction(fit, row.customerSolution, row.area),
      mandayCategory: estimate.category,
      min: estimate.min,
      max: estimate.max,
      recommended: estimate.recommended,
      phase: estimate.phase,
      priority: estimate.priority,
      presentSequence: `${String(index + 1).padStart(2, "0")} - ${row.area}: ${row.requirement.slice(0, 58)}`,
    };
  });
}

const additionalRows = [
  ["R001 Solution Note", "Accounting & Finance", "Financial report as Audit Report", "Accounting Reports / Audit report layout", "Standard report base แต่ audit format เฉพาะต้อง config/report", "Report / KPI", 2, 5, 3.5, "P2", "Medium"],
  ["R001 Solution Note", "Accounting & Finance", "Fixed Assets Family", "Assets standard", "Odoo Accounting asset/deferred model ใช้ได้ ต้อง setup asset category/family", "Standard / Config", 1, 3, 2, "P1", "Medium"],
  ["R001 Solution Note", "Accounting & Finance", "QR code for collection", "l10n_th/account_qr_code_emv", "Thailand localization มี QR base; format ธนาคารจริงต้องทดสอบ", "Standard / Config", 1, 3, 2, "P1", "Medium"],
  ["R001 Solution Note", "Accounting & Finance", "Netting Payment", "Accounting payment/journal entry", "Customer/vendor netting แบบ workflow อาจต้อง wizard/approval", "Custom / Guard", 5, 10, 8, "P2", "High"],
  ["R001 Solution Note", "Accounting & Finance", "Multi Ledger", "Journals, multi-company, analytic", "ถ้าหมายถึง parallel ledger/reporting book ต้อง design เพิ่ม", "Custom / Design", 10, 20, 15, "P3", "High"],
  ["R001 Solution Note", "Accounting & Finance", "Deferred Expenses", "Deferred expense/revenue standard", "ใช้ standard accounting deferral ก่อน", "Standard / Config", 1, 3, 2, "P1", "Medium"],
  ["R001 Solution Note", "Accounting & Finance", "Thai Tax report", "l10n_th + l10n_th_reports", "มี standard Thailand Accounting/Reports ใน source; ต้องติดตั้งและทดสอบแบบ ภ.ง.ด./VAT", "Standard / Config", 1, 4, 2.5, "P1", "High"],
  ["R001 Solution Note", "Warehouse & Logistic", "Ticket issuing / Driver evaluation", "Delivery + Fleet + Helpdesk/Project optional", "Route/cost standard บางส่วน; ticket/driver score workflow ต้องออกแบบ", "Partial Standard + Custom", 6, 12, 9, "P2", "High"],
  ["R001 Solution Note", "System / Infrastructure", "Cloud service / Server", "Deployment track", "แยกเป็น infrastructure/commercial ไม่ใช่ Odoo functional gap", "Commercial / Infra", 0, 0, 0, "Commercial", "Review"],
  ["R001 Solution Note", "Project Timeline", "Project lead time 9-12 MTH", "Project plan", "ใช้เป็น presentation timeline benchmark ไม่ใช่ functional manday", "Timeline", 0, 0, 0, "Commercial", "Review"],
];

const blueprintRows = [
  ["Blueprint", "Sales", "SP สินค้าใหม่ / IMR ขอรหัสสินค้า", "Product + Approvals + PLM", "Standard รองรับ product master/ECO/approval; ต้องเพิ่ม form/sequence ถ้าต้องเหมือนเอกสารเดิม", "Config + Custom Guard", 4, 8, 6, "P1", "High"],
  ["Blueprint", "Sales", "FA / Forecast Automotive จากลูกค้า", "Sales Forecast / MPS / Import", "MPS/MRP standard; automotive forecast file/API ต้องทำ import mapping", "Integration / Import", 8, 18, 12, "P2", "High"],
  ["Blueprint", "Sales", "SO + แผน / IV / BI", "Sales Order, Invoice, Billing Statement", "SO/Invoice standard; BI statement format ไทยหรือ legacy อาจต้อง custom report", "Config + Report", 3, 6, 4, "P1", "High"],
  ["Blueprint", "Procurement", "รวบรวม PR คัดแยก และออก PO", "Purchase + Approvals + Purchase Agreement", "Standard รองรับ RFQ/PO/approval; suggestion/auto grouping ต้องตรวจ rule", "Standard + Automation", 2, 6, 4, "P1", "Medium"],
  ["Blueprint", "Raw Material Warehouse", "รับ RM / พิมพ์ Tag / จ่าย RM", "Inventory Receipt, Barcode, Internal Transfer", "Standard รองรับ receipt/tag/barcode/move; label layout เฉพาะต้อง report template", "Standard + Report", 2, 6, 4, "P1", "High"],
  ["Blueprint", "Raw Material Warehouse", "วัตถุดิบลูกค้า / CP", "Owner stock / Customer supplied material", "Odoo มี owner/consignment concept; valuation/report separation ต้อง design", "Partial Standard + Report", 4, 8, 6, "P2", "High"],
  ["Blueprint", "Production Engineering", "PCC กำหนดขั้นตอนการผลิต", "BOM/Routing/Work Centers/PLM", "Routing/work centers standard; PCC document/form approval อาจต้อง custom report/workflow", "Config + Report", 4, 8, 6, "P1", "High"],
  ["Blueprint", "Quality", "ตรวจสอบตามข้อกำหนด และออก COA", "Quality Point/Quality Check/COA Report", "Quality standard เก็บผลตรวจได้; COA PDF/customer format ต้อง custom report", "Standard + Custom Report", 5, 10, 8, "P2", "High"],
  ["Blueprint", "Planning", "กำหนดเครื่องผลิต / IS เบิกวัตถุดิบ / WI กึ่งสำเร็จรูป", "MRP Work Orders, material issue, semi-finished", "MRP standard รองรับ work center/material consumption/semi-finished; WI/IS form เฉพาะต้อง report", "Config + Report", 5, 10, 8, "P1", "High"],
  ["Blueprint", "Manufacturing", "ผลิตตามแผน / ผลิตเสร็จ / แก้ไข", "MO/Work Orders/Rework/Scrap", "MO/WO/Rework/Scrap standard base; exact rework route approval ต้อง design", "Standard + Config", 3, 8, 5, "P1", "High"],
  ["Blueprint", "Finished Goods Warehouse", "PI รับเข้าคลัง / จัดส่งตาม SO", "FG Receipt/Delivery Order", "Standard inventory delivery flow; PI document sequence/report เฉพาะต้อง config/report", "Standard + Report", 2, 5, 3.5, "P1", "Medium"],
  ["Blueprint", "Logistics", "ตรวจสอบใบส่งของขนส่ง / รับวัตถุดิบลูกค้า", "Delivery/Fleet/Barcode", "Delivery/Fleet standard บางส่วน; delivery ticket/driver evaluation เพิ่ม", "Partial Standard + Custom", 5, 10, 7, "P2", "Medium"],
  ["Blueprint", "Accounting", "สร้างรหัสสินค้า / PD/RR/PS/RE", "Accounting, Payments, Receipts, Product approval", "Invoice/payment/receipt standard; legacy document code mapping ต้องทำ sequence/report", "Config + Report", 4, 8, 6, "P1", "High"],
  ["Blueprint", "Cross Module", "Legacy system icons Access/BP Soft/Express/Excel/Web", "Data migration / integration assessment", "ต้องทำ data migration mapping และตัดสินใจระบบใด replace ด้วย Odoo", "Migration / Integration", 8, 20, 14, "P2", "High"],
];

function matrixFromObjects(rows, headers, getter) {
  return [headers, ...rows.map(getter)];
}

function setHeader(range) {
  range.format = {
    fill: "#5B1747",
    font: { bold: true, color: "#FFFFFF" },
    wrapText: true,
    verticalAlignment: "middle",
    borders: { preset: "all", style: "thin", color: "#D9D9D9" },
  };
}

function setBody(range) {
  range.format = {
    wrapText: true,
    verticalAlignment: "top",
    borders: { preset: "all", style: "thin", color: "#E5E7EB" },
  };
}

function writeTable(sheet, startRow, startCol, rows, headerColor = "#5B1747") {
  const range = sheet.getRangeByIndexes(startRow, startCol, rows.length, rows[0].length);
  range.values = rows;
  const header = sheet.getRangeByIndexes(startRow, startCol, 1, rows[0].length);
  setHeader(header);
  header.format.fill = headerColor;
  if (rows.length > 1) setBody(sheet.getRangeByIndexes(startRow + 1, startCol, rows.length - 1, rows[0].length));
  return range;
}

function summarize(rows) {
  const map = new Map();
  for (const row of rows) {
    const key = row.area;
    if (!map.has(key)) map.set(key, { area: key, items: 0, min: 0, max: 0, rec: 0, high: 0, custom: 0, standard: 0, report: 0 });
    const item = map.get(key);
    item.items += 1;
    item.min += Number(row.min || 0);
    item.max += Number(row.max || 0);
    item.rec += Number(row.recommended || 0);
    if (row.priority === "High") item.high += 1;
    const cat = normalize(row.mandayCategory).toLowerCase();
    if (cat.includes("report") || cat.includes("kpi")) item.report += Number(row.recommended || 0);
    else if (cat.includes("custom") || cat.includes("gap") || cat.includes("integration") || cat.includes("migration") || cat.includes("guard")) item.custom += Number(row.recommended || 0);
    else item.standard += Number(row.recommended || 0);
  }
  return [...map.values()].sort((a, b) => b.rec - a.rec);
}

function htmlFromMarkdown(md) {
  const lines = md.split(/\r?\n/);
  const out = [
    "<!doctype html><html><head><meta charset=\"utf-8\"><title>AMS R001 Presentation Guide</title>",
    "<style>body{font-family:Arial,'Noto Sans Thai',sans-serif;max-width:1180px;margin:32px;line-height:1.55;color:#111827}h1{color:#5B1747}h2{border-bottom:2px solid #E5E7EB;padding-bottom:6px;margin-top:32px}h3{color:#374151}li{margin:5px 0}table{border-collapse:collapse;width:100%;margin:16px 0}td,th{border:1px solid #CBD5E1;padding:8px;vertical-align:top}th{background:#5B1747;color:white}</style></head><body>",
  ];
  let list = false;
  for (const line of lines) {
    if (!line.trim()) {
      if (list) {
        out.push("</ul>");
        list = false;
      }
      continue;
    }
    if (line.startsWith("# ")) out.push(`<h1>${line.slice(2)}</h1>`);
    else if (line.startsWith("## ")) out.push(`<h2>${line.slice(3)}</h2>`);
    else if (line.startsWith("### ")) out.push(`<h3>${line.slice(4)}</h3>`);
    else if (line.startsWith("- ")) {
      if (!list) {
        out.push("<ul>");
        list = true;
      }
      out.push(`<li>${line.slice(2)}</li>`);
    } else {
      out.push(`<p>${line}</p>`);
    }
  }
  if (list) out.push("</ul>");
  out.push("</body></html>");
  return out.join("\n");
}

await fs.mkdir(packageDir, { recursive: true });
await fs.copyFile(blueprintImagePath, imageCopyPath);

const customerValues = await importTable(customerPath, "Requirement", "A1:D82");
const ourValues = await importTable(oursPath, "Requirement Mapping", "A1:Q45");
const { requirements: customerRequirements, solutionOnly } = parseCustomerRows(customerValues);
const { map: ourMap, rows: ourRows } = parseOurRows(ourValues);
const comparisonRows = buildComparison(customerRequirements, ourMap);

const solutionRows = solutionOnly
  .filter((row) => normalize(row.requirement) || normalize(row.customerSolution))
  .map((row, index) => {
    const label = row.requirement === "Other solution note" ? row.customerSolution : row.requirement;
    const base = additionalRows.find((x) => normalizeKey(x[2]) === normalizeKey(label) || normalizeKey(x[2]) === normalizeKey(row.customerSolution));
    const est = base
      ? { category: base[5], min: base[6], max: base[7], recommended: base[8], phase: base[9], priority: base[10] }
      : estimateFromFit("", row.customerSolution, row.area, label, null);
    return {
      sequence: index + 1,
      source: "R001 Solution Note",
      area: row.area,
      no: "",
      requirement: label,
      customerYN: row.customerYN,
      customerSolution: row.customerSolution,
      ourMappedRequirement: "เพิ่มเป็น sub-scope / clarification",
      ourFit: "New / Clarification",
      customerVsOurs: "ลูกค้าเพิ่ม note ในคอลัมน์ Solution ต้องอธิบายเพิ่มใน Odoo",
      odooStandard: odooExplanation(row.area, label, row.customerSolution),
      apps: odooByArea[row.area]?.apps || "",
      models: odooByArea[row.area]?.models || "",
      standardCustomDecision: fitFromSolution(row.customerSolution, row.customerYN, ""),
      gapToAdd: customerSolutionNotes.get(row.customerSolution) || "เพิ่มเป็นประเด็น workshop",
      nextAction: nextAction("", row.customerSolution, row.area),
      mandayCategory: est.category,
      min: est.min,
      max: est.max,
      recommended: est.recommended,
      phase: est.phase,
      priority: est.priority,
      presentSequence: `Add-on ${index + 1}: ${label}`,
    };
  });

const addonRows = [
  ...additionalRows.map((row, index) => ({
    sequence: index + 1,
    source: row[0],
    area: row[1],
    no: "",
    requirement: row[2],
    customerYN: "",
    customerSolution: "",
    ourMappedRequirement: "เพิ่มจาก R001 solution note",
    ourFit: "New / Add-on",
    customerVsOurs: "ไม่ได้แยกชัดใน mapping เดิม ต้องเพิ่มบรรทัดอธิบาย",
    odooStandard: row[3],
    apps: odooByArea[row[1]]?.apps || "",
    models: odooByArea[row[1]]?.models || "",
    standardCustomDecision: row[4],
    gapToAdd: row[4],
    nextAction: "ยืนยันว่าอยู่ใน scope implementation หรือเป็น future phase",
    mandayCategory: row[5],
    min: row[6],
    max: row[7],
    recommended: row[8],
    phase: row[9],
    priority: row[10],
    presentSequence: `R001 Add-on ${index + 1}: ${row[2]}`,
  })),
  ...blueprintRows.map((row, index) => ({
    sequence: index + 1,
    source: row[0],
    area: row[1],
    no: "",
    requirement: row[2],
    customerYN: "",
    customerSolution: "",
    ourMappedRequirement: "เพิ่มจาก blueprint image",
    ourFit: "New / Flow Detail",
    customerVsOurs: "ภาพ blueprint เพิ่ม document/legacy handoff ที่ mapping เดิมยังไม่แตกละเอียด",
    odooStandard: row[3],
    apps: odooByArea[row[1]]?.apps || row[3],
    models: odooByArea[row[1]]?.models || "",
    standardCustomDecision: row[4],
    gapToAdd: row[4],
    nextAction: "ทำ workshop trace เอกสารเดิม -> Odoo document/model และตัดสินใจ sequence/report",
    mandayCategory: row[5],
    min: row[6],
    max: row[7],
    recommended: row[8],
    phase: row[9],
    priority: row[10],
    presentSequence: `Blueprint ${index + 1}: ${row[2]}`,
  })),
];

const allEstimateRows = [...comparisonRows, ...addonRows];
const summaryRows = summarize(allEstimateRows);
const total = summaryRows.reduce((acc, row) => {
  for (const key of ["items", "min", "max", "rec", "high", "custom", "standard", "report"]) acc[key] += row[key];
  return acc;
}, { items: 0, min: 0, max: 0, rec: 0, high: 0, custom: 0, standard: 0, report: 0 });

const workbook = Workbook.create();

const summary = workbook.worksheets.add("00 Executive Summary");
summary.showGridLines = false;
writeTable(summary, 0, 0, [["AMS R001 Comparison + Manday + Present Sequence", "", "", "", "", "", "", ""]]);
summary.getRange("A1:H1").format = { fill: "#5B1747", font: { bold: true, color: "#FFFFFF", size: 16 }, horizontalAlignment: "center" };
writeTable(summary, 2, 0, [
  ["Item", "Value", "อธิบาย"],
  ["Customer source", "Requirement on New System_R001.xlsx + TFI blueprint image", "ไฟล์ใหม่ของลูกค้าและรูป flow blueprint"],
  ["Our source", "AMS Workflow Mapping with Manday", "ไฟล์เดิมที่เราทำ mapping Odoo standard/custom"],
  ["R001 numbered requirements", customerRequirements.length, "รายการหลักจาก Excel ลูกค้า"],
  ["R001/Blueprint add-on rows", addonRows.length, "รายการที่ต้องอธิบายเพิ่มจาก Solution note และภาพ blueprint"],
  ["Recommended MD total if all included", total.rec, "รวมทั้ง base + add-on; ต้อง scope lock อีกครั้ง"],
  ["High priority items", total.high, "ส่วนใหญ่เป็น Accounting/Stock/MRP/Integration"],
], "#334155");
writeTable(summary, 11, 0, [
  ["Area", "Items", "Standard/Config MD", "Report/KPI MD", "Custom/Integration MD", "MD Min", "MD Max", "MD Recommended", "High Priority"],
  ...summaryRows.map((row) => [row.area, row.items, row.standard, row.report, row.custom, row.min, row.max, row.rec, row.high]),
  ["TOTAL", total.items, total.standard, total.report, total.custom, total.min, total.max, total.rec, total.high],
], "#5B1747");
summary.getRange(`A${summaryRows.length + 12}:I${summaryRows.length + 12}`).format = { fill: "#FDE68A", font: { bold: true }, borders: { preset: "all", style: "thin", color: "#D9D9D9" } };

const comp = workbook.worksheets.add("01 R001 vs Our Mapping");
comp.showGridLines = false;
const compHeaders = ["Seq", "Source", "Area", "No", "Customer Requirement", "Customer Y/N", "Customer Solution", "Our Existing Mapping", "Our Fit", "Compare Result", "Odoo Standard Explanation", "Apps / Modules", "Models / Objects", "Standard vs Custom", "What to Add / Explain", "Next Action", "MD Category", "MD Min", "MD Max", "MD Rec", "Phase", "Priority", "Present Sequence"];
writeTable(comp, 0, 0, matrixFromObjects(comparisonRows, compHeaders, (r) => [r.sequence, r.source, r.area, r.no, r.requirement, r.customerYN, r.customerSolution, r.ourMappedRequirement, r.ourFit, r.customerVsOurs, r.odooStandard, r.apps, r.models, r.standardCustomDecision, r.gapToAdd, r.nextAction, r.mandayCategory, r.min, r.max, r.recommended, r.phase, r.priority, r.presentSequence]));
comp.freezePanes.freezeRows(1);

const add = workbook.worksheets.add("02 Additions from R001 Blueprint");
add.showGridLines = false;
writeTable(add, 0, 0, matrixFromObjects(addonRows, compHeaders, (r) => [r.sequence, r.source, r.area, r.no, r.requirement, r.customerYN, r.customerSolution, r.ourMappedRequirement, r.ourFit, r.customerVsOurs, r.odooStandard, r.apps, r.models, r.standardCustomDecision, r.gapToAdd, r.nextAction, r.mandayCategory, r.min, r.max, r.recommended, r.phase, r.priority, r.presentSequence]));
add.freezePanes.freezeRows(1);

const blueprint = workbook.worksheets.add("03 Blueprint Flow Mapping");
blueprint.showGridLines = false;
writeTable(blueprint, 0, 0, [
  ["Blueprint Lane", "Customer step / Legacy code", "Odoo equivalent", "Standard support", "Custom risk", "Presentation note"],
  ["ขาย", "SP, FA, PR, IMR, SO, IV, BI", "CRM/Sales/Product/Invoice/Statement", "Sales/CRM/Invoice standard", "Legacy doc forms and forecast import", "เริ่มเล่าจากฝ่ายขาย เพราะเป็น trigger ของ demand"],
  ["ซื้อ", "รวบรวม PR, ออก PO", "Purchase/Approval/RFQ/PO", "Purchase standard", "Auto suggestion/grouping", "เชื่อมจาก Sales/MRP shortage ไป PO"],
  ["คลังวัตถุดิบ", "รับ RM, Tag, จ่าย RM, CP", "Inventory/Barcode/Owner stock", "Standard base", "Customer supplied material report/valuation", "ย้ำ owner stock และ lot/location"],
  ["วิศวกรรมการผลิต", "PCC", "BOM/Routing/Work Centers/PLM", "MRP/PLM standard", "PCC form/approval", "ก่อนผลิตต้อง master data พร้อม"],
  ["ควบคุมคุณภาพ", "ตรวจตามข้อกำหนด, COA", "Quality Check/COA report", "Quality standard base", "COA PDF/customer format", "COA เป็น output ให้ลูกค้า"],
  ["วางแผนผลิต", "PL, IS, WI", "MRP run/material issue/work instruction", "MRP standard", "IS/WI forms", "เล่าจุด buy/make และ material issue"],
  ["ผลิต", "ผลิตตามแผน, ผลิตเสร็จ, แก้ไข", "MO/WO/Rework/Scrap", "MRP work orders standard", "Exact rework route", "ตัดสินใจ QC pass/fail"],
  ["คลังสินค้าสำเร็จรูป/จัดส่ง", "PI, จัดส่งตาม SO", "FG receipt/Delivery", "Inventory delivery standard", "Delivery ticket/driver KPI", "จบ stock movement ก่อน invoice"],
  ["การเงิน/บัญชี", "PD, RR, PS, RE, Thai Tax", "Accounting/Payment/Receipt/Thai localization", "Accounting standard + l10n_th", "Legacy report/sequence/netting/multi ledger", "ปิด flow ด้วย accounting integrity"],
], "#5B1747");
const img = await fs.readFile(blueprintImagePath);
blueprint.images.add({
  dataUrl: `data:image/jpeg;base64,${img.toString("base64")}`,
  anchor: { from: { row: 12, col: 0 }, extent: { widthPx: 1260, heightPx: 280 } },
});

const details = workbook.worksheets.add("04 Odoo Function Detail");
details.showGridLines = false;
const detailRows = [
  ["Function Area", "Odoo Standard Function", "Standard Coverage", "Custom When", "Accounting/Stock Impact", "Key Workshop Question"],
  ["Multi-company / Consolidation", "Multi-company, inter-company, reports", "รองรับ company separation และ base reports", "Elimination, ownership %, translation adjustment", "สูง: Financial report", "ต้อง consolidation statutory หรือ management view"],
  ["Thai Tax / QR", "l10n_th, l10n_th_reports, account_qr_code_emv", "มี standard addon ใน source", "ฟอร์มเฉพาะ/format ส่งกรม/ธนาคารนอก standard", "สูง: VAT/Tax invoice", "รูปแบบภาษีและ QR ที่ใช้จริงคืออะไร"],
  ["Budget Control", "Analytic Budget, Approvals", "Budget tracking standard", "Hard lock PR/PO/Invoice over budget", "กลาง/สูง: commitment", "ต้อง warning หรือ block"],
  ["Cash Forecast", "AP/AR aging, cash flow statement", "มี actual/due data", "Forecast รวม PR/PO/AP/AR แบบ future projection", "กลาง: planning report", "สูตร forecast และ horizon"],
  ["Customer Forecast/API", "MPS/MRP, Sales", "รับ forecast/manual planning ได้", "External automotive PO/forecast import/API", "สูง: demand planning", "file/API format และรอบ update"],
  ["Supplier Evaluation", "Purchase/vendor pricelist", "เก็บ vendor/price/lead time", "Weighted scorecard/auto suggestion", "ต่ำ/กลาง", "คะแนนและน้ำหนักคืออะไร"],
  ["Customer Supplied Material", "Owner stock, locations, lots", "แยก owner/location/lot ได้", "Report/valuation exclusion/custom route", "สูง: stock valuation", "ของลูกค้าเข้าบัญชี stock หรือ off-balance"],
  ["COA", "Quality point/check", "เก็บผลตรวจได้", "COA PDF per customer/product/spec", "กลาง: quality output", "COA format และ spec source"],
  ["OEE/OPE/DPPM", "MRP Workorder, Maintenance, Quality, Returns", "มี source data", "สูตร KPI/report/dashboard", "กลาง: KPI", "สูตรที่บริษัท approve คืออะไร"],
  ["WIP/Variance", "MRP/stock valuation/landed cost", "track WIP/FG/valuation base", "WIP value without location, variance allocation to COG/WIP/FG", "สูงมาก", "valuation method และ posting rule"],
  ["Legacy document codes", "Sequences/reports/actions", "sequence/report standard base", "ต้อง match SP/FA/IMR/PCC/COA/WI/PI/BI/PD/RR/PS/RE", "กลาง/สูงตามเอกสาร", "เอกสารใดต้องคงเลขเดิมและ migrate"],
];
writeTable(details, 0, 0, detailRows, "#5B1747");

const manday = workbook.worksheets.add("05 Manday Summary");
manday.showGridLines = false;
writeTable(manday, 0, 0, [["AMS R001 Manday Summary", "", "", "", "", "", "", "", ""]]);
manday.getRange("A1:I1").format = { fill: "#5B1747", font: { bold: true, color: "#FFFFFF", size: 16 }, horizontalAlignment: "center" };
writeTable(manday, 2, 0, [
  ["Scope Block", "Items", "MD Min", "MD Max", "MD Recommended", "Purpose"],
  ["R001 numbered requirements", comparisonRows.length, comparisonRows.reduce((a, r) => a + r.min, 0), comparisonRows.reduce((a, r) => a + r.max, 0), comparisonRows.reduce((a, r) => a + r.recommended, 0), "Base requirement mapping"],
  ["R001 solution/blueprint additions", addonRows.length, addonRows.reduce((a, r) => a + r.min, 0), addonRows.reduce((a, r) => a + r.max, 0), addonRows.reduce((a, r) => a + r.recommended, 0), "New explanation/gaps from customer file and image"],
  ["TOTAL if all included", total.items, total.min, total.max, total.rec, "Initial estimate before scope lock"],
], "#334155");
writeTable(manday, 8, 0, [
  ["Area", "Items", "Standard/Config MD", "Report/KPI MD", "Custom/Integration MD", "MD Min", "MD Max", "MD Recommended", "High Priority"],
  ...summaryRows.map((row) => [row.area, row.items, row.standard, row.report, row.custom, row.min, row.max, row.rec, row.high]),
  ["TOTAL", total.items, total.standard, total.report, total.custom, total.min, total.max, total.rec, total.high],
]);

const present = workbook.worksheets.add("06 Present Sequence");
present.showGridLines = false;
const presentRows = [
  ["Seq", "Start / End", "Slide/Sheet", "Talk Track", "What to Show", "Decision / Output"],
  [1, "Start", "00 Executive Summary", "เปิดว่า R001 เป็นไฟล์ใหม่ที่ต้องเทียบกับ mapping เดิมและ blueprint", "Summary source + MD total", "เห็น scope และ source ตรงกัน"],
  [2, "Read method", "03 Blueprint Flow Mapping", "อธิบาย blueprint จากซ้ายไปขวาและ lane ตามแผนก", "ภาพ TFI blueprint + lane mapping", "ทุกคนอ่าน flow แบบเดียวกัน"],
  [3, "Sales trigger", "01 R001 vs Our Mapping", "เริ่มที่ Sales: RFQ/Quotation/SO/Customer PO/Forecast/API", "Sales rows + SP/FA/IMR/SO", "ยืนยัน customer forecast/API scope"],
  [4, "Procurement", "01/02", "ไล่ PR/RFQ/PO/Blanket/Supplier score/Cost up-down", "Procurement rows", "ตัดสินใจ supplier score และ approval suggestion"],
  [5, "Warehouse RM", "03 Blueprint Flow Mapping", "รับวัตถุดิบ, Tag, Lot, Shelf, CP customer material", "RM/CP mapping", "ยืนยัน owner stock และ valuation"],
  [6, "Engineering + QC", "04 Odoo Function Detail", "PCC/BOM/Routing/COA/Quality point", "PCC + COA rows", "ยืนยัน COA format และ product master owner"],
  [7, "Planning + Production", "01/02", "MRP/MPS, IS, WI, MO, WO, Rework/Scrap, OEE/OPE/DPPM", "MRP/Manufacturing rows", "ยืนยัน KPI formula และ rework route"],
  [8, "FG + Delivery", "03 Blueprint Flow Mapping", "PI รับเข้าคลัง, delivery by SO, route/cost/fleet", "FG/Logistics mapping", "ยืนยัน ticket/driver evaluation"],
  [9, "Accounting close", "04 Odoo Function Detail", "IV/BI/PD/RR/PS/RE, Thai Tax, QR, netting, multi ledger", "Accounting function detail", "ยืนยัน standard localization vs custom reports"],
  [10, "Manday", "05 Manday Summary", "แยก base requirement กับ R001/blueprint additions", "MD Min/Max/Recommended", "ล็อก priority และ phase"],
  [11, "End", "07 Workshop Questions", "ปิดด้วยคำถามที่ต้องตอบก่อนทำ UAT/final quotation", "Question list", "Action owner + next workshop"],
];
writeTable(present, 0, 0, presentRows, "#5B1747");

const questions = workbook.worksheets.add("07 Workshop Questions");
questions.showGridLines = false;
writeTable(questions, 0, 0, [
  ["Area", "Question", "Why it matters", "Owner to confirm"],
  ["Accounting", "Consolidation ต้องเป็น statutory consolidation หรือ management view?", "ตัดสินใจ standard multi-company vs custom consolidation", "Finance"],
  ["Accounting", "Budget control ต้อง warning หรือ hard block PR/PO?", "กำหนด custom guard และ risk", "Finance/Purchasing"],
  ["Accounting", "Multi Ledger หมายถึงอะไร: journal, company, branch, หรือ parallel ledger?", "กระทบ design ใหญ่", "Finance"],
  ["Accounting", "Thai tax/QR ใช้ format ใดและต้อง export ยื่นหน่วยงานหรือไม่?", "ตัดสินใจ standard localization vs report custom", "Finance"],
  ["Sales", "Customer PO/Forecast automotive มาเป็น Excel, EDI, API หรือ manual?", "กำหนด integration manday", "Sales/Planning"],
  ["Sales", "Sales framework agreement by BU ต้องมี approval/price control อย่างไร?", "อาจต้อง custom contract model", "Sales"],
  ["Procurement", "Supplier scorecard มี factor และ weight อะไรบ้าง?", "กำหนด KPI/report", "Purchasing/QC"],
  ["Warehouse", "Customer supplied material ต้อง valuate หรือ off-balance?", "กระทบ stock valuation/accounting", "Warehouse/Finance"],
  ["Quality", "COA format ต่อ customer/product/spec เป็นอย่างไร?", "กำหนด report custom", "QC"],
  ["Manufacturing", "OEE/OPE/DPPM สูตร approved คืออะไร?", "กำหนด dashboard/report", "Production/QC"],
  ["Manufacturing", "WIP จะ track ด้วย location หรือ process only?", "กระทบ stock/accounting integrity", "Production/Finance"],
  ["Cross-system", "Access/BP Soft/Express/Excel ตัวใดต้อง migrate และตัวใด retire?", "กำหนด data migration/integration scope", "IT/All owners"],
]);

const raw = workbook.worksheets.add("08 Raw Customer R001");
raw.showGridLines = false;
writeTable(raw, 0, 0, customerValues.map((row) => [row[0] ?? "", row[1] ?? "", row[2] ?? "", row[3] ?? ""]), "#334155");

for (const sheet of [summary, comp, add, blueprint, details, manday, present, questions, raw]) {
  const used = sheet.getUsedRange();
  used.format.wrapText = true;
  used.format.verticalAlignment = "top";
  used.format.autofitRows();
}

summary.getRange("A1:I40").format.columnWidthPx = 150;
summary.getRange("A1:A40").format.columnWidthPx = 260;
summary.getRange("C1:C40").format.columnWidthPx = 340;
comp.getRange("A1:W120").format.columnWidthPx = 140;
comp.getRange("E1:E120").format.columnWidthPx = 360;
comp.getRange("G1:K120").format.columnWidthPx = 280;
comp.getRange("O1:P120").format.columnWidthPx = 300;
add.getRange("A1:W80").format.columnWidthPx = 140;
add.getRange("E1:E80").format.columnWidthPx = 360;
add.getRange("K1:P80").format.columnWidthPx = 280;
blueprint.getRange("A1:F60").format.columnWidthPx = 220;
details.getRange("A1:F80").format.columnWidthPx = 240;
manday.getRange("A1:I80").format.columnWidthPx = 150;
manday.getRange("A1:A80").format.columnWidthPx = 270;
manday.getRange("A1:I1").format.rowHeightPx = 34;
manday.getRange("A3:I6").format.rowHeightPx = 42;
manday.getRange("A9:I25").format.rowHeightPx = 28;
present.getRange("A1:F40").format.columnWidthPx = 220;
questions.getRange("A1:D40").format.columnWidthPx = 280;
raw.getRange("A1:D100").format.columnWidthPx = 260;

const preview = await workbook.render({ sheetName: "05 Manday Summary", range: "A1:I25", scale: 1, format: "png" });
await fs.writeFile(previewPath, new Uint8Array(await preview.arrayBuffer()));
const errors = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 100 }, summary: "final formula error scan" });
console.log(errors.ndjson);
const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(outputXlsx);

const guide = `# AMS R001 Comparison Presentation Guide

## เริ่มอ่านจากอะไร

- เริ่มจากไฟล์ Excel: 01_AMS_R001_Comparison_Manday_Sequence.xlsx
- เปิด sheet 00 Executive Summary เพื่อบอก scope และตัวเลขรวม
- ต่อด้วย sheet 03 Blueprint Flow Mapping เพื่ออธิบายภาพ TFI blueprint จากซ้ายไปขวา
- ใช้ sheet 01 R001 vs Our Mapping เพื่อเทียบ requirement ลูกค้ากับ mapping เดิมของเรา
- ใช้ sheet 02 Additions from R001 Blueprint เพื่อคุยรายการที่เพิ่มจาก Solution note และภาพ blueprint
- ปิดด้วย sheet 05 Manday Summary และ 06 Present Sequence

## ประเด็นที่เพิ่มจากไฟล์ลูกค้า R001

- ลูกค้าเพิ่ม Solution note เช่น Multi Company, Need Budget APP, Need Project APP, Use Landed Cost, Use Action WIP, MPS, API, RMA
- ต้องอธิบายเพิ่มว่า Solution เหล่านี้ใน Odoo คือ standard/config/custom ระดับไหน
- ภาพ blueprint เพิ่มเอกสาร legacy และ handoff เช่น SP, FA, IMR, PCC, COA, IS, WI, PI, IV, BI, PD, RR, PS, RE
- ต้อง map เอกสารเดิมเหล่านี้กับ Odoo model/document ก่อนทำ UAT

## ลำดับ Present แบบละเอียด

- 1. เปิดด้วย objective: เทียบ R001 กับ mapping เดิมและ identify สิ่งที่ต้องเพิ่ม
- 2. อธิบายวิธีอ่าน blueprint: lane คือแผนก, ลูกศรคือ handoff, รหัสเอกสารคือ legacy document ที่ต้อง map กับ Odoo
- 3. เริ่ม Sales: RFQ/Quotation/SO/Customer PO/Forecast/API
- 4. ต่อ Procurement: PR/RFQ/PO/Blanket/Supplier evaluation
- 5. ต่อ Warehouse RM: Receipt, Tag, Lot, Shelf, Customer supplied material
- 6. ต่อ Engineering/QC: PCC, BOM/Routing, Quality Check, COA
- 7. ต่อ Planning/Production: MPS/MRP, IS, WI, MO, WO, Rework/Scrap, OEE/OPE/DPPM
- 8. ต่อ FG/Delivery: PI, Delivery by SO, route/cost/fleet
- 9. ปิด Accounting: Invoice, Billing, Payment, Receipt, Thai Tax, QR, Netting, Multi Ledger
- 10. Review Manday: แยก base requirement กับ add-on จาก R001/blueprint
- 11. ปิดด้วย Workshop Questions และ action owner

## วิธีอธิบาย Standard vs Custom

- Standard: ใช้ Odoo module โดย config/master data ได้ เช่น Sales, Purchase, Inventory, MRP, Quality, Accounting, Thai localization
- Config + Report: standard มีข้อมูล แต่ต้องจัด report/form/dashboard เฉพาะบริษัท เช่น COA, BI, stock aging, sales dashboard
- Custom / Integration: standard ไม่มี business rule หรือมี external file/API เช่น customer forecast API, supplier scorecard weighted, budget hard lock, netting wizard
- Accounting/Stock Critical: WIP, valuation, cost variance, customer supplied material ต้อง review design ก่อน custom

## Manday หมายถึงอะไร

- Manday เป็น initial estimate สำหรับ workshop/planning
- MD Min คือกรณี requirement ชัดและใช้ standard/config ได้มาก
- MD Max คือกรณีต้อง revise, build report/custom, UAT fix หรือมี data gap
- MD Recommended คือค่ากลางใช้คุย priority และ phase
- ตัวเลขยังไม่ใช่ fixed quotation จนกว่าจะ scope lock
`;

await fs.writeFile(guideMd, guide, "utf8");
await fs.writeFile(guideHtml, htmlFromMarkdown(guide), "utf8");
await fs.writeFile(readmePath, `# AMS R001 Compare Package

เปิดตามลำดับ:

1. 00_README_START_HERE_TH.md
2. 01_AMS_R001_Comparison_Manday_Sequence.xlsx
3. 02_AMS_R001_Presentation_Guide_TH.md
4. 03_AMS_R001_Presentation_Guide_TH.html
5. 04_Manday_Summary_Preview.png
6. 05_TFI_Blueprint_Reference.jpg

ไฟล์ Excel คือไฟล์หลัก มี sheet:

- 00 Executive Summary
- 01 R001 vs Our Mapping
- 02 Additions from R001 Blueprint
- 03 Blueprint Flow Mapping
- 04 Odoo Function Detail
- 05 Manday Summary
- 06 Present Sequence
- 07 Workshop Questions
- 08 Raw Customer R001

ตัวเลข Manday เป็น initial estimate สำหรับ planning/workshop ยังไม่ใช่ fixed quotation
`, "utf8");

console.log(JSON.stringify({
  packageDir,
  outputXlsx,
  guideMd,
  guideHtml,
  previewPath,
  imageCopyPath,
  customerRequirementRows: customerRequirements.length,
  addOnRows: addonRows.length,
  totalRecommendedManday: total.rec,
}, null, 2));
