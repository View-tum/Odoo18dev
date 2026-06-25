import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const baseDir = "C:/365_project/TheCool18e/Dev";
const outDir = `${baseDir}/output/ams_workflow`;
const screenshotsDir = `${outDir}/screenshots`;
const sourceJsonPath = `${baseDir}/tmp/ams_workflow_extract_clean.json`;
const verifyPath = `${outDir}/ams_current_verification.json`;

const areaNames = {
  "ACCOUNTING AND FINANCE": "Accounting & Finance",
  Sale: "Sales",
  PROCUREMENT: "Procurement",
  "WAREHOUSE AND LOGISTIC": "Warehouse & Logistic",
  MANUFACTURING: "Manufacturing",
};

const coverage = [
  ["Analytic Accounting, multi-company, accounting reports, spreadsheet dashboards. AMS has Business Unit and Branch analytic plans.", "Accounting, Analytic Accounting, Spreadsheet Dashboard", "account.move, account.analytic.account, account.report", "Config", "Use analytic dimensions first. Custom only if Branch/BU must become hard mandatory fields on every transaction.", "10_business_unit_analytics.png"],
  ["Financial statements, accounting reports, spreadsheet dashboards, pivots and export can support management ratios.", "Accounting Reports, Spreadsheet Dashboard", "account.report, spreadsheet", "Config/Report", "Company-specific ratio formulas and auto-refresh packs should be implemented as spreadsheet dashboard or custom report.", "12_accounting_dashboard.png"],
  ["This checkout does not expose a dedicated consolidation app. Standard coverage is multi-company, inter-company rules and spreadsheet/report consolidation.", "Multi-company, Inter-company, Spreadsheet", "res.company, account.move", "Gap", "Statutory consolidation with eliminations, ownership percentage and translation adjustments needs custom or external consolidation design.", "12_accounting_dashboard.png"],
  ["Bank journals, statement imports, reconciliation widget and multi-currency AR/AP/BANK are standard.", "Accounting, Bank Statement Import", "account.journal, account.bank.statement, account.move", "Standard", "Map the real bank file format. A non-standard bank format may need an import connector/template.", "12_accounting_dashboard.png"],
  ["AP/AR due dates and payment terms are standard. PO commitments exist in purchase data.", "Accounting, Purchase, Spreadsheet Dashboard", "account.move, purchase.order, approval.request", "Custom Report", "A single cash forecast combining PR, PO, AP due and AR expected receipts needs a custom dashboard/report.", "12_accounting_dashboard.png"],
  ["Budgets and analytic budgets are standard. AMS has account_budget installed and analytic dimensions configured.", "Budget Management, Analytic Accounting, Approvals", "account.budget, account.analytic.account", "Config + Custom Guard", "Alert/lock PR or PO over budget requires approval rule, automated action or custom constraint.", "11_approval_category.png"],
  ["Project plus analytic accounting and budget can track investment/capital spending.", "Project, Budget, Analytic Accounting", "project.project, account.analytic.account", "Standard/Config", "Multi-step CAPEX approval or automatic asset capitalization may need extra workflow design.", "10_business_unit_analytics.png"],
  ["BoM cost, work center cost, manufacturing accounting and stock valuation provide the data source.", "MRP Accounting, Stock Accounting, Spreadsheet Dashboard", "mrp.production, mrp.bom, stock.valuation.layer", "Config/Report", "Detailed standard-vs-actual variance by operation, yield and waste should be a custom dashboard/report.", "06_mrp_bom_routing.png"],
  ["Stock valuation supports FIFO, AVCO and standard cost; MRP accounting posts production values.", "Stock Accounting, MRP Accounting", "stock.valuation.layer, account.move, mrp.production", "Partial", "Variance allocation to COGS, FG inventory and WIP is accounting-sensitive and needs a controlled custom design.", "12_accounting_dashboard.png"],
  ["MRP and work orders track production progress; valuation by stock move/location is standard.", "MRP Work Orders, Stock Valuation", "mrp.workorder, mrp.production, stock.move", "Partial", "WIP quantity/value by process without stock locations needs a custom report from MO, WO and cost data.", "07_mrp_manufacturing_order.png"],
  ["Multi-currency AR/AP/BANK is standard. AMS activated THB, CNY, EUR, JPY, SGD and USD.", "Accounting Multi-currency", "res.currency, account.move, account.payment", "Standard", "Configure exchange rates and bank journals per currency before live operation.", "12_accounting_dashboard.png"],

  ["CRM opportunities, quotations, sales analysis and won/lost status are standard. AMS has quotation S00001.", "CRM, Sales", "crm.lead, sale.order", "Standard/Config", "Auto costing quotation from BOM template is a custom/PLM design if the structure must be controlled.", "02_sales_quotation.png"],
  ["Customer reference on SO, routes, replenishment and MRP demand integration are standard.", "Sales, Inventory, MRP", "sale.order, stock.rule, mrp.production", "Standard + Integration", "Automotive customer PO or rolling forecast file import may require EDI/import custom work.", "02_sales_quotation.png"],
  ["Delivery status, invoice status, sales analysis and stock picking data are standard.", "Sales, Inventory, Invoicing", "sale.order, stock.picking, account.move", "Custom KPI", "Forecast-to-invoice and request-vs-delivery percentages need a company-specific KPI definition.", "02_sales_quotation.png"],
  ["Sales analysis plus margin modules and analytic dimensions support GP by BU.", "Sales, Sales Margin, Analytic Accounting", "sale.order.line, account.analytic.account", "Standard/Config", "Make BU analytic mandatory if management reports must always reconcile.", "02_sales_quotation.png"],
  ["Branch GP can use analytic Branch or company/warehouse structure.", "Sales Margin, Analytic Accounting", "sale.order.line, account.analytic.account", "Config", "A hard Branch field on all flows needs custom field/rules if analytic dimensions are not enough.", "10_business_unit_analytics.png"],
  ["SO demand, replenishment, MPS/MRP and forecasted inventory are standard.", "Sales, MRP, Inventory", "sale.order, mrp.production, stock.warehouse.orderpoint", "Standard/Config", "Complex customer forecast import or seasonality logic may need custom import/dashboard.", "05_inventory_reordering_rule.png"],
  ["UoM, sales quantity, vendor minimum quantity, packaging and reordering multiples are standard pieces.", "Sales, Purchase, Inventory, MRP", "product.template, product.supplierinfo, stock.warehouse.orderpoint", "Partial", "Blocking SO by MOQ across master, stock and purchase units needs custom validation.", "02_sales_quotation.png"],
  ["Quotation templates, pricelists, analytic BU and recurring contract options cover part of the need.", "Sales, Subscriptions/Contracts by configuration", "sale.order, product.pricelist, account.analytic.account", "Partial", "Sales framework agreement by BU may need a custom contract model if templates are insufficient.", "02_sales_quotation.png"],
  ["CRM and Contacts can store customer profile, activities, notes, tags and opportunities.", "CRM, Contacts", "crm.lead, res.partner, mail.activity", "Standard/Config", "Structured mission, vision, strategy and performance fields may need Studio/custom fields.", "01_home_apps.png"],
  ["Useful standard add-ons include activities, quotation templates, pricelists, dashboards and spreadsheet analysis.", "Sales/CRM ecosystem", "various", "TBD", "Define the exact use case before custom work.", "01_home_apps.png"],

  ["RFQ, purchase agreements, vendor pricelists and purchase analysis are standard. AMS has RFQ P00002 and BO00001.", "Purchase, Purchase Agreements", "purchase.order, purchase.requisition, product.supplierinfo", "Standard/Config", "Target price scoring or vendor win-rate needs a custom scorecard/report.", "03_purchase_rfq.png"],
  ["Vendor data, PO history, receipt history and price records provide the standard data source.", "Purchase, Inventory, Spreadsheet", "res.partner, purchase.order, stock.picking", "Partial", "Weighted supplier scorecard needs custom dashboard/report.", "03_purchase_rfq.png"],
  ["Scheduled dates, receipt dates, payment terms and purchase prices are standard.", "Purchase, Inventory, Accounting", "purchase.order, stock.picking, account.move", "Config/Report", "Define scoring thresholds for delivery, price and credit before building reports.", "03_purchase_rfq.png"],
  ["Purchase analysis and vendor pricelist history support basic cost trend review.", "Purchase Reporting, Product Cost", "purchase.order.line, product.supplierinfo", "Custom Report", "Cost movement by item/vendor/period versus target/last purchase needs a custom dashboard/report.", "03_purchase_rfq.png"],
  ["Vendor lead time, vendor minimum quantity, reordering rules and MRP procurement are standard.", "Purchase, Inventory, MRP", "product.supplierinfo, stock.rule, mrp.production", "Standard/Config", "Requires complete supplierinfo, routes and lead-time master data.", "05_inventory_reordering_rule.png"],
  ["Approvals app, purchase approval and RFQ/PO workflow are standard. AMS has purchase request approval category.", "Approvals, Purchase", "approval.category, approval.request, purchase.order", "Standard + Custom KPI", "Auto suggestion before approval using budget/vendor score needs custom logic.", "11_approval_category.png"],
  ["Purchase Agreements and Blanket Orders are standard. AMS has BO00001.", "Purchase Agreements", "purchase.requisition", "Standard", "Configure approval, expiry and price-break policy.", "04_purchase_blanket_agreement.png"],
  ["Additional standard options include vendor pricelists, 3-way matching, replenishment and purchase dashboards.", "Purchase ecosystem", "various", "TBD", "Define details before custom work.", "03_purchase_rfq.png"],

  ["Lots/serials, traceability and stock moves are standard. AMS products use lot tracking where relevant.", "Inventory", "stock.lot, stock.move.line, product.template", "Standard", "Set tracking policy and label policy per product.", "06_mrp_bom_routing.png"],
  ["Storage locations, shelves, putaway rules and removal strategies are standard. AMS has shelf/QC/WIP locations.", "Inventory Locations", "stock.location", "Standard/Config", "Advanced capacity or bin optimization may need WMS customization.", "05_inventory_reordering_rule.png"],
  ["Barcode app supports receipts, delivery, inventory and production/quality bridge modules.", "Barcode, Inventory, MRP, Quality", "stock_barcode, stock.picking, mrp.production", "Standard", "Test real scanners, labels and mobile devices.", "01_home_apps.png"],
  ["Forecasted inventory, replenishment and reordering rules are standard. AMS has RM1 min/max rule.", "Inventory Forecast, MRP, Purchase", "stock.warehouse.orderpoint, stock.quant, purchase.order", "Partial", "Slow/dead stock aging and turnover dashboard needs a custom/spreadsheet KPI.", "05_inventory_reordering_rule.png"],
  ["Reordering Rules support min, max, multiple quantity, trigger and warehouse.", "Inventory Replenishment", "stock.warehouse.orderpoint", "Standard", "Configure per SKU and warehouse.", "05_inventory_reordering_rule.png"],
  ["Routes, delivery methods and Fleet provide standard coverage for logistics basics.", "Inventory Routes, Delivery Costs, Fleet", "stock.route, delivery.carrier, fleet.vehicle", "Partial", "Driver evaluation and ticket workflow need custom or Helpdesk/Project integration.", "13_delivery_methods.png"],

  ["MRP, work orders, replenishment, SO demand and purchase procurement are standard. AMS has MO WH/MO/00001.", "MRP, Inventory, Purchase, Sales", "mrp.production, stock.move, purchase.order", "Standard/Config", "Requires routes, BoM, work centers and lead times before go-live.", "07_mrp_manufacturing_order.png"],
  ["Work orders track consumed quantity, produced quantity, duration, scrap and productivity.", "MRP Work Orders", "mrp.workorder, stock.scrap, mrp.production", "Standard/Config", "Detailed waste and downtime reasons may need extra fields/report.", "07_mrp_manufacturing_order.png"],
  ["Shop Floor and Work Orders track status by operation. AMS has 7 work centers and 21 operations.", "MRP Work Orders / Shop Floor", "mrp.workcenter, mrp.routing.workcenter, mrp.workorder", "Standard", "Validate tablet/operator flow on the shop floor.", "09_work_centers.png"],
  ["Work center reports and productivity data support availability/performance/quality data sources.", "MRP Work Centers, Reporting", "mrp.workcenter, mrp.workorder", "Partial", "OPE formula is company-specific and should be custom/spreadsheet dashboard.", "09_work_centers.png"],
  ["OEE target, time efficiency and workorder productivity are standard concepts.", "MRP Work Centers", "mrp.workcenter, mrp.workorder", "Standard/Config", "Configure work center capacity, time efficiency and downtime capture.", "09_work_centers.png"],
  ["BoM, components and operations are standard. AMS has BOM AMS.400 REV 00 with 21 routing operations.", "MRP BoM/Routing", "mrp.bom, mrp.bom.line, mrp.routing.workcenter", "Standard", "Create semi-finished products and child BoMs for full multi-level production.", "06_mrp_bom_routing.png"],
  ["PLM/ECO and BoM revisions are standard. AMS has mrp_plm installed.", "PLM, MRP", "mrp.eco, mrp.bom", "Partial", "Quotation BOM and PPAP document workflow may need custom process or Documents/Sign integration.", "06_mrp_bom_routing.png"],
  ["Barcode MRP and Barcode Quality MRP bridge modules support scan points in production/quality.", "Barcode + MRP + Quality", "stock_barcode_mrp, quality_mrp_workorder", "Standard/Config", "Design barcode labels and scan points per operation.", "08_quality_point.png"],
  ["Quality Checks, Quality Alerts and Returns provide the data source.", "Quality, Inventory Returns, Sales", "quality.alert, quality.check, stock.return.picking", "Custom KPI", "DPPM formula by customer/product/period needs custom dashboard/report.", "08_quality_point.png"],
];

