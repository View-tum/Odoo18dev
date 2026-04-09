import json
import xmlrpc.client
from pathlib import Path


BASE = Path(r"C:\365_project\TheCool18e\Dev\reports\training_purchase_20260331")
OUT_JSON = BASE / "training_purchase_uat_docs.json"

URL = "http://127.0.0.1:8811"
DB = "uat"
USERNAME = "admin"
PASSWORD = "365@gmp"


class OdooRPC:
    def __init__(self):
        common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
        self.uid = common.authenticate(DB, USERNAME, PASSWORD, {})
        if not self.uid:
            raise RuntimeError("Odoo authentication failed")
        self.models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")

    def call(self, model, method, *args, **kwargs):
        return self.models.execute_kw(DB, self.uid, PASSWORD, model, method, list(args), kwargs or {})


def form_url(model, rec_id):
    return f"{URL}/odoo?db={DB}#id={rec_id}&model={model}&view_type=form"


def first(seq):
    return seq[0] if seq else None


def ensure_training_asset_location(rpc):
    loc = rpc.call(
        "stock.location",
        "search_read",
        [("name", "=", "Training Asset"), ("location_id", "=", 8)],
        fields=["id", "name", "complete_name"],
        limit=1,
    )
    if loc:
        return loc[0]
    loc_id = rpc.call(
        "stock.location",
        "create",
        {
            "name": "Training Asset",
            "location_id": 8,
            "usage": "internal",
        },
    )
    return rpc.call("stock.location", "read", [loc_id], fields=["id", "name", "complete_name"])[0]


def ensure_pr(rpc, *, origin, product_id, qty, analytic_id, unit_cost, vendor_id, description, state="draft"):
    recs = rpc.call(
        "purchase.request",
        "search_read",
        [("origin", "=", origin)],
        fields=["id", "name", "state", "origin", "line_ids"],
        limit=1,
    )
    if recs:
        rec = recs[0]
        if state != rec["state"]:
            rpc.call(
                "purchase.request",
                "write",
                [[rec["id"]], {"state": state}],
                context={"tracking_disable": True, "mail_create_nolog": True},
            )
            rec = rpc.call(
                "purchase.request",
                "search_read",
                [("id", "=", rec["id"])],
                fields=["id", "name", "state", "origin", "line_ids"],
                limit=1,
            )[0]
        return rec

    prod = rpc.call("product.product", "read", [product_id], fields=["display_name", "uom_id"])[0]
    pr_id = rpc.call(
        "purchase.request",
        "create",
        {
            "origin": origin,
            "description": description,
            "requested_by": rpc.uid,
            "assigned_to": rpc.uid,
            "vendor": vendor_id,
        },
    )
    rpc.call(
        "purchase.request.line",
        "create",
        {
            "request_id": pr_id,
            "product_id": product_id,
            "name": prod["display_name"],
            "product_qty": qty,
            "product_uom_id": prod["uom_id"][0],
            "date_required": "2026-03-31",
            "analytic_distribution": {str(analytic_id): 100.0},
            "unit_cost": unit_cost,
        },
    )
    if state != "draft":
        rpc.call(
            "purchase.request",
            "write",
            [[pr_id], {"state": state}],
            context={"tracking_disable": True, "mail_create_nolog": True},
        )
    return rpc.call(
        "purchase.request",
        "search_read",
        [("id", "=", pr_id)],
        fields=["id", "name", "state", "origin", "line_ids"],
        limit=1,
    )[0]


