# inventory_stock_card/wizards/inventory_stock_card_query_mixin.py
from odoo import models, api


class InventoryStockCardQueryMixin(models.AbstractModel):
    _name = "inventory.stock.card.query.mixin"
    _description = "Stock Card Database Query Logic"

    def _collect_location_ids(self):
        self.ensure_one()

        domain = [("usage", "=", "internal")]
        if self.company_id:
            domain.append(("company_id", "in", [False, self.company_id.id]))

        if not self.location_id:
            return self.env["stock.location"].search(domain).ids

        if self.include_child_locations:
            domain.append(("id", "child_of", self.location_id.id))
            return self.env["stock.location"].search(domain).ids
        else:
            if self.location_id.usage == "internal":
                return [self.location_id.id]
            else:
                return []

    def _run_stock_card_query(
        self,
        product_id,
        location_ids,
        opening_location_ids,
        date_from,
        date_to,
        company_id,
    ):
        Product = (
            self.env["product.product"].with_company(company_id).browse(product_id)
        )
        product_uom = Product.uom_id

        domain_op = [
            ("state", "=", "done"),
            ("product_id", "=", product_id),
            ("company_id", "=", company_id),
            ("date", "<", date_from),
            "|",
            ("location_id", "in", opening_location_ids),
            ("location_dest_id", "in", opening_location_ids),
        ]

        smls_op = self.env["stock.move.line"].search(domain_op)

        opening_qty = 0.0
        opening_val = 0.0

        for line in smls_op:
            qty = line.quantity if "quantity" in line else line.qty_done

            if line.product_uom_id and line.product_uom_id != product_uom:
                qty = line.product_uom_id._compute_quantity(qty, product_uom)

            unit_cost = 0.0
            layers = line.move_id.stock_valuation_layer_ids
            if layers:
                val_sum = sum(layers.mapped("value"))
                qty_sum = sum(layers.mapped("quantity"))
                if qty_sum:
                    unit_cost = abs(val_sum / qty_sum)

            if unit_cost == 0.0:
                unit_cost = line.move_id.price_unit

            if unit_cost == 0.0 and line.move_id.origin:
                siblings = self.env["stock.move"].search(
                    [
                        ("origin", "=", line.move_id.origin),
                        ("product_id", "=", product_id),
                        ("state", "=", "done"),
                        ("id", "!=", line.move_id.id),
                    ],
                    limit=5,
                )
                for sib in siblings:
                    if sib.stock_valuation_layer_ids:
                        s_val = sum(sib.stock_valuation_layer_ids.mapped("value"))
                        s_qty = sum(sib.stock_valuation_layer_ids.mapped("quantity"))
                        if s_qty:
                            unit_cost = abs(s_val / s_qty)
                            break
                    if unit_cost == 0.0 and sib.price_unit > 0:
                        unit_cost = sib.price_unit
                        break

            if unit_cost == 0.0:
                unit_cost = Product.standard_price

            is_in = (line.location_dest_id.id in opening_location_ids) and (
                line.location_id.id not in opening_location_ids
            )
            is_out = (line.location_id.id in opening_location_ids) and (
                line.location_dest_id.id not in opening_location_ids
            )

            if is_in:
                opening_qty += qty
                opening_val += qty * unit_cost
            elif is_out:
                opening_qty -= qty
                opening_val -= qty * unit_cost

        domain_period = [
            ("state", "=", "done"),
            ("product_id", "=", product_id),
            ("company_id", "=", company_id),
            ("date", ">=", date_from),
            ("date", "<", date_to),
            "|",
            ("location_id", "in", location_ids),
            ("location_dest_id", "in", location_ids),
        ]

        smls_period = self.env["stock.move.line"].search(
            domain_period, order="date, id"
        )

        results = []

        for line in smls_period:
            qty = line.quantity if "quantity" in line else line.qty_done

            if line.product_uom_id and line.product_uom_id != product_uom:
                qty = line.product_uom_id._compute_quantity(qty, product_uom)

            unit_cost = 0.0
            layers = line.move_id.stock_valuation_layer_ids
            if layers:
                val_sum = sum(layers.mapped("value"))
                qty_sum = sum(layers.mapped("quantity"))
                if qty_sum:
                    unit_cost = abs(val_sum / qty_sum)

            if unit_cost == 0.0:
                unit_cost = line.move_id.price_unit

            if unit_cost == 0.0 and line.move_id.origin:
                siblings = self.env["stock.move"].search(
                    [
                        ("origin", "=", line.move_id.origin),
                        ("product_id", "=", product_id),
                        ("state", "=", "done"),
                        ("id", "!=", line.move_id.id),
                    ],
                    limit=5,
                )
                for sib in siblings:
                    if sib.stock_valuation_layer_ids:
                        s_val = sum(sib.stock_valuation_layer_ids.mapped("value"))
                        s_qty = sum(sib.stock_valuation_layer_ids.mapped("quantity"))
                        if s_qty:
                            unit_cost = abs(s_val / s_qty)
                            break
                    if unit_cost == 0.0 and sib.price_unit > 0:
                        unit_cost = sib.price_unit
                        break

            if unit_cost == 0.0:
                unit_cost = Product.standard_price

            is_in = (line.location_dest_id.id in location_ids) and (
                line.location_id.id not in location_ids
            )
            is_out = (line.location_id.id in location_ids) and (
                line.location_dest_id.id not in location_ids
            )

            if not is_in and not is_out:
                continue

            qty_in = qty if is_in else 0.0
            qty_out = qty if is_out else 0.0
            delta = qty_in - qty_out
            valuation_amount = qty * unit_cost

            origin_raw = line.move_id.origin or ""
            picking = line.picking_id.name or ""
            lot_name = line.lot_id.name or ""

            partner_name = (
                line.picking_id.partner_id.display_name
                or line.move_id.partner_id.display_name
            )
            if not partner_name and origin_raw:
                if "purchase.order" in self.env:
                    po = self.env["purchase.order"].search(
                        [("name", "=", origin_raw)], limit=1
                    )
                    if po:
                        partner_name = po.partner_id.display_name
                if not partner_name and "sale.order" in self.env:
                    so = self.env["sale.order"].search(
                        [("name", "=", origin_raw)], limit=1
                    )
                    if so:
                        partner_name = so.partner_id.display_name
            partner_name = partner_name or ""

            origin_display = origin_raw
            if origin_raw:
                org_items = [x.strip() for x in origin_raw.split(",") if x.strip()]
                origin_display = ", \n".join(org_items)

            am_name = ""
            accounting_date = None
            if layers:
                am = layers.mapped("account_move_id")
                if am:
                    am_name = am[0].name
                    accounting_date = am[0].date

            results.append(
                {
                    "rowtype": "line",
                    "line_id": line.id,
                    "date": line.date,
                    "picking": picking,
                    "origin": origin_display,
                    "partner": partner_name,
                    "lot_id": line.lot_id.id,
                    "lot_name": lot_name,
                    "qty_in": qty_in,
                    "qty_out": qty_out,
                    "delta": delta,
                    "unit_price": unit_cost,
                    "valuation_amount": valuation_amount,
                    "journal_entry": am_name,
                    "accounting_date": accounting_date,
                }
            )

        opening_row = {
            "rowtype": "opening",
            "line_id": None,
            "date": None,
            "picking": None,
            "origin": None,
            "partner": None,
            "lot_id": None,
            "lot_name": None,
            "qty_in": None,
            "qty_out": None,
            "delta": opening_qty,
            "unit_price": None,
            "valuation_amount": opening_val,
            "journal_entry": None,
            "accounting_date": None,
        }

        results.insert(0, opening_row)

        return results