function extractRequirements(source) {
  const sheet = source.find((s) => s.sheet === "Follow on Requirement");
  const rows = sheet.nonempty_rows_preview;
  const result = [];
  let currentArea = "";
  for (const row of rows) {
    const [colA, colB, colC] = row.values;
    if (typeof colA === "string" && areaNames[colA.trim()]) {
      currentArea = areaNames[colA.trim()];
      continue;
    }
    if (typeof colA === "number" && colB) {
      result.push({
        area: currentArea,
        no: colA,
        requirement: String(colB),
        demoNote: colC ? String(colC) : "",
      });
    }
  }
  return result.map((req, i) => ({
    ...req,
    coverage: coverage[i]?.[0] ?? "",
    apps: coverage[i]?.[1] ?? "",
    models: coverage[i]?.[2] ?? "",
    fit: coverage[i]?.[3] ?? "TBD",
    custom: coverage[i]?.[4] ?? "",
    screenshot: coverage[i]?.[5] ?? "",
  }));
}

function styleHeader(range, fill = "#7030A0") {
  range.format = {
    fill,
    font: { bold: true, color: "#FFFFFF" },
    wrapText: true,
  };
}

function styleBody(range) {
  range.format = {
    wrapText: true,
    borders: { preset: "all", style: "thin", color: "#D9E2F3" },
  };
}

