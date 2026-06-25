import json
import os
from pathlib import Path

from odoo import fields


PRESENT_DIR = Path(r"C:\365_project\TheCool18e\Dev\output\AMS_PRESENT_CUSTOMER_TH")
PACKAGE_DIR = Path(r"C:\365_project\TheCool18e\Dev\output\ams_customer_r001_compare\AMS_R001_COMPARE_PACKAGE")
DOWNLOAD_DIR = Path(r"C:\Users\tumsu\Downloads")
JSON_NAME = "AMS_WORKORDER_COST_STATUS.json"
DRY_RUN = os.environ.get("AMS_COST_DRY_RUN") == "1"

WORKCENTER_COSTS = {
    "PUNCHING": 350.0,
    "SLIT": 300.0,
    "LAMINATE": 500.0,
    "CUTTING": 280.0,
    "MANUAL": 180.0,
    "ASSEMBLY": 220.0,
    "PACKING": 220.0,
}

OPERATION_MINUTES = {
    "PUNCHING 1": 12.0,
    "SLIT FILM 1": 8.0,
    "SLIT ADHESIVE 1": 8.0,
    "LAMINATE 1": 15.0,
    "PUNCHING 2": 12.0,
    "LAMINATE MACHINE 2": 15.0,
    "CUTTING 1": 10.0,
    "SLIT ADHESIVE 2": 8.0,
    "PRE-CUT1": 20.0,
    "SLIT FILM 2": 8.0,
    "SLIT ADHESIVE 3": 8.0,
    "PRE-CUT2": 20.0,
    "CUTTING 2": 10.0,
    "CUTTING 3": 10.0,
    "CUTTING 4": 10.0,
    "PUNCHING 3": 12.0,
    "CUTTING 5": 10.0,
    "CUTTING 6": 10.0,
    "CUTTING 7": 10.0,
    "CUTTING 8": 10.0,
    "ASSEMBLY & PACKING": 25.0,
}


def money(value):
    return round(float(value or 0.0), 2)


def get_product(code):
    product = env["product.product"].sudo().search([("default_code", "=", code)], limit=1)
    if not product:
        raise RuntimeError(f"Missing product {code}")
    return product


def get_or_create_partner(name, rank_field):
    partner = env["res.partner"].sudo().search([("name", "=", name)], limit=1)
    vals = {"name": name, rank_field: 1}
    if partner:
        if not partner[rank_field]:
            partner.write({rank_field: 1})
        return partner
    return env["res.partner"].sudo().create(vals)


def apply_cost_config(fg, bom):
    workcenters = []
    for name, cost in WORKCENTER_COSTS.items():
        wc = env["mrp.workcenter"].sudo().search([("name", "=", name)], limit=1)
        if wc:
            wc.write({"costs_hour": cost})
            workcenters.append({
                "name": wc.name,
                "costs_hour": money(wc.costs_hour),
            })

    operations = []
    for op in bom.operation_ids.sorted("sequence"):
        minutes = OPERATION_MINUTES.get(op.name, op.time_cycle_manual or 10.0)
        op.write({
            "time_mode": "manual",
            "time_cycle_manual": minutes,
        })
        operations.append({
            "sequence": op.sequence,
            "name": op.name,
            "workcenter": op.workcenter_id.name,
            "minutes": money(op.time_cycle_manual),
            "costs_hour": money(op.workcenter_id.costs_hour),
            "planned_cost": money(op.time_cycle_manual / 60.0 * op.workcenter_id.costs_hour),
        })

    component_cost = 0.0
    components = []
    for line in bom.bom_line_ids:
        product = line.product_id
        if product.standard_price <= 0:
            product.standard_price = 1.0
        line_cost = line.product_qty * product.standard_price
        component_cost += line_cost
        components.append({
            "code": product.default_code or "",
            "product": product.display_name,
            "qty": money(line.product_qty),
            "uom": line.product_uom_id.name,
            "unit_cost": money(product.standard_price),
            "line_cost": money(line_cost),
            "cost_method": product.cost_method,
            "valuation": product.valuation,
        })

    fg.button_bom_cost()
    fg.product_tmpl_id.write({"list_price": money(max(fg.standard_price * 1.35, fg.standard_price + 100.0))})
    return {
        "workcenters": workcenters,
        "operations": operations,
        "components": components,
        "component_cost": money(component_cost),
        "operation_cost": money(sum(row["planned_cost"] for row in operations)),
        "fg_standard_price": money(fg.standard_price),
        "fg_sale_price": money(fg.product_tmpl_id.list_price),
    }


