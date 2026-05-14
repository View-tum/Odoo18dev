# models/cost_sheet_report.py
from odoo import models, api, _

class ReportCostSheet(models.AbstractModel):
    _name = "report.cost_sheet.report_cost_sheet"
    _description = "Cost Sheet QWeb Data Provider"

    @api.model
    def _get_report_values(self, docids, data=None):
        wizard = None
        if data and data.get("wizard_id"):
            wizard = self.env["cost.sheet.wizard"].browse(data["wizard_id"])
        elif docids:
            wizard = self.env["cost.sheet.wizard"].browse(docids[0])

        default_company = wizard.company_id if wizard else self.env.company
        default_currency = default_company.currency_id

        def money(value, currency=None):
            value = value or 0.0
            cur = currency or default_currency
            if cur and cur.symbol:
                return f"{value:,.2f} {cur.symbol}"
            return f"{value:,.2f}"

        StockValuationLayer = self.env["stock.valuation.layer"]
        AccountMove = self.env["account.move"]

        sheets = []

        if wizard:
            landed_costs = wizard._get_landed_costs()
        else:
            landed_costs = self.env["stock.landed.cost"].browse()

        for lc in landed_costs:
            currency = getattr(lc, "currency_id", False) or lc.company_id.currency_id or default_currency

            pickings = lc.picking_ids
            qty_total = 0.0
            transfer_journal_entry = ""
            transfer_journal = ""

            product_qty_map = {}
            all_moves = self.env["stock.move"]
            transfer_moves = self.env["account.move"]

            if pickings:
                for picking in pickings:
                    moves = picking.move_ids_without_package.filtered(lambda m: m.state == "done")
                    if not moves:
                        moves = picking.move_ids.filtered(lambda m: m.state == "done")

                    all_moves |= moves

                    for move in moves:
                        qty = move.quantity_done if "quantity_done" in move._fields else move.product_uom_qty
                        product_qty_map[move.product_id.id] = product_qty_map.get(move.product_id.id, 0.0) + qty
                        qty_total += qty

                    move_je = AccountMove.search([
                        ("ref", "ilike", picking.name),
                        ("company_id", "=", lc.company_id.id),
                        ("state", "!=", "cancel"),
                    ], limit=1, order="date desc, id desc")
                    transfer_moves |= move_je

                if transfer_moves:
                    transfer_journal_entry = ", ".join(transfer_moves.mapped("name"))
                    journals = list({j for j in transfer_moves.mapped("journal_id.display_name") if j})
                    transfer_journal = ", ".join(journals)

            # --- ดึง Unit Value (unit_cost) รายสินค้าจาก Stock Valuation Layer ---
            product_stats_map = {}
            if all_moves:
                svls = StockValuationLayer.search([
                    ("stock_move_id", "in", all_moves.ids), 
                    ("company_id", "=", lc.company_id.id)
                ])
                for svl in svls:
                    pid = svl.product_id.id
                    if pid not in product_stats_map:
                        product_stats_map[pid] = {"qty": 0.0, "value": 0.0}
                    product_stats_map[pid]["qty"] += svl.quantity
                    product_stats_map[pid]["value"] += svl.value

            lines = []
            for line in lc.cost_lines:
                lines.append({
                    "name": line.name,
                    "amount": line.price_unit,
                })

            product_map = {}
            for adj in lc.valuation_adjustment_lines:
                product = adj.product_id
                if not product: continue

                rec = product_map.setdefault(product.id, {
                    "product_id": product.id, # เก็บ ID ไว้ใช้อ้างอิง
                    "name": product.display_name,
                    "qty": 0.0,
                    "additional": 0.0,
                })
                rec["qty"] = product_qty_map.get(product.id, rec["qty"])
                rec["additional"] += getattr(adj, "additional_landed_cost", 0.0)

            if not qty_total:
                qty_total = sum(r["qty"] for r in product_map.values())

            # --- คำนวณ Allocation by Product ---
            product_lines = []
            total_goods = 0.0

            for rec in product_map.values():
                pid = rec["product_id"]
                qty = rec["qty"] or 0.0
                additional = rec["additional"] or 0.0

                # หาราคาต่อหน่วยจาก SVL ของใบรับสินค้านั้น (ป้องกันกรณีมีหลายล็อต ให้หาค่าเฉลี่ย)
                svl_stats = product_stats_map.get(pid, {"qty": 0.0, "value": 0.0})
                if svl_stats["qty"]:
                    unit_cost = svl_stats["value"] / svl_stats["qty"]
                else:
                    # Fallback ถ้าไม่เจอ SVL ให้ใช้ Standard Price
                    product_obj = self.env['product.product'].browse(pid)
                    unit_cost = product_obj.standard_price

                # คำนวณยอด
                goods_total = unit_cost * qty
                total_goods += goods_total

                final_total = goods_total + additional
                unit_cost_add = qty and (additional / qty) or 0.0
                unit_cost_final = qty and (final_total / qty) or 0.0

                product_lines.append({
                    "name": rec["name"],
                    "qty": qty,
                    "unit_cost": unit_cost,          # <--- เพิ่ม Unit Cost
                    "additional": additional,
                    "final": final_total,
                    "unit_cost_add": unit_cost_add,
                    "unit_cost_final": unit_cost_final,
                })

            product_lines.sort(key=lambda p: p["name"])

            # --- คำนวณสรุปยอด (Totals) ---
            total = lc.amount_total or 0.0
            total_shipment_cost = total + total_goods

            display_lines = lines if (not wizard or wizard.show_details) else []
            period_from = wizard.date_from if wizard and wizard.date_from else lc.date
            period_to = wizard.date_to if wizard and wizard.date_to else lc.date

            sheets.append({
                "title": lc.name,
                "company": lc.company_id.display_name if lc.company_id else "",
                "date_from": period_from,
                "date_to": period_to,
                "lc_date": lc.date,
                "description": wizard.description if wizard else "",
                "currency_symbol": currency.symbol if currency else "",
                "lines": display_lines,
                "total": total,
                "qty_total": qty_total,
                "total_goods": total_goods,                  # <--- แทน base_unit_cost เดิม
                "total_shipment_cost": total_shipment_cost,  # <--- แทน unit_cost รวมเดิม
                "product_lines": product_lines,
                "vendor": lc.vendor_bill_id.partner_id.display_name if getattr(lc, "vendor_bill_id", False) and lc.vendor_bill_id.partner_id else "",
                "vendor_bill": lc.vendor_bill_id.name if getattr(lc, "vendor_bill_id", False) else "",
                "journal_entry": lc.account_move_id.name if getattr(lc, "account_move_id", False) else "",
                "journal": lc.account_journal_id.display_name if getattr(lc, "account_journal_id", False) else "",
                "transfer_journal_entry": transfer_journal_entry,
                "transfer_journal": transfer_journal,
                "pickings": ", ".join(lc.picking_ids.mapped("name")) if lc.picking_ids else "",
            })

        return {
            "doc_ids": docids,
            "doc_model": "cost.sheet.wizard",
            "docs": wizard,
            "payload": {"sheets": sheets},
            "money": money,
        }