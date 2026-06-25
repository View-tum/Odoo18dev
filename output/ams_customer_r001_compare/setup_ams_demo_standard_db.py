from datetime import datetime
from pathlib import Path
import json

from odoo import Command

base_out = Path(r"C:\365_project\TheCool18e\Dev\output")
present_dir = base_out / "AMS_PRESENT_CUSTOMER_TH"
package_dir = base_out / "ams_customer_r001_compare" / "AMS_R001_COMPARE_PACKAGE"
run_code = datetime.now().strftime("AMS-DEMO-%Y%m%d-%H%M")

summary = {
    "run_code": run_code,
    "database": env.cr.dbname,
    "port": 8813,
    "standard_only": True,
    "installed_custom_modules": [],
    "configured": [],
    "records": {},
    "test_flow": [],
    "custom_gaps": [],
}

custom_roots = [
    Path(r"C:\365_project\TheCool18e\Dev\custom\goldmints_addon-main"),
    Path(r"C:\365_project\TheCool18e\Dev\custom\view_dev"),
    Path(r"C:\365_project\TheCool18e\Dev\server\addons"),
]
custom_names = set()
for root in custom_roots:
    if root.exists():
        for manifest in list(root.rglob("__manifest__.py")) + list(root.rglob("__openerp__.py")):
            custom_names.add(manifest.parent.name)
installed_names = set(env["ir.module.module"].search([("state", "=", "installed")]).mapped("name"))
summary["installed_custom_modules"] = sorted(installed_names & custom_names)
summary["standard_only"] = not summary["installed_custom_modules"]

required_modules = [
    "sale_management",
    "purchase",
    "stock",
    "mrp",
    "mrp_workorder",
    "quality_control",
    "quality_mrp",
    "stock_account",
    "account",
    "approvals",
    "stock_barcode",
    "l10n_th",
]
summary["records"]["required_modules"] = {
    name: env["ir.module.module"].search([("name", "=", name)], limit=1).state for name in required_modules
}

company = env.company
company.write({"name": "AMS Co., Ltd.", "currency_id": env.ref("base.THB").id})
summary["configured"].append("Company set to AMS Co., Ltd. with THB currency")

unit = env.ref("uom.product_uom_unit")


def ensure_partner(name, customer=False, supplier=False):
    partner = env["res.partner"].search([("name", "=", name)], limit=1)
    vals = {
        "name": name,
        "company_type": "company",
        "customer_rank": 1 if customer else 0,
        "supplier_rank": 1 if supplier else 0,
    }
    if partner:
        partner.write(vals)
    else:
        partner = env["res.partner"].create(vals)
    return partner


customer = ensure_partner("AMS Customer Demo", customer=True)
supplier = ensure_partner("AMS Supplier Demo", supplier=True)
summary["configured"].append("Demo customer and supplier configured")


def ensure_category(name, parent=None):
    domain = [("name", "=", name)]
    if parent:
        domain.append(("parent_id", "=", parent.id))
    category = env["product.category"].search(domain, limit=1)
    vals = {"name": name}
    if parent:
        vals["parent_id"] = parent.id
    if category:
        category.write(vals)
    else:
        category = env["product.category"].create(vals)
    return category


root_category = env.ref("product.product_category_all")
cat_fg = ensure_category("AMS Finished Goods", root_category)
cat_rm = ensure_category("AMS Raw Material", root_category)
cat_semi = ensure_category("AMS Semi Part", root_category)
cat_tool = ensure_category("AMS Tooling", root_category)
cat_trading = ensure_category("AMS Trading", root_category)


def ensure_product(name, code, category, sale_ok=False, purchase_ok=False, tracking="lot", cost=10.0, price=50.0, routes=None):
    template = env["product.template"].search(["|", ("default_code", "=", code), ("name", "=", name)], limit=1)
    vals = {
        "name": name,
        "default_code": code,
        "type": "consu",
        "is_storable": True,
        "tracking": tracking,
        "categ_id": category.id,
        "uom_id": unit.id,
        "uom_po_id": unit.id,
        "sale_ok": sale_ok,
        "purchase_ok": purchase_ok,
        "standard_price": cost,
        "list_price": price,
    }
    if routes is not None:
        vals["route_ids"] = [Command.set([r.id for r in routes])]
    if template:
        template.write(vals)
    else:
        template = env["product.template"].create(vals)
    return template.product_variant_id


routes = env["stock.route"].search([])
buy_route = routes.filtered(lambda r: "Buy" in r.name or "ซื้อ" in r.name)[:1]
manufacture_route = routes.filtered(lambda r: "Manufacture" in r.name or "ผลิต" in r.name)[:1]

