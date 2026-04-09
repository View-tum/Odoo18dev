# inventory_stock_card/wizards/inventory_stock_card_wizard.py
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date

from ..utils.inventory_stock_card_utils import local_midnight_to_utc_naive


class InventoryStockCardWizard(models.TransientModel):
    _name = "inventory.stock.card.wizard"
    _description = "Stock Card XLSX Export Wizard"
    _inherit = ["inventory.stock.card.query.mixin", "inventory.stock.card.xlsx.mixin"]

    def _get_report_base_filename(self):
        self.ensure_one()
        date_str = fields.Datetime.context_timestamp(self, fields.Datetime.now())
        buddhist_year = date_str.year + 543
        timestamp = date_str.strftime("%H%M%S")
        return f"Stock Card - {buddhist_year}{date_str.month:02d}{date_str.day:02d}-{timestamp}"

    company_id = fields.Many2one(
        "res.company", default=lambda s: s.env.company, required=True
    )
    product_ids = fields.Many2many("product.product", required=True)
    location_id = fields.Many2one(
        comodel_name="stock.location",
        domain="[('usage','=','internal'), ('company_id','in',[False, company_id])]",
    )
    include_child_locations = fields.Boolean(
        default=True, string="Include Sub-Locations"
    )
    date_from = fields.Datetime(required=True)
    date_to = fields.Datetime(required=True)
    at_date_only = fields.Boolean(default=False)
    show_lot = fields.Boolean(default=True)
    show_partner = fields.Boolean(default=True)
    show_doc = fields.Boolean(default=True)

    period_id = fields.Many2one(
        "inventory.stock.card.period",
        string="Period",
        domain=lambda self: [
            ("date_from", ">=", date(fields.Date.context_today(self).year, 1, 1)),
            ("date_from", "<", date(fields.Date.context_today(self).year + 1, 1, 1)),
        ],
    )

    @api.onchange("period_id")
    def _onchange_period_id_fill_dates(self):
        if self.period_id:
            self.date_from = local_midnight_to_utc_naive(
                self.env, self.period_id.date_from
            )
            self.date_to = local_midnight_to_utc_naive(self.env, self.period_id.date_to)

    @api.onchange("date_from", "date_to", "at_date_only")
    def _onchange_dates_clear_period(self):
        if not (self.date_from or self.date_to or self.at_date_only):
            return
        if self.period_id and self.period_id.date_from and self.period_id.date_to:
            df = local_midnight_to_utc_naive(self.env, self.period_id.date_from)
            dt = local_midnight_to_utc_naive(self.env, self.period_id.date_to)
            if self.date_from == df and self.date_to == dt:
                return
        self.period_id = False

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        self.env["inventory.stock.card.period"].sudo().ensure_current_year_periods()
        return res

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from >= rec.date_to:
                raise UserError(_("Date From must be before Date To."))

    def _build_report_payload(self):
        self.ensure_one()
        all_loc_ids = self._collect_location_ids()

        loc_map = {
            loc.id: loc for loc in self.env["stock.location"].browse(all_loc_ids)
        }

        sheets = []

        for product in self.product_ids:
            for loc_id in all_loc_ids:

                rows = self._run_stock_card_query(
                    product_id=product.id,
                    location_ids=[loc_id],
                    opening_location_ids=[loc_id],
                    date_from=self.date_from,
                    date_to=self.date_to,
                    company_id=self.company_id.id,
                )

                opening_qty = 0.0
                opening_val = 0.0
                has_movements = False

                for rr in rows:
                    if rr.get("rowtype") == "opening":
                        opening_qty = rr.get("delta") or 0.0
                        opening_val = rr.get("valuation_amount") or 0.0
                    elif rr.get("rowtype") == "line":
                        has_movements = True

                opening_qty = round(opening_qty, 6)
                opening_val = round(opening_val, 6)

                if not has_movements and abs(opening_qty) == 0:
                    continue

                if product.default_code and f"[{product.default_code}]" in (
                    product.name or ""
                ):
                    clean_name = (
                        (product.name or "")
                        .replace(f"[{product.default_code}]", "")
                        .strip()
                    )
                else:
                    clean_name = product.name or product.display_name or ""
                prod_label = (
                    f"[{product.default_code}] {clean_name}".strip()
                    if product.default_code
                    else clean_name
                )

                current_location = loc_map.get(loc_id)
                location_name = (
                    current_location.display_name if current_location else ""
                )

                sheet = {
                    "title": "Stock Card",
                    "company": self.company_id.display_name or "",
                    "product": prod_label,
                    "uom": product.uom_id.display_name or "",
                    "location": location_name,
                    "date_from": self.date_from,
                    "date_to": self.date_to,
                    "currency_symbol": self.company_id.currency_id.symbol or "",
                    "at_date_only": bool(self.at_date_only),
                    "opening_qty": opening_qty,
                    "opening_val": opening_val,
                    "opening_price": (
                        (opening_val / opening_qty) if opening_qty else 0.0
                    ),
                    "lines": [],
                }

                if self.at_date_only:
                    balance_qty = opening_qty + sum(
                        (r.get("delta") or 0.0)
                        for r in rows
                        if r.get("rowtype") == "line"
                    )
                    balance_val = opening_val + sum(
                        (r.get("valuation_amount") or 0.0)
                        * (-1 if (r.get("qty_out") or 0.0) > 0 else 1)
                        for r in rows
                        if r.get("rowtype") == "line"
                    )

                    balance_qty = round(balance_qty, 6)
                    balance_val = round(balance_val, 6)

                    sheet["opening_qty"] = None
                    sheet["lines"] = [
                        {
                            "is_opening": False,
                            "date": self.date_to,
                            "picking": "-",
                            "origin": "-",
                            "partner": "-",
                            "lot_name": "",
                            "unit_price": 0.0,
                            "valuation_amount": 0.0,
                            "qty_in": 0.0,
                            "qty_out": 0.0,
                            "journal_entry": "",
                            "balance_qty": balance_qty,
                            "balance_val": balance_val,
                            "balance_price": (
                                (balance_val / balance_qty) if balance_qty else 0.0
                            ),
                        }
                    ]
                else:
                    bal_qty = opening_qty
                    bal_val = opening_val

                    incoming_cost_map = {}

                    for rr in rows:
                        if rr.get("rowtype") != "line":
                            continue

                        bal_qty = round(bal_qty, 6)
                        bal_val = round(bal_val, 6)

                        line_open_qty = bal_qty
                        line_open_val = bal_val
                        line_open_price = (bal_val / bal_qty) if bal_qty else 0.0

                        qty_in = rr.get("qty_in") or 0.0
                        qty_out = rr.get("qty_out") or 0.0
                        origin_key = rr.get("origin")

                        unit_price = rr.get("unit_price") or 0.0
                        val_trans = rr.get("valuation_amount") or 0.0

                        if (
                            val_trans == 0.0
                            and (qty_in > 0 or qty_out > 0)
                            and unit_price > 0
                        ):
                            val_trans = (qty_in if qty_in > 0 else qty_out) * unit_price

                        if qty_in > 0 and origin_key and val_trans > 0:
                            current_cost = val_trans / qty_in
                            incoming_cost_map[origin_key] = current_cost

                        if (
                            qty_out > 0
                            and origin_key
                            and origin_key in incoming_cost_map
                        ):
                            cached_cost = incoming_cost_map[origin_key]
                            val_trans = qty_out * cached_cost
                            unit_price = cached_cost

                        val_trans = round(val_trans, 6)

                        if qty_out > 0:
                            bal_val -= val_trans
                        else:
                            bal_val += val_trans

                        bal_qty += rr.get("delta") or 0.0

                        bal_qty = round(bal_qty, 6)
                        bal_val = round(bal_val, 6)

                        if abs(bal_qty) < 0.000001:
                            bal_qty = 0.0
                        if abs(bal_val) < 0.000001:
                            bal_val = 0.0

                        line_bal_price = (bal_val / bal_qty) if bal_qty else 0.0

                        picking_val = rr.get("picking") if self.show_doc else ""
                        origin_val = rr.get("origin") if self.show_doc else ""
                        partner_val = rr.get("partner") if self.show_partner else ""
                        lot_name_val = rr.get("lot_name") if self.show_lot else ""
                        journal_entry_val = rr.get("journal_entry") or ""

                        sheet["lines"].append(
                            {
                                "is_opening": False,
                                "date": rr.get("date"),
                                "picking": picking_val,
                                "origin": origin_val,
                                "partner": partner_val,
                                "lot_name": lot_name_val,
                                "journal_entry": journal_entry_val,
                                "line_open_qty": line_open_qty,
                                "line_open_price": line_open_price,
                                "line_open_val": line_open_val,
                                "qty_in": qty_in,
                                "qty_out": qty_out,
                                "unit_price": unit_price,
                                "valuation_amount": val_trans,
                                "balance_qty": bal_qty,
                                "balance_val": bal_val,
                                "balance_price": line_bal_price,
                            }
                        )
                sheets.append(sheet)

        return {"sheets": sheets}

    def _report_action(self, report_xmlid, report_type="qweb-pdf"):
        self.ensure_one()
        action = self.env.ref(report_xmlid).report_action(
            self, data={"wizard_id": self.id}
        )
        action["report_type"] = report_type
        return action

    def action_view_html(self):
        return self._report_action(
            "inventory_stock_card.action_report_stock_card", "qweb-html"
        )

    def action_export_pdf(self):
        action = self._report_action(
            "inventory_stock_card.action_report_stock_card", "qweb-pdf"
        )
        action["close_on_report_download"] = True
        return action