def ensure_stock_po(
    rpc,
    *,
    origin,
    partner_id,
    product_id,
    qty,
    price_unit,
    date_order,
    invoice_reference,
    invoice_date,
    lot_name=None,
    location_dest_id=None,
):
    recs = rpc.call(
        "purchase.order",
        "search_read",
        [("origin", "=", origin)],
        fields=["id", "name", "state", "picking_ids", "origin"],
        limit=1,
    )
    if recs:
        po = recs[0]
    else:
        prod = rpc.call("product.product", "read", [product_id], fields=["display_name", "uom_id"])[0]
        po_id = rpc.call(
            "purchase.order",
            "create",
            {
                "partner_id": partner_id,
                "origin": origin,
                "date_order": date_order,
                "order_line": [
                    [
                        0,
                        0,
                        {
                            "product_id": product_id,
                            "name": prod["display_name"],
                            "product_qty": qty,
                            "product_uom": prod["uom_id"][0],
                            "price_unit": price_unit,
                            "date_planned": date_order,
                        },
                    ]
                ],
            },
        )
        rpc.call("purchase.order", "button_confirm", [po_id])
        rpc.call("purchase.order", "button_approve", [po_id])
        po = rpc.call(
            "purchase.order",
            "search_read",
            [("id", "=", po_id)],
            fields=["id", "name", "state", "picking_ids", "origin"],
            limit=1,
        )[0]

    pick_id = first(po["picking_ids"])
    picking = None
    if pick_id:
        picking = rpc.call(
            "stock.picking",
            "read",
            [pick_id],
            fields=["id", "name", "state", "move_line_ids", "location_dest_id", "invoice_reference", "invoice_date"],
        )[0]
        if picking["state"] != "done":
            write_vals = {"invoice_reference": invoice_reference, "invoice_date": invoice_date}
            if location_dest_id:
                write_vals["location_dest_id"] = location_dest_id
            rpc.call("stock.picking", "write", [[pick_id], write_vals])
            if picking["move_line_ids"]:
                line_vals = {"qty_done": qty, "quantity": qty}
                if location_dest_id:
                    line_vals["location_dest_id"] = location_dest_id
                if lot_name:
                    line_vals["lot_name"] = lot_name
                rpc.call("stock.move.line", "write", [picking["move_line_ids"], line_vals])
            rpc.call("stock.picking", "button_validate", [pick_id])
            picking = rpc.call(
                "stock.picking",
                "read",
                [pick_id],
                fields=["id", "name", "state", "move_line_ids", "location_dest_id", "invoice_reference", "invoice_date"],
            )[0]

    return po, picking


def ensure_scrap(rpc, *, origin, product_id, qty, product_uom_id, location_id, lot_id=None):
    recs = rpc.call(
        "stock.scrap",
        "search_read",
        [("origin", "=", origin)],
        fields=["id", "name", "state", "origin"],
        limit=1,
    )
    if recs:
        return recs[0]
    vals = {
        "product_id": product_id,
        "scrap_qty": qty,
        "product_uom_id": product_uom_id,
        "location_id": location_id,
        "company_id": 1,
        "origin": origin,
    }
    if lot_id:
        vals["lot_id"] = lot_id
    scrap_id = rpc.call("stock.scrap", "create", vals)
    rpc.call("stock.scrap", "action_validate", [scrap_id])
    return rpc.call(
        "stock.scrap",
        "search_read",
        [("id", "=", scrap_id)],
        fields=["id", "name", "state", "origin", "lot_id"],
        limit=1,
    )[0]