fg = ensure_product("AMS.400 REV 00", "AMS.400", cat_fg, sale_ok=True, purchase_ok=False, tracking="lot", cost=250.0, price=500.0, routes=manufacture_route)
raw_products = []
raw_code_map = {17: "BOX.0001"}
for index in range(1, 18):
    code = raw_code_map.get(index, f"100010{index:02d}")
    raw_products.append(ensure_product(f"Raw Material {index}", code, cat_rm, sale_ok=False, purchase_ok=True, tracking="lot", cost=8.0 + index))
trading = ensure_product("Trading 1", "40001014", cat_trading, sale_ok=False, purchase_ok=True, tracking="lot", cost=25.0)
semi_products = {}
for index in [9, 10, 11, 12, 15, 16]:
    semi_products[index] = ensure_product(f"Semi Part {index}", f"200010{index:02d}", cat_semi, sale_ok=False, purchase_ok=False, tracking="lot", cost=30.0)
for index in [1, 2, 3]:
    ensure_product(f"TOOLING.{index:03d}", f"TOOLING.{index:03d}", cat_tool, sale_ok=False, purchase_ok=True, tracking="none", cost=150.0)
summary["configured"].append("Products, product codes, categories, stockability, lot tracking, sale/purchase flags configured")


def ensure_workcenter(code, name=None):
    wc = env["mrp.workcenter"].search(["|", ("code", "=", code), ("name", "=", name or code)], limit=1)
    vals = {"name": name or code, "code": code, "default_capacity": 1.0, "time_efficiency": 100.0}
    if wc:
        wc.write(vals)
    else:
        wc = env["mrp.workcenter"].create(vals)
    return wc


workcenters = {
    "PUNCHING": ensure_workcenter("PUNCHING"),
    "SLIT": ensure_workcenter("SLIT"),
    "LAMINATE": ensure_workcenter("LAMINATE"),
    "CUTTING": ensure_workcenter("CUTTING"),
    "MANUAL": ensure_workcenter("MANUAL"),
    "ASSEMBLY": ensure_workcenter("ASSEMBLY"),
}

operation_defs = [
    (10, "PUNCH1", "PUNCHING 1", "PUNCHING"),
    (20, "SL-FILM-1", "SLIT FILM 1", "SLIT"),
    (30, "SL-ADH-1", "SLIT ADHESIVE 1", "SLIT"),
    (40, "LAMINATE1", "LAMINATE 1", "LAMINATE"),
    (50, "PUNCH2", "PUNCHING 2", "PUNCHING"),
    (60, "LAMINATE2", "LAMINATE MACHINE 2", "LAMINATE"),
    (70, "V-CUT1", "CUTTING 1", "CUTTING"),
    (80, "SL-ADH-2", "SLIT ADHESIVE 2", "SLIT"),
    (90, "MANUAL", "PRE-CUT1", "MANUAL"),
    (100, "SL-FILM-2", "SLIT FILM 2", "SLIT"),
    (110, "SL-ADH-3", "SLIT ADHESIVE 3", "SLIT"),
    (120, "MANUAL", "PRE-CUT2", "MANUAL"),
    (130, "V-CUT2", "CUTTING 2", "CUTTING"),
    (140, "V-CUT3", "CUTTING 3", "CUTTING"),
    (150, "V-CUT4", "CUTTING 4", "CUTTING"),
    (160, "PUNCH3", "PUNCHING 3", "PUNCHING"),
    (170, "V-CUT5", "CUTTING 5", "CUTTING"),
    (180, "V-CUT6", "CUTTING 6", "CUTTING"),
    (190, "V-CUT7", "CUTTING 7", "CUTTING"),
    (200, "V-CUT8", "CUTTING 8", "CUTTING"),
    (210, "MANUAL", "ASSEMBLY & PACKING", "ASSEMBLY"),
]

manufacturing_type = env["stock.picking.type"].search([("code", "=", "mrp_operation"), ("company_id", "=", company.id)], limit=1)
bom = env["mrp.bom"].search([("product_tmpl_id", "=", fg.product_tmpl_id.id)], limit=1)
bom_vals = {
    "product_tmpl_id": fg.product_tmpl_id.id,
    "product_qty": 1.0,
    "product_uom_id": unit.id,
    "type": "normal",
    "ready_to_produce": "asap",
    "consumption": "warning",
}
if manufacturing_type:
    bom_vals["picking_type_id"] = manufacturing_type.id
if bom:
    bom.write(bom_vals)
else:
    bom = env["mrp.bom"].create(bom_vals)