def assign_tracked_lines(mo):
    Quant = env["stock.quant"].sudo()
    for move in mo.move_raw_ids.filtered(lambda m: m.state not in ("done", "cancel")):
        needed = move.product_uom_qty
        if move.product_id.tracking == "none":
            continue
        if move.move_line_ids.filtered("lot_id"):
            continue
        quants = Quant.search([
            ("product_id", "=", move.product_id.id),
            ("location_id", "child_of", move.location_id.id),
            ("quantity", ">", 0),
            ("lot_id", "!=", False),
        ], limit=50)
        quant = next((item for item in quants if item.available_quantity >= needed), False)
        if not quant:
            raise RuntimeError(f"No available lot for {move.product_id.display_name}")
        env["stock.move.line"].sudo().create({
            "move_id": move.id,
            "product_id": move.product_id.id,
            "product_uom_id": move.product_uom.id,
            "location_id": move.location_id.id,
            "location_dest_id": move.location_dest_id.id,
            "lot_id": quant.lot_id.id,
            "quantity": needed,
        })


def pass_quality(records):
    checks = records.mapped("check_ids").filtered(lambda check: check.quality_state != "pass")
    for check in checks:
        check.do_pass()


def complete_workorders(mo):
    mo.write({"qty_producing": mo.product_qty})
    if mo.state == "draft":
        mo.action_confirm()
    mo.action_assign()
    assign_tracked_lines(mo)
    pass_quality(mo)
    for workorder in mo.workorder_ids.sorted("sequence"):
        pass_quality(workorder)
        if workorder.state not in ("done", "cancel"):
            workorder.write({"duration": workorder.duration_expected})
            workorder.button_finish()
    mo.with_context(skip_redirection=True).button_mark_done()


def validate_delivery(sale, finished_lot):
    result = []
    for picking in sale.picking_ids.filtered(lambda p: p.state not in ("done", "cancel")):
        picking.action_assign()
        for move in picking.move_ids.filtered(lambda m: m.state not in ("done", "cancel")):
            qty = move.product_uom_qty
            if move.product_id.tracking != "none":
                lines = move.move_line_ids
                if not lines:
                    env["stock.move.line"].sudo().create({
                        "move_id": move.id,
                        "product_id": move.product_id.id,
                        "product_uom_id": move.product_uom.id,
                        "location_id": move.location_id.id,
                        "location_dest_id": move.location_dest_id.id,
                        "lot_id": finished_lot.id,
                        "quantity": qty,
                    })
                else:
                    for line in lines:
                        line.write({"lot_id": finished_lot.id, "qty_done": qty})
            else:
                move._set_quantity_done(qty)
            move.picked = True
        picking.with_context(skip_backorder=True).button_validate()
        result.append({"name": picking.name, "state": picking.state})
    return result


def create_invoice(sale):
    try:
        invoices = sale._create_invoices()
        for invoice in invoices:
            if invoice.state == "draft":
                invoice.action_post()
        return [{"name": inv.name, "state": inv.state, "amount_total": money(inv.amount_total)} for inv in invoices]
    except Exception as exc:
        return [{"name": "", "state": "not_posted", "amount_total": 0.0, "note": str(exc)}]


def create_demo_flow(fg):
    customer = get_or_create_partner("AMS Customer Demo", "customer_rank")
    sale_price = fg.product_tmpl_id.list_price or max(fg.standard_price * 1.35, fg.standard_price + 100.0)
    sale = env["sale.order"].sudo().create({
        "partner_id": customer.id,
        "client_order_ref": "AMS Work Order Cost Demo",
        "order_line": [(0, 0, {
            "product_id": fg.id,
            "product_uom_qty": 1.0,
            "price_unit": sale_price,
        })],
    })
    sale.action_confirm()
    mo = env["mrp.production"].sudo().search([
        ("origin", "=", sale.name),
        ("product_id", "=", fg.id),
    ], order="id desc", limit=1)
    if not mo:
        mo = env["mrp.production"].sudo().search([
            ("origin", "ilike", sale.name),
            ("product_id", "=", fg.id),
        ], order="id desc", limit=1)
    if not mo:
        raise RuntimeError(f"No MO created from {sale.name}")

    lot_name = f"FG-COST-{sale.name}"
    lot = env["stock.lot"].sudo().search([
        ("name", "=", lot_name),
        ("product_id", "=", fg.id),
    ], limit=1)
    if not lot:
        lot = env["stock.lot"].sudo().create({
            "name": lot_name,
            "product_id": fg.id,
            "company_id": mo.company_id.id,
        })
    mo.write({"lot_producing_id": lot.id, "extra_cost": 0.0})
    complete_workorders(mo)
    deliveries = validate_delivery(sale, lot)
    invoices = create_invoice(sale)
    purchase_orders = env["purchase.order"].sudo().search([
        "|",
        ("origin", "ilike", sale.name),
        ("origin", "ilike", mo.name),
    ])
    svls = env["stock.valuation.layer"].sudo().search([
        ("id", "in", (mo.move_raw_ids | mo.move_finished_ids | sale.picking_ids.move_ids).stock_valuation_layer_ids.ids),
    ], order="id")
    return {
        "sale_order": sale.name,
        "sale_state": sale.state,
        "manufacturing_order": mo.name,
        "mo_state": mo.state,
        "mo_origin": mo.origin,
        "finished_lot": lot.name,
        "purchase_orders": [{"name": po.name, "state": po.state, "origin": po.origin} for po in purchase_orders],
        "deliveries": deliveries,
        "invoices": invoices,
        "workorders": [{
            "sequence": wo.sequence,
            "name": wo.name,
            "state": wo.state,
            "workcenter": wo.workcenter_id.name,
            "duration_expected": money(wo.duration_expected),
            "duration": money(wo.duration),
            "costs_hour": money(wo.costs_hour or wo.workcenter_id.costs_hour),
            "actual_cost": money(wo._cal_cost()),
        } for wo in mo.workorder_ids.sorted("sequence")],
        "valuation_layers": [{
            "reference": svl.reference,
            "product": svl.product_id.display_name,
            "quantity": money(svl.quantity),
            "unit_cost": money(svl.unit_cost),
            "value": money(svl.value),
        } for svl in svls],
        "mo_workcenter_cost_total": money(sum(wo._cal_cost() for wo in mo.workorder_ids)),
        "mo_svl_total": money(sum(svl.value for svl in svls)),
    }