def ensure_service_po(
    rpc,
    *,
    origin,
    partner_id,
    product_id,
    qty,
    price_unit,
    date_order,
):
    recs = rpc.call(
        "purchase.order",
        "search_read",
        [("origin", "=", origin)],
        fields=["id", "name", "state", "order_line"],
        limit=1,
    )
    if recs:
        po = recs[0]
    else:
        prod = rpc.call("product.product", "read", [product_id], fields=["display_name", "uom_id"])[0]
        po_id = rpc.call(
            "purchase.order",
            "create",
            {
                "partner_id": partner_id,
                "origin": origin,
                "date_order": date_order,
                "order_line": [
                    [
                        0,
                        0,
                        {
                            "product_id": product_id,
                            "name": prod["display_name"],
                            "product_qty": qty,
                            "product_uom": prod["uom_id"][0],
                            "price_unit": price_unit,
                            "date_planned": date_order,
                        },
                    ]
                ],
            },
        )
        rpc.call("purchase.order", "button_confirm", [po_id])
        rpc.call("purchase.order", "button_approve", [po_id])
        po = rpc.call(
            "purchase.order",
            "search_read",
            [("id", "=", po_id)],
            fields=["id", "name", "state", "order_line"],
            limit=1,
        )[0]

    accs = rpc.call(
        "service.acceptance",
        "search_read",
        [("purchase_id", "=", po["id"])],
        fields=["id", "name", "state", "acceptance_line_ids"],
        limit=1,
    )
    if accs:
        acceptance = accs[0]
    else:
        rpc.call("purchase.order", "action_create_service_acceptance", [po["id"]])
        acceptance = rpc.call(
            "service.acceptance",
            "search_read",
            [("purchase_id", "=", po["id"])],
            fields=["id", "name", "state", "acceptance_line_ids"],
            limit=1,
        )[0]
    if acceptance["state"] != "done":
        rpc.call("service.acceptance", "action_confirm", [acceptance["id"]])
        acceptance = rpc.call(
            "service.acceptance",
            "search_read",
            [("id", "=", acceptance["id"])],
            fields=["id", "name", "state", "acceptance_line_ids"],
            limit=1,
        )[0]

    bill_ids = rpc.call(
        "account.move",
        "search",
        [("invoice_origin", "=", po["name"]), ("move_type", "=", "in_invoice")],
        order="id desc",
        limit=1,
    )
    if bill_ids:
        bill = rpc.call(
            "account.move",
            "read",
            [bill_ids[0]],
            fields=["id", "name", "state", "invoice_origin"],
        )[0]
    else:
        result = rpc.call("purchase.order", "action_create_invoice", [po["id"]])
        bill_id = result.get("res_id")
        bill = rpc.call(
            "account.move",
            "read",
            [bill_id],
            fields=["id", "name", "state", "invoice_origin"],
        )[0]
    return po, acceptance, bill