operation_by_seq = {op.sequence: op for op in bom.operation_ids}
operations = {}
for sequence, process_id, name, wc_key in operation_defs:
    vals = {
        "bom_id": bom.id,
        "sequence": sequence,
        "name": name,
        "workcenter_id": workcenters[wc_key].id,
        "time_cycle_manual": 60.0,
    }
    op = operation_by_seq.get(sequence)
    if op:
        op.write(vals)
    else:
        op = env["mrp.routing.workcenter"].create(vals)
    operations[name] = op

component_operation = {
    "Raw Material 1": "PUNCHING 1",
    "Raw Material 2": "SLIT FILM 1",
    "Raw Material 3": "SLIT ADHESIVE 1",
    "Raw Material 4": "SLIT ADHESIVE 2",
    "Raw Material 5": "LAMINATE MACHINE 2",
    "Raw Material 6": "ASSEMBLY & PACKING",
    "Raw Material 7": "SLIT FILM 2",
    "Raw Material 8": "SLIT ADHESIVE 3",
    "Raw Material 9": "CUTTING 2",
    "Raw Material 10": "CUTTING 3",
    "Raw Material 11": "CUTTING 4",
    "Raw Material 12": "CUTTING 5",
    "Raw Material 13": "CUTTING 6",
    "Raw Material 14": "ASSEMBLY & PACKING",
    "Raw Material 15": "CUTTING 7",
    "Raw Material 16": "CUTTING 8",
    "Raw Material 17": "ASSEMBLY & PACKING",
    "Trading 1": "ASSEMBLY & PACKING",
}
component_products = raw_products + [trading]
existing_lines = {line.product_id.id: line for line in bom.bom_line_ids}
for product in component_products:
    op = operations.get(component_operation.get(product.display_name, "ASSEMBLY & PACKING"))
    vals = {
        "bom_id": bom.id,
        "product_id": product.id,
        "product_qty": 1.0,
        "product_uom_id": unit.id,
        "operation_id": op.id if op else False,
    }
    line = existing_lines.get(product.id)
    if line:
        line.write(vals)
    else:
        env["mrp.bom.line"].create(vals)
summary["configured"].append("BOM AMS.400 REV 00 configured with 18 components and 21 routing operations")

stock_location = env["stock.location"].search([("usage", "=", "internal"), ("company_id", "in", [company.id, False])], limit=1)


def ensure_lot(product, name):
    lot = env["stock.lot"].search([("name", "=", name), ("product_id", "=", product.id), ("company_id", "in", [company.id, False])], limit=1)
    if not lot:
        lot = env["stock.lot"].create({"name": name, "product_id": product.id, "company_id": company.id})
    return lot


lot_by_product = {}
for product in component_products:
    lot = ensure_lot(product, f"LOT-{product.default_code or product.id}-AMS")
    lot_by_product[product.id] = lot
    current = env["stock.quant"]._get_available_quantity(product, stock_location, lot_id=lot)
    if current < 100:
        env["stock.quant"]._update_available_quantity(product, stock_location, 100 - current, lot_id=lot)
summary["configured"].append("Raw material and trading stock lots loaded to WH/Stock for demo production")

orderpoint_model = env["stock.warehouse.orderpoint"]
for product in raw_products:
    opoint = orderpoint_model.search([("product_id", "=", product.id), ("location_id", "=", stock_location.id)], limit=1)
    vals = {
        "product_id": product.id,
        "location_id": stock_location.id,
        "product_min_qty": 10.0,
        "product_max_qty": 100.0,
        "qty_multiple": 1.0,
    }
    if opoint:
        opoint.write(vals)
    else:
        orderpoint_model.create(vals)
summary["configured"].append("Reordering rules configured for raw materials")

quality_team = env["quality.alert.team"].search([], limit=1)
test_type = env["quality.point.test_type"].search([("technical_name", "=", "passfail")], limit=1) or env["quality.point.test_type"].search([], limit=1)
qc_operations = ["PUNCHING 1", "SLIT FILM 1", "LAMINATE 1", "CUTTING 1", "PRE-CUT1", "ASSEMBLY & PACKING"]
for index, op_name in enumerate(qc_operations, start=1):
    op = operations[op_name]
    name = f"AMS QC {index:02d} - {op_name}"
    point = env["quality.point"].search([("name", "=", name)], limit=1)
    vals = {
        "name": name,
        "team_id": quality_team.id,
        "picking_type_ids": [Command.set([manufacturing_type.id])] if manufacturing_type else False,
        "product_ids": [Command.set([fg.id])],
        "bom_id": bom.id,
        "operation_id": op.id,
        "test_type_id": test_type.id,
        "measure_on": "operation",
        "measure_frequency_type": "all",
    }
    if point:
        point.write(vals)
    else:
        env["quality.point"].create(vals)