function sanitizeForReport(text) {
  return String(text ?? "").replaceAll("???", "").replaceAll("�", "");
}

function escapeHtml(text) {
  return sanitizeForReport(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function imageDataUrl(filePath) {
  return fs.readFile(filePath).then((buf) => `data:image/png;base64,${buf.toString("base64")}`);
}

const source = JSON.parse(await fs.readFile(sourceJsonPath, "utf8"));
const verification = JSON.parse(await fs.readFile(verifyPath, "utf8"));
const rows = extractRequirements(source);

if (rows.length !== coverage.length) {
  throw new Error(`Requirement count mismatch: source=${rows.length}, coverage=${coverage.length}`);
}

await fs.mkdir(outDir, { recursive: true });

const workbook = Workbook.create();
const summary = workbook.worksheets.add("Summary");
const mapping = workbook.worksheets.add("Requirement Mapping");
const apps = workbook.worksheets.add("Standard Apps");
const evidence = workbook.worksheets.add("Odoo Screenshots");
const backlog = workbook.worksheets.add("Custom Backlog");

for (const sheet of [summary, mapping, apps, evidence, backlog]) {
  sheet.showGridLines = false;
}

summary.getRange("A1:F1").merge();
summary.getRange("A1").values = [["AMS Workflow vs Standard Odoo 18 Enterprise Mapping"]];
summary.getRange("A1").format = { fill: "#5B1747", font: { bold: true, color: "#FFFFFF", size: 16 } };
summary.getRange("A3:B16").values = [
  ["Database", verification.database],
  ["URL", verification.url],
  ["Login", verification.login],
  ["Installed standard modules", verification.installed_modules],
  ["Custom modules installed", verification.custom_modules_installed],
  ["Business Unit analytic accounts", verification.business_units],
  ["Branch analytic accounts", verification.branch_analytics],
  ["Work centers", verification.work_centers],
  ["Raw materials", verification.raw_materials],
  ["BOM count", verification.bom_count],
  ["Routing operations", verification.routing_operations],
  ["Quality points", verification.quality_points],
  ["RFQ / Quotation / MO", `${verification.rfq_count} / ${verification.quotation_count} / ${verification.mo_count}`],
  ["Reordering rules", verification.reordering_rules],
];
styleHeader(summary.getRange("A3:B3"), "#305496");
styleBody(summary.getRange("A3:B16"));
summary.getRange("A18:F18").values = [["Standard vs Pain Point"]];
styleHeader(summary.getRange("A18:F18"), "#305496");
summary.getRange("A19:F22").values = [
  ["Standard First", "Use standard Odoo apps and configuration first: Accounting, Sales/CRM, Purchase, Inventory, Barcode, MRP, Quality, Maintenance, Budget, Project, Delivery, Fleet and Spreadsheet dashboards.", null, null, null, null],
  ["Pain Point", "Several needs are company-specific KPIs or control policies: budget lock, supplier scorecard, DPPM, cash forecast, cost variance allocation and external forecast/PO import.", null, null, null, null],
  ["Custom Boundary", "Custom only reports, validation, integrations and approval guards that standard Odoo does not cover after configuration.", null, null, null, null],
  ["Integrity Note", "Do not custom-post stock valuation or accounting entries with SQL. Design FIFO/AVCO, WIP and COGS policy before go-live.", null, null, null, null],
];
for (let r = 19; r <= 22; r += 1) {
  summary.getRange(`A${r}:F${r}`).merge(true);
}
styleBody(summary.getRange("A19:F22"));
summary.getRange("A:A").format.columnWidthPx = 220;
summary.getRange("B:F").format.columnWidthPx = 170;

const mappingHeader = [["Area", "No.", "Requirement from Excel", "Demo note", "Standard Odoo function", "Apps / Modules", "Models / Objects", "Fit", "Pain Point / Custom Needed", "Odoo screenshot"]];
mapping.getRange("A1:J1").values = mappingHeader;
styleHeader(mapping.getRange("A1:J1"), "#5B1747");
mapping.getRangeByIndexes(1, 0, rows.length, 10).values = rows.map((r) => [
  r.area,
  r.no,
  r.requirement,
  r.demoNote,
  r.coverage,
  r.apps,
  r.models,
  r.fit,
  r.custom,
  r.screenshot,
]);
styleBody(mapping.getRangeByIndexes(0, 0, rows.length + 1, 10));
mapping.freezePanes.freezeRows(1);
mapping.getRange("A:A").format.columnWidthPx = 150;
mapping.getRange("B:B").format.columnWidthPx = 50;
mapping.getRange("C:C").format.columnWidthPx = 420;
mapping.getRange("D:D").format.columnWidthPx = 300;
mapping.getRange("E:G").format.columnWidthPx = 280;
mapping.getRange("H:H").format.columnWidthPx = 130;
mapping.getRange("I:I").format.columnWidthPx = 330;
mapping.getRange("J:J").format.columnWidthPx = 230;

const requiredRows = Object.entries(verification.required_modules).map(([module, installed]) => [
  module,
  installed ? "Installed" : "Missing",
]);
apps.getRange("A1:B1").values = [["Standard module", "Status"]];
styleHeader(apps.getRange("A1:B1"), "#305496");
apps.getRangeByIndexes(1, 0, requiredRows.length, 2).values = requiredRows;
styleBody(apps.getRangeByIndexes(0, 0, requiredRows.length + 1, 2));
apps.getRange("A:A").format.columnWidthPx = 260;
apps.getRange("B:B").format.columnWidthPx = 140;

const screenshotRows = [
  ["01", "Home apps", "01_home_apps.png"],
  ["02", "Sales Quotation", "02_sales_quotation.png"],
  ["03", "Purchase RFQ", "03_purchase_rfq.png"],
  ["04", "Purchase Blanket Agreement", "04_purchase_blanket_agreement.png"],
  ["05", "Inventory Reordering Rule", "05_inventory_reordering_rule.png"],
  ["06", "MRP BOM/Routing", "06_mrp_bom_routing.png"],
  ["07", "Manufacturing Order", "07_mrp_manufacturing_order.png"],
  ["08", "Quality Point", "08_quality_point.png"],
  ["09", "Work Centers", "09_work_centers.png"],
  ["10", "Business Unit Analytics", "10_business_unit_analytics.png"],
  ["11", "Approval Category", "11_approval_category.png"],
  ["12", "Accounting Dashboard", "12_accounting_dashboard.png"],
  ["13", "Delivery Methods", "13_delivery_methods.png"],
  ["14", "Fleet Vehicles", "14_fleet_vehicles.png"],
];
evidence.getRange("A1:D1").values = [["No.", "Odoo screen", "File", "Preview"]];
styleHeader(evidence.getRange("A1:D1"), "#305496");
evidence.getRangeByIndexes(1, 0, screenshotRows.length, 3).values = screenshotRows;
styleBody(evidence.getRangeByIndexes(0, 0, screenshotRows.length + 1, 4));
evidence.getRange("A:A").format.columnWidthPx = 50;
evidence.getRange("B:B").format.columnWidthPx = 260;
evidence.getRange("C:C").format.columnWidthPx = 260;
evidence.getRange("D:D").format.columnWidthPx = 380;
for (let i = 0; i < screenshotRows.length; i += 1) {
  const rowNumber = i + 2;
  evidence.getRange(`A${rowNumber}:D${rowNumber}`).format.rowHeightPx = 155;
  const imgPath = path.join(screenshotsDir, screenshotRows[i][2]);
  try {
    const dataUrl = await imageDataUrl(imgPath);
    evidence.images.add({
      dataUrl,
      anchor: {
        from: { row: rowNumber - 1, col: 3 },
        extent: { widthPx: 320, heightPx: 140 },
      },
    });
  } catch {
    evidence.getRange(`D${rowNumber}`).values = [[`Image not found: ${screenshotRows[i][2]}`]];
  }
}

const backlogRows = rows
  .filter((r) => /custom|partial|gap/i.test(r.fit))
  .map((r) => [r.area, r.no, r.requirement, r.fit, r.custom]);
backlog.getRange("A1:E1").values = [["Area", "No.", "Requirement", "Fit", "Recommended next action"]];
styleHeader(backlog.getRange("A1:E1"), "#C00000");
backlog.getRangeByIndexes(1, 0, backlogRows.length, 5).values = backlogRows;
styleBody(backlog.getRangeByIndexes(0, 0, backlogRows.length + 1, 5));
backlog.freezePanes.freezeRows(1);
backlog.getRange("A:A").format.columnWidthPx = 150;
backlog.getRange("B:B").format.columnWidthPx = 50;
backlog.getRange("C:C").format.columnWidthPx = 420;
backlog.getRange("D:D").format.columnWidthPx = 150;
backlog.getRange("E:E").format.columnWidthPx = 430;

const mdLines = [];
mdLines.push("# AMS Workflow vs Standard Odoo 18 Enterprise Mapping");
mdLines.push("");
mdLines.push("## Setup Evidence");
for (const [key, value] of [
  ["Database", verification.database],
  ["URL", verification.url],
  ["Installed standard modules", verification.installed_modules],
  ["Custom modules installed", verification.custom_modules_installed],
  ["BOM / Routing operations / Quality points", `${verification.bom_count} / ${verification.routing_operations} / ${verification.quality_points}`],
]) {
  mdLines.push(`- **${key}:** ${value}`);
}
mdLines.push("");
mdLines.push("## Requirement Mapping");
mdLines.push("| Area | No. | Requirement | Standard Odoo function | Fit | Custom/Pain Point | Screenshot |");
mdLines.push("|---|---:|---|---|---|---|---|");
for (const r of rows) {
  mdLines.push(`| ${r.area} | ${r.no} | ${sanitizeForReport(r.requirement).replaceAll("|", "/")} | ${r.coverage.replaceAll("|", "/")} | ${r.fit} | ${r.custom.replaceAll("|", "/")} | ${r.screenshot} |`);
}
await fs.writeFile(`${outDir}/AMS_Odoo_Standard_Mapping_Report.md`, mdLines.join("\n"), "utf8");

const htmlRows = rows.map((r) => `<tr><td>${escapeHtml(r.area)}</td><td>${r.no}</td><td>${escapeHtml(r.requirement)}</td><td>${escapeHtml(r.demoNote)}</td><td>${escapeHtml(r.coverage)}</td><td>${escapeHtml(r.apps)}</td><td>${escapeHtml(r.fit)}</td><td>${escapeHtml(r.custom)}</td><td>${escapeHtml(r.screenshot)}</td></tr>`).join("\n");
const htmlScreens = screenshotRows.map((r) => `<h3>${escapeHtml(r[1])}</h3><p>${escapeHtml(r[2])}</p><img src="screenshots/${escapeHtml(r[2])}" alt="${escapeHtml(r[1])}">`).join("\n");
const htmlDoc = `<!doctype html><html><head><meta charset="utf-8"><title>AMS Odoo Standard Mapping Report</title><style>body{font-family:Arial,'Noto Sans Thai',sans-serif;margin:24px;color:#17202a;line-height:1.45}table{border-collapse:collapse;width:100%;font-size:13px}th{background:#5B1747;color:white;text-align:left}td,th{border:1px solid #d8dee9;padding:7px;vertical-align:top}img{max-width:100%;border:1px solid #d0d7de;margin-bottom:24px}.meta{color:#5f6b7a}.ok{background:#dcfce7}.warn{background:#fef3c7}</style></head><body><h1>AMS Workflow vs Standard Odoo 18 Enterprise Mapping</h1><p class="meta">Database ${verification.database} | Installed standard modules ${verification.installed_modules} | Custom modules ${verification.custom_modules_installed}</p><h2>Standard vs Pain Point</h2><p>Standard Odoo covers core sales, purchase, inventory, MRP, quality, accounting, budget, project, delivery and fleet flows. Custom work should be limited to company-specific validation, dashboards, scorecards and integrations.</p><h2>Requirement Mapping</h2><table><tr><th>Area</th><th>No.</th><th>Requirement</th><th>Demo note</th><th>Standard Odoo function</th><th>Apps / Modules</th><th>Fit</th><th>Custom/Pain Point</th><th>Screenshot</th></tr>${htmlRows}</table><h2>Odoo Screenshots</h2>${htmlScreens}</body></html>`;
await fs.writeFile(`${outDir}/AMS_Odoo_Standard_Mapping_Report.html`, htmlDoc, "utf8");

const summaryPreview = await workbook.render({ sheetName: "Summary", range: "A1:F22", scale: 1, format: "png" });
await fs.writeFile(`${outDir}/AMS_Workflow_Mapping_Summary_Preview.png`, new Uint8Array(await summaryPreview.arrayBuffer()));
const mappingPreview = await workbook.render({ sheetName: "Requirement Mapping", range: "A1:J16", scale: 1, format: "png" });
await fs.writeFile(`${outDir}/AMS_Workflow_Mapping_Table_Preview.png`, new Uint8Array(await mappingPreview.arrayBuffer()));
const screenshotPreview = await workbook.render({ sheetName: "Odoo Screenshots", range: "A1:D8", scale: 1, format: "png" });
await fs.writeFile(`${outDir}/AMS_Workflow_Screenshots_Preview.png`, new Uint8Array(await screenshotPreview.arrayBuffer()));

const errorScan = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|\\?\\?\\?|�|à¸|à¹",
  options: { useRegex: true, maxResults: 300 },
  summary: "final bad token scan",
});
await fs.writeFile(`${outDir}/AMS_Workflow_Excel_Verification.ndjson`, errorScan.ndjson, "utf8");
const foundBadToken = errorScan.ndjson
  .split(/\r?\n/)
  .filter(Boolean)
  .some((line) => !line.includes("matched 0 entries"));
if (foundBadToken) {
  throw new Error(`Bad token/formula scan found matches: ${errorScan.ndjson.slice(0, 500)}`);
}

const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(`${outDir}/AMS_Odoo_Standard_Mapping_Report.xlsx`);

const index = JSON.parse(await fs.readFile(`${outDir}/deliverables_index.json`, "utf8").catch(() => "{}"));
index.excel_report = `${outDir}/AMS_Odoo_Standard_Mapping_Report.xlsx`;
index.excel_previews = [
  `${outDir}/AMS_Workflow_Mapping_Summary_Preview.png`,
  `${outDir}/AMS_Workflow_Mapping_Table_Preview.png`,
  `${outDir}/AMS_Workflow_Screenshots_Preview.png`,
];
index.mapping_rows = rows.length;
index.bad_token_scan = `${outDir}/AMS_Workflow_Excel_Verification.ndjson`;
await fs.writeFile(`${outDir}/deliverables_index.json`, JSON.stringify(index, null, 2), "utf8");

console.log(JSON.stringify({
  xlsx: `${outDir}/AMS_Odoo_Standard_Mapping_Report.xlsx`,
  rows: rows.length,
  screenshots: screenshotRows.length,
  previews: index.excel_previews,
}, null, 2));