def main():
    rpc = OdooRPC()
    asset_location = ensure_training_asset_location(rpc)

    rm_pr_draft = ensure_pr(
        rpc,
        origin="TRN-PUR-RM-DRAFT-2",
        product_id=8750,
        qty=5.0,
        analytic_id=1,
        unit_cost=120.0,
        vendor_id=70302,
        description="Training RM draft PR",
        state="draft",
    )
    rm_pr_approved = ensure_pr(
        rpc,
        origin="TRN-PUR-RM-APPROVED-2",
        product_id=8751,
        qty=8.0,
        analytic_id=1,
        unit_cost=95.0,
        vendor_id=70302,
        description="Training RM approved PR",
        state="approved",
    )
    rm_po, rm_picking = ensure_stock_po(
        rpc,
        origin="TRN-PUR-RM-PO1",
        partner_id=70302,
        product_id=8750,
        qty=10.0,
        price_unit=120.0,
        date_order="2026-03-31 09:00:00",
        invoice_reference="TRN-RM-INV-01",
        invoice_date="2026-03-31",
        lot_name="TRN-RM-LOT-01",
    )
    rm_move_lines = rpc.call(
        "stock.move.line",
        "read",
        rm_picking["move_line_ids"],
        fields=["id", "lot_id", "location_dest_id", "qty_done", "quantity"],
    )
    rm_scrap = ensure_scrap(
        rpc,
        origin="TRN-PUR-RM-SCRAP",
        product_id=8750,
        qty=1.0,
        product_uom_id=10,
        location_id=first(rm_move_lines)["location_dest_id"][0],
        lot_id=first(rm_move_lines)["lot_id"][0],
    )

    asset_pr = ensure_pr(
        rpc,
        origin="TRN-PUR-ASSET-PR1",
        product_id=8671,
        qty=2.0,
        analytic_id=5,
        unit_cost=25000.0,
        vendor_id=70302,
        description="Training asset PR",
        state="draft",
    )
    asset_po, asset_picking = ensure_stock_po(
        rpc,
        origin="TRN-PUR-ASSET-PO1",
        partner_id=70302,
        product_id=8671,
        qty=2.0,
        price_unit=25000.0,
        date_order="2026-03-31 09:30:00",
        invoice_reference="TRN-ASSET-INV-01",
        invoice_date="2026-03-31",
        location_dest_id=asset_location["id"],
    )
    asset_bill_id = first(
        rpc.call(
            "account.move",
            "search",
            [("invoice_origin", "=", asset_po["name"]), ("move_type", "=", "in_invoice")],
            order="id desc",
            limit=1,
        )
    )
    asset_bill = rpc.call(
        "account.move",
        "read",
        [asset_bill_id],
        fields=["id", "name", "state", "invoice_origin"],
    )[0]

    consu_pr = ensure_pr(
        rpc,
        origin="TRN-PUR-CONSU-PR1",
        product_id=8724,
        qty=24.0,
        analytic_id=5,
        unit_cost=35.0,
        vendor_id=70302,
        description="Training consumable PR",
        state="draft",
    )
    consu_po, consu_picking = ensure_stock_po(
        rpc,
        origin="TRN-PUR-CONSU-PO1",
        partner_id=70302,
        product_id=8724,
        qty=24.0,
        price_unit=35.0,
        date_order="2026-03-31 10:30:00",
        invoice_reference="TRN-CONSU-INV-01",
        invoice_date="2026-03-31",
    )

    service_po, service_acceptance, service_bill = ensure_service_po(
        rpc,
        origin="TRN-PUR-SERVICE-PO1",
        partner_id=70303,
        product_id=8165,
        qty=1.0,
        price_unit=15000.0,
        date_order="2026-03-31 10:00:00",
    )

    category_id = rpc.call("product.product", "read", [8750], fields=["categ_id"])[0]["categ_id"][0]

    docs = {
        "urls": {
            "home": f"{URL}/odoo?db={DB}",
            "product_category_rm": form_url("product.category", category_id),
            "vendor_master": form_url("res.partner", 70302),
            "rm_pr_draft": form_url("purchase.request", rm_pr_draft["id"]),
            "rm_pr_approved": form_url("purchase.request", rm_pr_approved["id"]),
            "rm_po": form_url("purchase.order", rm_po["id"]),
            "rm_receipt": form_url("stock.picking", rm_picking["id"]),
            "rm_scrap": form_url("stock.scrap", rm_scrap["id"]),
            "asset_pr": form_url("purchase.request", asset_pr["id"]),
            "asset_receipt": form_url("stock.picking", asset_picking["id"]),
            "asset_bill": form_url("account.move", asset_bill["id"]),
            "consu_pr": form_url("purchase.request", consu_pr["id"]),
            "consu_receipt": form_url("stock.picking", consu_picking["id"]),
            "service_po": form_url("purchase.order", service_po["id"]),
            "service_acceptance": form_url("service.acceptance", service_acceptance["id"]),
            "service_bill": form_url("account.move", service_bill["id"]),
        },
        "records": {
            "rm_pr_draft": rm_pr_draft,
            "rm_pr_approved": rm_pr_approved,
            "rm_po": rm_po,
            "rm_picking": rm_picking,
            "rm_scrap": rm_scrap,
            "asset_location": asset_location,
            "asset_pr": asset_pr,
            "asset_po": asset_po,
            "asset_picking": asset_picking,
            "asset_bill": asset_bill,
            "consu_pr": consu_pr,
            "consu_po": consu_po,
            "consu_picking": consu_picking,
            "service_po": service_po,
            "service_acceptance": service_acceptance,
            "service_bill": service_bill,
        },
        "screenshots": {
            "01_home_dashboard.png": "home",
            "02_product_category_rm.png": "product_category_rm",
            "03_vendor_master.png": "vendor_master",
            "04_create_pr.png": "rm_pr_draft",
            "05_approve_pr.png": "rm_pr_approved",
            "06_confirm_po.png": "rm_po",
            "07_receipt_lot.png": "rm_receipt",
            "08_scrap_operation.png": "rm_scrap",
            "09_asset_pr.png": "asset_pr",
            "10_asset_location.png": "asset_receipt",
            "11_asset_bill.png": "asset_bill",
            "12_consumable_pr.png": "consu_pr",
            "13_consumable_receipt.png": "consu_receipt",
            "14_service_po.png": "service_po",
            "15_service_entry.png": "service_acceptance",
            "16_vendor_bill_je.png": "service_bill",
        },
    }

    OUT_JSON.write_text(json.dumps(docs, ensure_ascii=False, indent=2), encoding="utf-8")
    print(OUT_JSON)


if __name__ == "__main__":
    main()