summary["configured"].append("Quality control points configured on selected manufacturing operations")


def log_step(name, status, record=None, detail=None):
    row = {"step": name, "status": status}
    if record:
        row["record"] = record.display_name
        row["model"] = record._name
        row["id"] = record.id
    if detail:
        row["detail"] = detail
    summary["test_flow"].append(row)


def pass_quality_checks(record):
    for check in record.check_ids:
        if hasattr(check, "do_pass") and check.quality_state == "none":
            check.do_pass()


def finish_workorders(production):
    for workorder in production.workorder_ids.sorted("sequence"):
        workorder.invalidate_recordset()
        if workorder.state in ("pending", "ready"):
            workorder.button_start()
        pass_quality_checks(workorder)
        if "qty_producing" in workorder._fields:
            workorder.qty_producing = 1.0
        if workorder.state in ("progress", "ready", "pending"):
            workorder.button_finish()


try:
    po = env["purchase.order"].create({
        "partner_id": supplier.id,
        "origin": run_code,
        "order_line": [Command.create({
            "product_id": raw_products[0].id,
            "name": raw_products[0].display_name,
            "product_qty": 5.0,
            "product_uom": unit.id,
            "price_unit": raw_products[0].standard_price,
        })],
    })
    po.button_confirm()
    log_step("Purchase Order confirmed", "passed", po)
    for picking in po.picking_ids:
        picking.action_assign()
        for move in picking.move_ids:
            lot = ensure_lot(move.product_id, f"LOT-PO-{run_code}-{move.product_id.default_code or move.product_id.id}")
            move.move_line_ids.unlink()
            env["stock.move.line"].create({
                "move_id": move.id,
                "product_id": move.product_id.id,
                "product_uom_id": move.product_uom.id,
                "location_id": move.location_id.id,
                "location_dest_id": move.location_dest_id.id,
                "lot_id": lot.id,
                "quantity": move.product_uom_qty,
                "company_id": company.id,
            })
        picking.button_validate()
        log_step("Vendor receipt validated", "passed", picking)
except Exception as exc:
    log_step("Purchase to receipt", "failed", detail=f"{type(exc).__name__}: {exc}")

try:
    so = env["sale.order"].create({
        "partner_id": customer.id,
        "client_order_ref": run_code,
        "order_line": [Command.create({
            "product_id": fg.id,
            "name": fg.display_name,
            "product_uom_qty": 1.0,
            "product_uom": unit.id,
            "price_unit": fg.lst_price,
        })],
    })
    so.action_confirm()
    log_step("Sales Order confirmed", "passed", so)
except Exception as exc:
    so = False
    log_step("Sales order", "failed", detail=f"{type(exc).__name__}: {exc}")

try:
    mo = env["mrp.production"].create({
        "product_id": fg.id,
        "product_qty": 1.0,
        "product_uom_id": unit.id,
        "bom_id": bom.id,
    })
    mo.action_confirm()
    mo.action_assign()
    mo.button_plan()
    fg_lot = ensure_lot(fg, f"LOT-FG-{run_code}")
    mo.write({"lot_producing_id": fg_lot.id, "qty_producing": 1.0})
    for move in mo.move_raw_ids:
        lot = lot_by_product.get(move.product_id.id) or ensure_lot(move.product_id, f"LOT-{move.product_id.default_code or move.product_id.id}-AMS")
        if not move.move_line_ids:
            env["stock.move.line"].create({
                "move_id": move.id,
                "product_id": move.product_id.id,
                "product_uom_id": move.product_uom.id,
                "location_id": move.location_id.id,
                "location_dest_id": move.location_dest_id.id,
                "lot_id": lot.id,
                "quantity": move.product_uom_qty,
                "company_id": company.id,
            })
        else:
            move.move_line_ids.write({"lot_id": lot.id, "quantity": move.product_uom_qty})
    for move in mo.move_finished_ids.filtered(lambda m: m.product_id == fg):
        if not move.move_line_ids:
            env["stock.move.line"].create({
                "move_id": move.id,
                "product_id": fg.id,
                "product_uom_id": unit.id,
                "location_id": move.location_id.id,
                "location_dest_id": move.location_dest_id.id,
                "lot_id": fg_lot.id,
                "quantity": 1.0,
                "company_id": company.id,
            })
        else:
            move.move_line_ids.write({"lot_id": fg_lot.id, "quantity": 1.0})
    finish_workorders(mo)
    mo.button_mark_done()
    log_step("Manufacturing Order produced", "passed", mo)