def installed_custom_modules():
    module_names = set()
    for base in [
        Path(r"C:\365_project\TheCool18e\Dev\custom\goldmints_addon-main"),
        Path(r"C:\365_project\TheCool18e\Dev\custom\view_dev"),
    ]:
        if not base.exists():
            continue
        for manifest in base.glob("*/__manifest__.py"):
            module_names.add(manifest.parent.name)
    if not module_names:
        return []
    return env["ir.module.module"].sudo().search([
        ("state", "=", "installed"),
        ("name", "in", sorted(module_names)),
    ]).mapped("name")


fg = get_product("AMS.400")
bom = env["mrp.bom"].sudo().search([("product_tmpl_id", "=", fg.product_tmpl_id.id)], limit=1)
if not bom:
    raise RuntimeError("Missing AMS.400 BOM")

config = apply_cost_config(fg, bom)
flow = create_demo_flow(fg)
modules = {}
for module_name in ["mrp_workorder", "mrp_account", "stock_account", "stock_accountant", "spreadsheet_dashboard_stock_account", "spreadsheet_dashboard_mrp"]:
    module = env["ir.module.module"].sudo().search([("name", "=", module_name)], limit=1)
    modules[module_name] = module.state if module else "missing"

data = {
    "database": env.cr.dbname,
    "url": "http://localhost:8813/web/login?db=AMS",
    "generated_at": fields.Datetime.now().isoformat(),
    "dry_run": DRY_RUN,
    "standard_first": True,
    "installed_custom_modules": installed_custom_modules(),
    "modules": modules,
    "product": {
        "code": fg.default_code,
        "name": fg.display_name,
        "cost_method": fg.cost_method,
        "valuation": fg.valuation,
        "standard_price": money(fg.standard_price),
        "sale_price": money(fg.product_tmpl_id.list_price),
        "routes": fg.route_ids.mapped("name"),
    },
    "bom": {
        "name": bom.display_name,
        "components": len(bom.bom_line_ids),
        "operations": len(bom.operation_ids),
    },
    "cost_config": config,
    "flow": flow,
    "dashboard_paths": [
        "Manufacturing > Operations > Manufacturing Orders",
        "Manufacturing > Operations > Work Orders",
        "Product > AMS.400 > Cost Structure",
        "Inventory > Reporting > Valuation",
        "Accounting > Customers > Invoices",
    ],
    "notes": [
        "All changes use standard Odoo ORM and standard Odoo MRP/Stock/Accounting models.",
        "Work center cost is assumed demo cost in THB/hour and can be edited in Odoo Work Centers.",
        "Inventory valuation is manual periodic in this AMS demo database, so cost is visible in stock valuation layers without automated stock journal posting.",
    ],
}

if DRY_RUN:
    env.cr.rollback()
else:
    env.cr.commit()
    for directory in [PRESENT_DIR, PACKAGE_DIR, DOWNLOAD_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / JSON_NAME).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

print(json.dumps({
    "dry_run": DRY_RUN,
    "sale_order": data["flow"]["sale_order"],
    "manufacturing_order": data["flow"]["manufacturing_order"],
    "mo_state": data["flow"]["mo_state"],
    "workorders": len(data["flow"]["workorders"]),
    "workcenter_cost_total": data["flow"]["mo_workcenter_cost_total"],
    "svl_total": data["flow"]["mo_svl_total"],
    "fg_standard_price": data["product"]["standard_price"],
    "output": str(PRESENT_DIR / JSON_NAME),
}, ensure_ascii=False))
