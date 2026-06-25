# AMS Detailed Swimlane Workflow

## Standard vs Pain Point
- Standard Odoo covers the core transaction flow with Sales, CRM, Purchase, Inventory, Barcode, MRP, Quality, Accounting, Budget, Project, Delivery and Fleet.
- Pain points that remain custom candidates: budget hard lock, supplier scorecard, cash forecast from PR/PO/AP/AR, DPPM, cost variance allocation, slow/dead stock KPI, automotive forecast/PO import.
- Accounting/stock integrity: no SQL posting or manual valuation manipulation. Any custom allocation must be designed through Odoo models and accounting rules.

## DB Evidence
- Database: AMS
- URL: http://127.0.0.1:8813/web/login?db=AMS
- Installed standard modules: 217
- Custom modules installed: 0
- BOM/routing/quality points: 1/21/9

## Draw.io Pages
1. Symbol Legend
2. 00 Overall AMS to Odoo Flow
3. 01 Sales CRM Flow
4. 02 Procurement Flow
5. 03 Warehouse Logistics Flow
6. 04 Manufacturing Quality Flow
7. 05 Accounting Finance Flow
8. 06 Planning MRP Master Data Flow

## Symbol Meaning
- **Terminator / rounded rectangle:** Start or End of a process
- **Rectangle:** Process or Odoo action
- **Diamond:** Decision branch such as approved, QC pass, stock enough
- **Parallelogram:** Input or output data
- **Document:** Odoo document such as SO, PO, MO, Invoice
- **Cylinder:** Database/master/transaction data in AMS
- **Circle:** Connector to another flow/page
- **Arrow:** Flowline showing direction and handoff

## Detailed Swimlane Steps

### 00 Overall AMS to Odoo Flow
| Lane | Step | Odoo Standard Function / Model | Decision / Gate | Fit |
|---|---|---|---|---|
| Customer / Sales | Receive forecast, RFQ or customer PO | CRM Lead / Sales Quotation | Customer demand exists | Standard |
| Sales / CRM | Create quotation, track win/lost and convert to SO | sale.order, crm.lead | Won? | Standard; BOM-temp costing may be custom |
| Planning / MRP | Run MRP from SO, forecast and min/max | mrp, stock.warehouse.orderpoint | Stock/material enough? | Standard |
| Procurement | Create RFQ/PO or Blanket Agreement with approval | purchase.order, purchase.requisition, approval.request | Approval required? | Budget guard may be custom |
| Warehouse | Receive, scan barcode, assign lot and shelf | stock.picking, stock.lot, stock.location | Lot required? | Standard |
| Manufacturing / QC | Execute MO, WO, quality checks and rework/scrap if needed | mrp.production, mrp.workorder, quality.point | QC pass? | Standard; DPPM dashboard custom |
| Accounting / Finance | Post invoice/bill/payment and valuation | account.move, account.payment, stock.valuation.layer | Multi-currency / reconciliation | Standard with configuration |
| Management Reporting | Report BU/Branch, GP, cost variance, cash forecast | account.report, spreadsheet dashboard | KPI definition? | Several custom reports |

### 01 Sales CRM Flow
| Lane | Step | Odoo Standard Function / Model | Decision / Gate | Fit |
|---|---|---|---|---|
| Customer | Send inquiry, RFQ, forecast or PO reference | Input data | Complete spec? | Standard input |
| Sales / CRM | Create lead/opportunity and maintain customer profile | crm.lead, res.partner | New customer? | Standard |
| Sales / CRM | Prepare quotation and track win rate | sale.order | Customer accepts? | Standard |
| Product / Engineering | Use product/BOM/cost/pricelist for quotation basis | product.template, mrp.bom, product.pricelist | Need BOM-based costing? | Custom if quotation BOM is separate from production BOM |
| Inventory / MRP | Check forecasted stock and trigger demand | stock.quant, stock.rule, mrp.production | Stock enough? | Standard |
| Accounting | Invoice AR and recognize margin/reporting data | account.move, sale_margin | Invoiceable? | Standard |
| Management | Review sales by BU/Branch/GP and win rate | sale.report, analytic account | Management KPI? | Config/report |

### 02 Procurement Flow
| Lane | Step | Odoo Standard Function / Model | Decision / Gate | Fit |
|---|---|---|---|---|
| Requester / MRP | Create demand from shortage, reorder rule or manual request | stock.warehouse.orderpoint, mrp | Need buy? | Standard |
| Approver / Budget | Review budget/approval category | approval.category, account_budget | Approved? | Hard budget lock custom |
| Purchasing | Send RFQ and compare supplier quotes | purchase.order | Best supplier? | Standard data, scorecard custom |
| Vendor | Submit price, lead time, MOQ and credit term | vendor pricelist / RFQ response | Meets target? | Report/custom score |
| Purchasing | Confirm PO or Blanket Agreement | purchase.order, purchase.requisition | Agreement needed? | Standard |
| Warehouse | Receive and validate lot/barcode | stock.picking | Quantity/quality ok? | Standard |
| Accounting | Create vendor bill and payment schedule | account.move | 3-way match? | Standard/config |

