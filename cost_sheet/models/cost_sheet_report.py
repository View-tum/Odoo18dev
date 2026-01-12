# models/cost_sheet_report.py
from odoo import models, api, _


class ReportCostSheet(models.AbstractModel):
    _name = "report.cost_sheet.report_cost_sheet"
    _description = "Cost Sheet QWeb Data Provider"

    @api.model
    def _get_report_values(self, docids, data=None):
        # หา wizard ที่เรียกรายงาน
        wizard = None
        if data and data.get("wizard_id"):
            wizard = self.env["cost.sheet.wizard"].browse(data["wizard_id"])
        elif docids:
            wizard = self.env["cost.sheet.wizard"].browse(docids[0])

        # currency มาตรฐาน
        default_company = wizard.company_id if wizard else self.env.company
        default_currency = default_company.currency_id

        # helper format เงิน พร้อมสกุลเงิน
        def money(value, currency=None):
            value = value or 0.0
            cur = currency or default_currency
            if cur and cur.symbol:
                return f"{value:,.2f} {cur.symbol}"
            return f"{value:,.2f}"

        StockValuationLayer = self.env["stock.valuation.layer"]
        AccountMove = self.env["account.move"]

        sheets = []

        # หา landed costs ตามเงื่อนไข wizard
        if wizard:
            landed_costs = wizard._get_landed_costs()
        else:
            landed_costs = self.env["stock.landed.cost"].browse()

        for lc in landed_costs:
            # currency ของเอกสาร (ถ้ามี) ไม่งั้นใช้ของบริษัท
            currency = getattr(lc, "currency_id", False) or lc.company_id.currency_id or default_currency

            # ------------------------------------------------------------------
            # A) ดึงข้อมูลจากใบ Transfers:
            #    - qty_total = ปริมาณที่รับเข้า (ใช้ใน Total Quantity)
            #    - base_unit_cost = Unit Value เดิม จาก stock.valuation.layer
            #    - transfer_journal / transfer_journal_entry = JE ของใบรับเข้า
            # ------------------------------------------------------------------
            pickings = lc.picking_ids  # สมมุติใช้ใบ transfer แรก (ปกติ 1 ใบต่อ LC)
            qty_total = 0.0
            base_unit_cost = 0.0
            transfer_journal_entry = ""
            transfer_journal = ""

            # map เก็บ qty ตาม product จาก stock.move
            product_qty_map = {}
            all_moves = self.env["stock.move"]
            transfer_moves = self.env["account.move"]

            if pickings:
                for picking in pickings:
                    # 1) move ของแต่ละใบที่ Done
                    moves = picking.move_ids_without_package.filtered(lambda m: m.state == "done")
                    if not moves:
                        moves = picking.move_ids.filtered(lambda m: m.state == "done")

                    all_moves |= moves

                    # 1.1) qty รวม + qty ตาม product
                    for move in moves:
                        qty = move.quantity_done if "quantity_done" in move._fields else move.product_uom_qty
                        product_qty_map[move.product_id.id] = product_qty_map.get(move.product_id.id, 0.0) + qty
                        qty_total += qty

                    # 3) หา Journal Entry ของใบ Transfer ใบนี้
                    move_je = AccountMove.search(
                        [
                            ("ref", "ilike", picking.name),
                            ("company_id", "=", lc.company_id.id),
                            ("state", "!=", "cancel"),
                        ],
                        limit=1,
                        order="date desc, id desc",
                    )
                    transfer_moves |= move_je

                # 2) Base unit cost จาก valuation ของ moves ทั้งหมด
                if all_moves:
                    svls = StockValuationLayer.search(
                        [("stock_move_id", "in", all_moves.ids), ("company_id", "=", lc.company_id.id)]
                    )
                    if svls:
                        total_value = sum(svls.mapped("value"))
                        total_qty = sum(svls.mapped("quantity")) or qty_total
                        base_unit_cost = (total_value / total_qty) if total_qty else 0.0

                # 3.2) รวมชื่อ JE / Journal ทุกใบ
                if transfer_moves:
                    transfer_journal_entry = ", ".join(transfer_moves.mapped("name"))
                    # journal ส่วนใหญ่ชื่อเดียวกัน เลยรวมแบบ unique
                    journals = list({j for j in transfer_moves.mapped("journal_id.display_name") if j})
                    transfer_journal = ", ".join(journals)

            # ------------------------------------------------------------------
            # B) รายการต้นทุนจาก cost_lines (Cost Components)
            # ------------------------------------------------------------------
            lines = []
            for line in lc.cost_lines:
                lines.append(
                    {
                        "name": line.name,
                        "amount": line.price_unit,
                    }
                )

            # ------------------------------------------------------------------
            # C) Allocation by Product: ใช้ qty จาก product_qty_map (ไม่ใช้ adj.quantity แล้ว)
            # ------------------------------------------------------------------
            product_map = {}

            for adj in lc.valuation_adjustment_lines:
                product = adj.product_id
                if not product:
                    continue

                rec = product_map.setdefault(
                    product.id,
                    {
                        "name": product.display_name,
                        "qty": 0.0,
                        "additional": 0.0,
                    },
                )

                # qty ที่รับเข้าจริง
                rec["qty"] = product_qty_map.get(product.id, rec["qty"])

                # เก็บเฉพาะ Additional Landed Cost
                additional = getattr(adj, "additional_landed_cost", 0.0)
                rec["additional"] += additional

            # ถ้าไม่มี picking เลย ให้ fallback กลับไป sum qty จาก product_map
            if not qty_total:
                qty_total = sum(r["qty"] for r in product_map.values())

            # แปลงเป็น list และคำนวน cost / unit
            product_lines = []
            for rec in product_map.values():
                qty = rec["qty"] or 0.0
                additional = rec["additional"] or 0.0

                # ต้นทุนเดิมของสินค้า (goods) ใช้ base_unit_cost ที่คำนวณจาก SVL
                goods_total = base_unit_cost * qty
                final_total = goods_total + additional

                unit_cost_add = qty and (additional / qty) or 0.0
                unit_cost_final = qty and (final_total / qty) or 0.0

                product_lines.append(
                    {
                        "name": rec["name"],
                        "qty": qty,
                        "additional": additional,
                        "final": final_total,
                        "unit_cost_add": unit_cost_add,
                        "unit_cost_final": unit_cost_final,
                    }
                )

            # sort ตามชื่อสินค้าให้สวย ๆ
            product_lines.sort(key=lambda p: p["name"])

            # ------------------------------------------------------------------
            # D) Total Landed Cost + Unit Cost ใหม่
            #     - total = lc.amount_total
            #     - landed_unit_cost = total / qty_total
            #     - unit_cost (สุดท้าย) = base_unit_cost + landed_unit_cost
            # ------------------------------------------------------------------
            total = lc.amount_total or 0.0
            landed_unit_cost = (total / qty_total) if qty_total else 0.0
            unit_cost = base_unit_cost + landed_unit_cost

            # ถ้า wizard ไม่อยากเห็นรายละเอียด cost_lines ให้ซ่อน
            display_lines = lines if (not wizard or wizard.show_details) else []

            # ช่วงวันที่ (ใช้จาก wizard ถ้ามี, ไม่งั้นใช้วันเอกสาร)
            period_from = wizard.date_from if wizard and wizard.date_from else lc.date
            period_to = wizard.date_to if wizard and wizard.date_to else lc.date

            sheets.append(
                {
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
                    "unit_cost": unit_cost,
                    "base_unit_cost": base_unit_cost,
                    "landed_unit_cost": landed_unit_cost,
                    "product_lines": product_lines,
                    # รายละเอียดเพิ่มบนหัวรายงาน
                    "vendor": lc.vendor_bill_id.partner_id.display_name
                    if getattr(lc, "vendor_bill_id", False) and lc.vendor_bill_id.partner_id
                    else "",
                    "vendor_bill": lc.vendor_bill_id.name if getattr(lc, "vendor_bill_id", False) else "",
                    "journal_entry": lc.account_move_id.name
                    if getattr(lc, "account_move_id", False)
                    else "",
                    "journal": lc.account_journal_id.display_name
                    if getattr(lc, "account_journal_id", False)
                    else "",
                    # JE ของใบรับเข้า (Transfer)
                    "transfer_journal_entry": transfer_journal_entry,
                    "transfer_journal": transfer_journal,
                    # ชื่อใบ Transfer เดิม (ใช้เหมือนเดิมได้)
                    "pickings": ", ".join(lc.picking_ids.mapped("name")) if lc.picking_ids else "",
                }
            )

        return {
            "doc_ids": docids,
            "doc_model": "cost.sheet.wizard",
            "docs": wizard,
            "payload": {"sheets": sheets},
            "money": money,
        }