except Exception as exc:
    mo = locals().get("mo") or False
    log_step("Manufacturing order", "failed", mo if mo else None, f"{type(exc).__name__}: {exc}")

try:
    if so:
        for picking in so.picking_ids:
            picking.action_assign()
            for move in picking.move_ids:
                if move.product_id == fg:
                    fg_lot = env["stock.lot"].search([("name", "=", f"LOT-FG-{run_code}"), ("product_id", "=", fg.id)], limit=1)
                    move.move_line_ids.unlink()
                    env["stock.move.line"].create({
                        "move_id": move.id,
                        "product_id": fg.id,
                        "product_uom_id": unit.id,
                        "location_id": move.location_id.id,
                        "location_dest_id": move.location_dest_id.id,
                        "lot_id": fg_lot.id,
                        "quantity": move.product_uom_qty,
                        "company_id": company.id,
                    })
            picking.button_validate()
            log_step("Customer delivery validated", "passed", picking)
        invoices = so._create_invoices()
        for invoice in invoices:
            invoice.action_post()
            log_step("Customer invoice posted", "passed", invoice)
except Exception as exc:
    log_step("Delivery to invoice", "failed", detail=f"{type(exc).__name__}: {exc}")

summary["records"].update({
    "products": env["product.template"].search_count([]),
    "bom": bom.display_name,
    "bom_components": len(bom.bom_line_ids),
    "bom_operations": len(bom.operation_ids),
    "quality_points_total": env["quality.point"].search_count([]),
    "raw_material_orderpoints": env["stock.warehouse.orderpoint"].search_count([("product_id", "in", [p.id for p in raw_products])]),
})

summary["custom_gaps"] = [
    {"flow": "Request FA Sample", "gap": "ต้องมีฟอร์มและ approval เฉพาะ", "standard_position": "ใช้ Sales/CRM + Activity เป็น workaround ได้"},
    {"flow": "Request Raw Material", "gap": "ฟอร์มเบิก/ขอวัตถุดิบเฉพาะและ approval หลายระดับ", "standard_position": "ใช้ Manufacturing component demand / internal transfer ได้บางส่วน"},
    {"flow": "PCC / Process Control Chart", "gap": "รูปแบบเอกสาร PCC เฉพาะลูกค้า", "standard_position": "ใช้ Quality Check เป็น data source ได้ แต่ template/report ต้อง custom"},
    {"flow": "Document Control", "gap": "ทะเบียนเอกสารและ revision control เฉพาะ", "standard_position": "ใช้ Documents/PLM ได้บางส่วน แต่ format และ workflow ต้อง custom/config เพิ่ม"},
    {"flow": "Legacy Thai Forms / QR Label", "gap": "แบบฟอร์มและ QR ตามรูปเดิม", "standard_position": "ข้อมูลมีใน Odoo แต่ report layout ต้อง custom"},
]

summary_path = present_dir / "AMS_DB_SETUP_SUMMARY.json"
summary_md_path = present_dir / "AMS_DB_SETUP_SUMMARY.md"
package_summary_path = package_dir / "AMS_DB_SETUP_SUMMARY.json"
package_summary_md_path = package_dir / "AMS_DB_SETUP_SUMMARY.md"
present_dir.mkdir(parents=True, exist_ok=True)
package_dir.mkdir(parents=True, exist_ok=True)

summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
package_summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

lines = [
    "# AMS Demo Database Setup Summary",
    "",
    f"- Database: `{summary['database']}`",
    "- URL: `http://localhost:8813`",
    "- Login: `admin` / `admin`",
    f"- Standard only installed custom modules: `{len(summary['installed_custom_modules'])}`",
    "",
    "## Configured",
]
lines += [f"- {item}" for item in summary["configured"]]
lines += ["", "## Test Flow"]
for row in summary["test_flow"]:
    record = f" - {row.get('record')}" if row.get("record") else ""
    detail = f" ({row.get('detail')})" if row.get("detail") else ""
    lines.append(f"- {row['status'].upper()}: {row['step']}{record}{detail}")
lines += ["", "## Current Records"]
for key, value in summary["records"].items():
    lines.append(f"- {key}: {value}")
lines += ["", "## Custom Gap Points"]
for gap in summary["custom_gaps"]:
    lines.append(f"- {gap['flow']}: {gap['gap']} | Standard position: {gap['standard_position']}")
summary_md_path.write_text("\n".join(lines), encoding="utf-8")
package_summary_md_path.write_text("\n".join(lines), encoding="utf-8")

env.cr.commit()
print(json.dumps(summary, ensure_ascii=True, indent=2))