### 03 Warehouse Logistics Flow
| Lane | Step | Odoo Standard Function / Model | Decision / Gate | Fit |
|---|---|---|---|---|
| Warehouse | Receive, store, pick, pack and deliver | stock.picking, stock.move | Operation type? | Standard |
| Barcode Device | Scan product, lot, shelf and quantity | stock_barcode | Barcode available? | Standard |
| Warehouse | Control shelf/location, QC hold and WIP staging | stock.location | Putaway/removal rule? | Config |
| Purchase / Sales / MRP | Use min/max and forecasted inventory to replenish | stock.warehouse.orderpoint | Below min? | Standard |
| Logistics / Fleet | Assign delivery method, cost, route and vehicle context | delivery.carrier, fleet.vehicle | Driver/ticket evaluation? | Custom workflow candidate |
| Accounting | Update stock valuation and COGS | stock.valuation.layer, account.move | Valuation method? | Standard with accounting setup |
| Management | Review slow/dead stock and delivery KPI | inventory reports | KPI threshold? | Custom dashboard |

### 04 Manufacturing Quality Flow
| Lane | Step | Odoo Standard Function / Model | Decision / Gate | Fit |
|---|---|---|---|---|
| Planning / MRP | Convert demand to MO/procurement | mrp.production, stock.rule | Components available? | Standard |
| Engineering / Master Data | Maintain product, multi-level BOM, routing and revisions | product.template, mrp.bom, mrp.routing.workcenter, mrp.eco | BOM revision needed? | PLM standard; PPAP workflow custom |
| Production / Shop Floor | Execute work orders by work center | mrp.workorder, mrp.workcenter | Operation complete? | Standard |
| Production / Shop Floor | Capture input, output, waste and time | workorder productivity, stock.scrap | Waste reason needed? | Extra reporting/custom field possible |
| Quality | Run quality points and quality alerts | quality.point, quality.check, quality.alert | QC pass? | Standard |
| Warehouse | Move FG/WIP and assign lot | stock.move, stock.lot | FG ready? | Standard |
| Accounting / Costing | Calculate production cost and valuation | mrp_account, stock_account | Variance allocation needed? | Custom accounting design |
| Management | Review OEE/OPE/DPPM/cost variance | mrp reports + spreadsheet | Formula defined? | Custom KPI dashboard |

### 05 Accounting Finance Flow
| Lane | Step | Odoo Standard Function / Model | Decision / Gate | Fit |
|---|---|---|---|---|
| Source Documents | SO, PO, MO, receipt, delivery feed accounting | sale.order, purchase.order, mrp.production, stock.picking | Source posted? | Standard |
| Accounting | Create invoices, bills, payments and journal entries | account.move, account.payment | Multi-currency? | Standard |
| Bank / Cash | Import bank statement and reconcile | account.bank.statement, reconciliation widget | Bank format supported? | Custom import if bank file is non-standard |
| Budget / Project | Track analytic budget by BU/Branch/Project | account_budget, account.analytic.account, project.project | Over budget? | Alert/lock custom |
| Stock / MRP Cost | Post stock valuation, WIP, FG and COGS | stock.valuation.layer, account.move | FIFO/AVCO policy? | Standard with setup |
| Management | Review ratios, EBITDA, consolidation and cash forecast | account.report, spreadsheet dashboard | Need statutory consolidation? | Gap/custom/external |

### 06 Planning MRP Master Data Flow
| Lane | Step | Odoo Standard Function / Model | Decision / Gate | Fit |
|---|---|---|---|---|
| Sales Forecast | Collect customer forecast and SO demand | sale.order, forecast input | Forecast format standard? | Custom import if automotive file |
| Master Data | Maintain product, UoM, MOQ, lead time, routes | product.template, product.supplierinfo, stock.route | Master complete? | Config |
| Master Data | Maintain multi-layer BOM/routing/revision | mrp.bom, mrp.routing.workcenter, mrp_plm | Revision controlled? | PLM standard |
| MRP Scheduler | Run MRP and replenish by buy/make rule | mrp, stock.warehouse.orderpoint | Buy or make? | Standard |
| Procurement | Create RFQ from buy demand | purchase.order | Supplier lead time ok? | Standard |
| Manufacturing | Create MO/WO from make demand | mrp.production | Capacity ok? | Planning/capacity may need deeper setup |
| Reporting | Compare forecast vs SO vs delivery vs invoice | sale/reporting data | KPI definition? | Custom dashboard |