# trip_closing_report/report/trip_closing_queries.py
# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, timedelta, time
import pytz
import logging

_logger = logging.getLogger(__name__)


class TripClosingQueries(models.AbstractModel):
    _name = "trip.closing.queries"
    _description = "Trip Closing SQL Queries (maintainable)"

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------
    def _fetchall_dict(self):
        cr = self.env.cr
        cols = [c.name for c in cr.description]
        return [dict(zip(cols, row)) for row in cr.fetchall()]

    def get_period_label(self, wizard):
        ds = wizard.date_start
        de = wizard.date_end
        if not ds or not de:
            return ""
        return f"{ds} - {de}"
    
    def _date_to_utc_start(self, d):
        """local date -> utc naive datetime at start of day"""
        tz = pytz.timezone(self.env.user.tz or "UTC")
        dt_local = tz.localize(datetime.combine(d, time.min))
        return dt_local.astimezone(pytz.utc).replace(tzinfo=None)

    def _date_end_exclusive(self, d):
        """date -> next date (exclusive end for DATE fields)"""
        return d + timedelta(days=1)
    
    def _build_page1_summary(self, totals: dict) -> dict:
        """
        Map totals -> summary keys that Page 1 template expects.
        หมายเหตุ: ตอนนี้ยังไม่คำนวณ VAT/ยอดรวมภาษีจริง เพราะเราดึงจาก invoice_line.price_subtotal (untaxed)
        ถ้าต้องการ VAT จริง ต้อง query tax เพิ่มภายหลัง
        """
        gross = float(totals.get("gross_sales") or 0.0)
        discount = float(totals.get("discount_total") or 0.0)

        untaxed = float(totals.get("net_sales") or 0.0)  # net แบบเดิม (ไม่รวม VAT)
        vat = float(totals.get("vat_amount") or 0.0)
        total = float(totals.get("total_amount") or 0.0) or (untaxed + vat)

        # คืนของ/ลดหนี้ (รวม VAT) — ใช้ตัวใหม่เป็นหลัก
        return_total = float(
            totals.get("return_total_amount")
            or totals.get("return_amount")
            or 0.0
        )
        net_after_return = total - return_total
        return_amount = float(totals.get("return_amount") or 0.0)

        return {
            "gross_sales": gross,
            "discount_amount": discount,
            "untaxed_amount": untaxed,
            "vat_amount": vat,
            "total_amount": total,
            "return_amount": return_total,
            "net_sales": net_after_return,
        }

    # ------------------------------------------------------------
    # Location utilities (FG roots)
    # ------------------------------------------------------------
    def _search_fg_locations(self):
        """
        ปรับ domain ตรงนี้ให้ตรงระบบจริงของคุณได้
        ตอนนี้ใช้ชื่อ path: GMP/Stock/FG, GMP/SC01/FG ตามที่คุณแจ้ง
        """
        names = ["GMP/Stock/FG", "GMP/SC01/FG"]
        return self.env["stock.location"].search([("complete_name", "in", names)])

    
    def _search_carsale_root_locations(self):
        """
        หา root ของ CARSALE (ถ้าระบบคุณมี root เดียว/หลาย root ก็รองรับ)
        ปัจจุบันอิงจากชื่อ path ที่มีคำว่า 'CARSALE' และเป็น internal
        """
        return self.env["stock.location"].search([
            ("usage", "=", "internal"),
            ("complete_name", "ilike", "CARSALE"),
        ])

    # ------------------------------------------------------------
    # Main: Build per-vehicle (carsale location) data
    # ------------------------------------------------------------
    
    def build_driver_data(self, wizard):
        """
        Phase 1:
        - Wizard filter: date_start/date_end + driver_id (res.users)
        - Internal transfer: FG -> CARSALE (นับ trip matrix)
        - Sales: OUT (done outgoing) ผูก sale.order.user_id = driver_id
        - Price/Amount/Net sales: อิง sale.order.line (price_subtotal) แบบไม่ใช้ invoice
        คืน dict ที่ shape ใกล้เคียง build_vehicle_data เพื่อ reuse QWeb เดิม
        """
        ds, de = wizard.date_start, wizard.date_end
        driver = wizard.driver_id
        vehicle_name = wizard.location_id.display_name if wizard.location_id else "ALL CARSALE"

        if not ds or not de:
            return {
                "vehicle_name": vehicle_name,
                "trip_numbers": [],
                "date_start": ds,
                "date_end": de,
                "lines": [],
                "totals": {},
            }

       # ทั้งเดือนของ ds
        month_start = ds.replace(day=1)
        if month_start.month == 12:
            next_month_start = month_start.replace(year=month_start.year + 1, month=1, day=1)
        else:
            next_month_start = month_start.replace(month=month_start.month + 1, day=1)

        it_start_ts = self._date_to_utc_start(month_start)
        it_end_ts_excl = self._date_to_utc_start(next_month_start)
        # Datetime range (UTC) สำหรับ stock_picking.date_done
        start_ts, end_ts_excl = wizard._get_utc_dt_range_exclusive()

        fg_locs = self._search_fg_locations()
        fg_ids = fg_locs.ids or []

        if wizard.location_id:
            carsale_root_ids = [wizard.location_id.id]
        else:
            carsale_roots = self._search_carsale_root_locations()
            carsale_root_ids = carsale_roots.ids or []

        # 1) Trip matrix (internal transfer by trip_no/product) - รวมทุก CARSALE
        trip_matrix = self._sql_trip_matrix_all_carsale(
            it_start_ts=it_start_ts,
            it_end_ts_excl=it_end_ts_excl,
            fg_ids=fg_ids,
            carsale_root_ids=carsale_root_ids,
        )

        end_date_excl = self._date_end_exclusive(de)

        # 2) Sales basic by driver (no invoice) within full selected range
        sales_basic = self._sql_sale_invoice_summary_all_carsale_by_salesperson(
            carsale_root_ids=carsale_root_ids,
            salesperson_user_id=driver.id,
            start_ts=start_ts,
            end_ts_excl=end_ts_excl,
            start_date=ds,
            end_date_excl=end_date_excl,
        )

        product_ids = sorted(set(trip_matrix["product_ids"]) | set(sales_basic["product_ids"]))
        products = self.env["product.product"].browse(product_ids).sudo()

        trip_nos = trip_matrix["trip_nos"]
        trip_qty_map = trip_matrix["trip_qty_map"]
        transfer_total_map = trip_matrix["transfer_total_map"]

        sold_qty_map   = sales_basic.get("sold_qty_map", {})
        unit_price_map = sales_basic.get("unit_price_map", {})
        inv_amount_map = sales_basic.get("inv_amount_map", {})

        lines = []
        for p in products:
            trip_cols = [(trip_qty_map.get((p.id, tno), 0.0) or 0.0) for tno in trip_nos]

            transfer_total = transfer_total_map.get(p.id, 0.0) or 0.0
            sold_qty = sold_qty_map.get(p.id, 0.0) or 0.0
            price = unit_price_map.get(p.id, 0.0) or 0.0
            if (not price) and (sold_qty_map.get(p.id, 0.0) or 0.0) > 0:
                amt = inv_amount_map.get(p.id, 0.0) or 0.0
                sqty = sold_qty_map.get(p.id, 0.0) or 0.0
                if amt and sqty:
                    price = amt / sqty

            # ถ้ามี inv_amount_map ใช้มันก่อน, ไม่งั้นค่อยคูณ sold_qty * price
            amount = inv_amount_map.get(p.id)
            if amount is None:
                amount = sold_qty * price
            amount = float(amount or 0.0)
            amount_money = float((sold_qty or 0.0) * (price or 0.0))
            latest_day = trip_matrix.get("latest_trip_day_map", {}).get(p.id)

            lines.append({
                "product_id": p.id,
                "product_code": p.default_code or "",
                "product_name": p.display_name or "",

                "trip_qty": trip_cols,
                "transfer_total": transfer_total,
                "sold_qty": sold_qty,
                "price": price,
                "amount_money": float((sold_qty or 0.0) * (price or 0.0)),
                "amount": amount,
                "latest_transfer_date": latest_day,

                # เผื่อ template/logic เก่า
                "trip_qtys": trip_cols,
                "total_transfer": transfer_total,
            })

        totals = {
            "sold_qty_total": sum(l["sold_qty"] for l in lines),
            "transfer_qty_total": sum(l.get("transfer_total", 0.0) for l in lines),
            "sold_amount_total": sum(l["amount_money"] for l in lines),

            "gross_sales": sales_basic.get("gross_sales", 0.0),
            "discount_total": sales_basic.get("discount_total", 0.0),
            "net_sales": sales_basic.get("net_sales", 0.0),
        }

        receipts_summary = self._sql_receipts_summary_all_carsale_by_salesperson(
            carsale_root_ids=carsale_root_ids,
            salesperson_user_id=driver.id,
            start_ts=start_ts,
            end_ts_excl=end_ts_excl,
            start_date=ds,
            end_date_excl=self._date_end_exclusive(de),
        )
        
        bank_transfers, cheques = self._sql_receipts_details_all_carsale_by_salesperson(
            carsale_root_ids=carsale_root_ids,
            salesperson_user_id=driver.id,
            start_ts=start_ts,
            end_ts_excl=end_ts_excl,
            start_date=ds,
            end_date_excl=self._date_end_exclusive(de),
        )

        # [UPDATE] อัปเดตยอดเงินใน totals
        totals.update({
            "gross_sales": receipts_summary["gross_sales"],
            "discount_total": receipts_summary["discount_total"],
            "net_sales": receipts_summary["net_sales"],
            "vat_amount": receipts_summary.get("vat_amount", 0.0),
            "total_amount": receipts_summary.get("total_amount", 0.0),
            "cash_received": receipts_summary["cash_received"],
            "transfer_received": receipts_summary["transfer_received"],
            "cheque_received": receipts_summary["cheque_received"],
            "received_total": receipts_summary["received_total"],
            "ar_unpaid": receipts_summary["ar_unpaid"],
        })

        summary = self._build_page1_summary(totals)
        totals.update(summary)

        return {
            "vehicle_name": vehicle_name,
            "carsale_location_name": vehicle_name,
            "trip_numbers": trip_nos,
            "trip_nos": trip_nos,
            "date_start": ds,
            "date_end": de,
            "lines": lines,
            "totals": totals,
            "summary": summary,
            "bank_transfers": bank_transfers,
            "cheques": cheques,
            
            # [ADD] เพิ่มส่วนนี้เพื่อกัน Error Template
            "trip_info": {
                "odometer_start": 0,
                "odometer_end": 0,
                "distance": 0,
            },
            "final_summary": {
                "grand_total": totals.get("net_sales", 0.0), # หรือค่าที่ต้องการ
            },
            "cash_summary": {}, # เผื่อ template เรียก
        }

    def build_vehicle_data(self, wizard, carsale_loc):
        """
        คืน dict สำหรับ QWeb/XLSX 1 คัน (1 carsale location)
        """
        ds, de = wizard.date_start, wizard.date_end
        driver = wizard.driver_id
        if not ds or not de:
            return {
                "carsale_location_name": carsale_loc.display_name,
                "date_start": ds,
                "date_end": de,
                "vehicle_name": carsale_loc.display_name,
                "trip_nos": [],
                "lines": [],
                "totals": {},
                "bank_transfers": [],
                "cheques": [],
            }

        carsale_roots = self._search_carsale_root_locations()
        carsale_root_ids = [carsale_loc.id]

        month_start = ds.replace(day=1)
        if month_start.month == 12:
            next_month_start = month_start.replace(year=month_start.year + 1, month=1, day=1)
        else:
            next_month_start = month_start.replace(month=month_start.month + 1, day=1)

        it_start_ts = self._date_to_utc_start(month_start)
        it_end_ts_excl = self._date_to_utc_start(next_month_start)

        # Datetime range (UTC) สำหรับ stock_picking.date_done
        start_ts, end_ts_excl = wizard._get_utc_dt_range_exclusive()

        # Date range สำหรับ invoice_date / account_payment.date
        start_date = ds
        end_date_excl = self._date_end_exclusive(de)

        fg_locs = self._search_fg_locations()
        fg_ids = fg_locs.ids or []

        # 1) Trip matrix (internal transfer by trip_no/product)
        trip_matrix = self._sql_trip_matrix(
            carsale_loc_id=carsale_loc.id,
            it_start_ts=it_start_ts,
            it_end_ts_excl=it_end_ts_excl,
            fg_ids=fg_ids,
        )

        # 2) OUT + Invoice summary (sell qty, invoice amounts) within full selected range ds..de
        sale_summary = self._sql_sale_invoice_summary_all_carsale_by_salesperson(
            carsale_root_ids=carsale_root_ids,
            salesperson_user_id=driver.id if driver else None,
            start_ts=start_ts,
            end_ts_excl=end_ts_excl,
            start_date=ds,
            end_date_excl=end_date_excl,
        )

        # 3) Merge into lines
        #    key = product_id
        product_ids = sorted(set(trip_matrix["product_ids"]) | set(sale_summary["product_ids"]))
        products = self.env["product.product"].browse(product_ids).sudo()

        trip_nos = trip_matrix["trip_nos"]  # [1..N]
        trip_qty_map = trip_matrix["trip_qty_map"]  # (product_id, trip_no) -> qty
        transfer_total_map = trip_matrix["transfer_total_map"]  # product_id -> qty

        sold_qty_map = sale_summary["sold_qty_map"]            # product_id -> qty
        inv_qty_map = sale_summary["inv_qty_map"]              # product_id -> qty (invoiced)
        inv_amount_map = sale_summary["inv_amount_map"]        # product_id -> amount (net)
        unit_price_map = sale_summary["unit_price_map"]        # product_id -> price (avg)

        lines = []
        for p in products:
            trip_cols = []
            for tno in trip_nos:
                trip_cols.append(trip_qty_map.get((p.id, tno), 0.0) or 0.0)

            transfer_total = transfer_total_map.get(p.id, 0.0) or 0.0
            sold_qty = sold_qty_map.get(p.id, 0.0) or 0.0

            # ราคา: ใช้ avg unit price จาก invoice (ถ้าไม่มี invoice ให้ 0)
            price = unit_price_map.get(p.id, 0.0) or 0.0
            if (not price) and sold_qty:
                inv_amt = inv_amount_map.get(p.id, 0.0) or 0.0
                if inv_amt:
                    price = inv_amt / sold_qty
            amount = inv_amount_map.get(p.id)
            if amount is None:
                amount = sold_qty * price
            amount = float(amount or 0.0)
            amount_money = float((sold_qty or 0.0) * (price or 0.0))
            latest_day = trip_matrix.get("latest_trip_day_map", {}).get(p.id)

            lines.append({
                "product_id": p.id,
                "product_code": p.default_code or "",
                "product_name": p.display_name or "",
                "trip_qtys": trip_cols,               # columns 1..N
                "transfer_total": transfer_total,     # column รวม
                "sold_qty": sold_qty,                 # column ขาย
                "price": price,                       # column ราคา (จาก invoice avg)
                "amount": amount,                     # column จำนวนเงิน
                "amount_money": amount_money,
                "latest_transfer_date": latest_day,
                # เผื่อใช้ภายหลัง
                "inv_qty": inv_qty_map.get(p.id, 0.0) or 0.0,
                "inv_amount": inv_amount_map.get(p.id, 0.0) or 0.0,
            })

        # 4) Receipts summary + details (อิง payment)
        receipts_summary = self._sql_receipts_summary_all_carsale_by_salesperson(
            carsale_root_ids=carsale_root_ids,
            salesperson_user_id=driver.id if driver else None,
            start_ts=start_ts,
            end_ts_excl=end_ts_excl,
            start_date=ds,
            end_date_excl=end_date_excl,
        )
        bank_transfers, cheques = self._sql_receipts_details_all_carsale_by_salesperson(
            carsale_root_ids=carsale_root_ids,
            salesperson_user_id=driver.id if driver else None,
            start_ts=start_ts,
            end_ts_excl=end_ts_excl,
            start_date=ds,
            end_date_excl=end_date_excl,
        )

        # รวมยอดแบบง่ายก่อน (คุณจะ map ไปหน้า summary ได้ต่อ)
        totals = {
            "sold_amount_total": sum(l["amount"] for l in lines),
            "sold_qty_total": sum(l["sold_qty"] for l in lines),
            "transfer_qty_total": sum(l["transfer_total"] for l in lines),
        }

        # รวมยอดของหน้า per-vehicle
        totals.update({
            "gross_sales": receipts_summary["gross_sales"],
            "discount_total": receipts_summary["discount_total"],
            "net_sales": receipts_summary["net_sales"],
            "vat_amount": receipts_summary.get("vat_amount", 0.0),
            "total_amount": receipts_summary.get("total_amount", 0.0),
            "cash_received": receipts_summary["cash_received"],
            "transfer_received": receipts_summary["transfer_received"],
            "cheque_received": receipts_summary["cheque_received"],
            "received_total": receipts_summary["received_total"],
            "ar_unpaid": receipts_summary["ar_unpaid"],
        })

        summary = self._build_page1_summary(totals)
        totals.update(summary)

        return {
            "carsale_location_name": carsale_loc.display_name,
            "date_start": ds,
            "date_end": de,
            "trip_nos": trip_nos,
            "lines": lines,
            "totals": totals,
            "summary": summary,
            "bank_transfers": bank_transfers,
            "cheques": cheques,

            "trip_info": {
                "odometer_start": 0,
                "odometer_end": 0,
                "distance": 0,
            },
            "final_summary": {
                "grand_total": totals.get("net_sales", 0.0),
            },
            "cash_summary": {},
        }

    # ------------------------------------------------------------
    # SQL: Trip matrix (internal transfer: FG -> CARSALE) within 1-14 window
    # ------------------------------------------------------------
    def _sql_trip_matrix(self, carsale_loc_id, it_start_ts, it_end_ts_excl, fg_ids):
        """
        Returns:
          trip_nos: [1..N]
          product_ids: []
          trip_qty_map: {(product_id, trip_no): qty}
          transfer_total_map: {product_id: qty}
        """
        # no internal window => empty
        if not it_start_ts or not it_end_ts_excl:
            return {
                "trip_nos": [],
                "product_ids": [],
                "trip_qty_map": {},
                "transfer_total_map": {},
            }

        sql = """
            WITH
            params AS (
                SELECT
                    %(it_start_ts)s::timestamp AS it_start_ts,
                    %(it_end_ts_excl)s::timestamp AS it_end_ts_excl,
                    %(carsale_loc_id)s::int AS carsale_loc_id,
                    %(fg_ids)s::int[] AS fg_ids
            ),
            carsale_tree AS (
                SELECT sl.id
                FROM stock_location sl, params p
                WHERE sl.id = p.carsale_loc_id
                    OR sl.parent_path LIKE ('%%/' || p.carsale_loc_id || '/%%')
            ),
            fg_tree AS (
                SELECT sl.id
                FROM stock_location sl, params p
                WHERE
                    (p.fg_ids IS NOT NULL AND array_length(p.fg_ids, 1) > 0)
                    AND (
                        sl.id = ANY(p.fg_ids)
                        OR EXISTS (
                            SELECT 1
                            FROM unnest(p.fg_ids) fg_id
                            WHERE sl.parent_path LIKE ('%%/' || fg_id || '/%%')
                        )
                    )
            ),
            internal_pickings AS (
                SELECT
                    sp.id,
                    (sp.date_done AT TIME ZONE 'UTC' AT TIME ZONE %(tz)s)::date AS trip_day
                FROM stock_picking sp
                JOIN stock_picking_type spt ON spt.id = sp.picking_type_id
                JOIN params p ON TRUE
                WHERE sp.state = 'done'
                AND spt.code = 'internal'
                AND sp.date_done >= p.it_start_ts
                AND sp.date_done <  p.it_end_ts_excl
                AND sp.location_dest_id IN (SELECT id FROM carsale_tree)
                AND sp.location_id      IN (SELECT id FROM fg_tree)
            ),
            trip_days AS (
                SELECT
                    trip_day,
                    DENSE_RANK() OVER (ORDER BY trip_day) AS trip_no
                FROM (SELECT DISTINCT trip_day FROM internal_pickings) d
            ),
            pickings_with_trip AS (
                SELECT ip.id, td.trip_no
                FROM internal_pickings ip
                JOIN trip_days td ON td.trip_day = ip.trip_day
            ),
            transfer_lines AS (
                SELECT
                    sml.product_id,
                    pwt.trip_no,
                    SUM(sml.quantity) AS qty
                FROM stock_move_line sml
                JOIN pickings_with_trip pwt ON pwt.id = sml.picking_id
                WHERE sml.state = 'done'
                GROUP BY sml.product_id, pwt.trip_no
            ),
            latest_by_product AS (
                SELECT
                    sml.product_id,
                    MAX((sp.date_done AT TIME ZONE 'UTC' AT TIME ZONE %(tz)s)::date) AS latest_trip_day
                FROM stock_move_line sml
                JOIN stock_picking sp ON sp.id = sml.picking_id
                JOIN stock_picking_type spt ON spt.id = sp.picking_type_id
                JOIN params p ON TRUE
                WHERE sml.state = 'done'
                AND sp.state = 'done'
                AND spt.code = 'internal'
                AND sp.date_done >= p.it_start_ts
                AND sp.date_done <  p.it_end_ts_excl
                AND sp.location_dest_id IN (SELECT id FROM carsale_tree)
                AND sp.location_id      IN (SELECT id FROM fg_tree)
                GROUP BY sml.product_id
            ),
            transfer_totals AS (
                SELECT product_id, SUM(qty) AS total_qty
                FROM transfer_lines
                GROUP BY product_id
            ),
            trip_max AS (
                SELECT COALESCE(MAX(trip_no), 0) AS max_trip
                FROM trip_days
            )
            SELECT
                tl.product_id,
                tl.trip_no,
                tl.qty,
                tt.total_qty,
                tm.max_trip,
                lbp.latest_trip_day
            FROM transfer_lines tl
            JOIN transfer_totals tt ON tt.product_id = tl.product_id
            CROSS JOIN trip_max tm
            LEFT JOIN latest_by_product lbp ON lbp.product_id = tl.product_id
            ORDER BY tl.product_id, tl.trip_no
            """

        self.env.cr.execute(sql, {
            "carsale_loc_id": carsale_loc_id,
            "it_start_ts": it_start_ts,
            "it_end_ts_excl": it_end_ts_excl,
            "fg_ids": fg_ids or [],
            "tz": self.env.user.tz or "UTC",
        })
        rows = self._fetchall_dict()

        trip_qty_map = {}
        transfer_total_map = {}
        product_ids = set()
        max_trip = 0
        latest_trip_day_map = {}

        for r in rows:
            pid = r["product_id"]
            tno = r["trip_no"]
            qty = float(r["qty"] or 0.0)
            trip_qty_map[(pid, tno)] = qty
            transfer_total_map[pid] = float(r["total_qty"] or 0.0)
            product_ids.add(pid)
            max_trip = max(max_trip, int(r["max_trip"] or 0))
            if r.get("latest_trip_day"):
                latest_trip_day_map[pid] = r["latest_trip_day"]

        trip_nos = list(range(1, max_trip + 1)) if max_trip else []
        return {
            "trip_nos": trip_nos,
            "product_ids": list(product_ids),
            "trip_qty_map": trip_qty_map,
            "transfer_total_map": transfer_total_map,
            "latest_trip_day_map": latest_trip_day_map,
        }

    
    def _sql_trip_matrix_all_carsale(self, it_start_ts, it_end_ts_excl, fg_ids, carsale_root_ids):
        """
        Trip matrix รวมทุก CARSALE (Phase 1)
        - internal picking done
        - picking_type internal
        - location_id อยู่ใต้ FG
        - location_dest_id อยู่ใต้ CARSALE roots (ถ้าไม่พบ root จะคืนค่าว่างเพื่อกันข้อมูลหลุด)
        """
        if not it_start_ts or not it_end_ts_excl:
            return {"trip_nos": [], "product_ids": [], "trip_qty_map": {}, "transfer_total_map": {}}

        if not carsale_root_ids:
            # ไม่รู้ว่า CARSALE อยู่ตรงไหน -> ไม่ดึงเพื่อกันข้อมูลหลุดไป location อื่น
            return {"trip_nos": [], "product_ids": [], "trip_qty_map": {}, "transfer_total_map": {}}

        sql = """
        WITH
        params AS (
            SELECT
                %(it_start_ts)s::timestamp AS it_start_ts,
                %(it_end_ts_excl)s::timestamp AS it_end_ts_excl,
                %(fg_ids)s::int[] AS fg_ids,
                %(carsale_root_ids)s::int[] AS carsale_root_ids
        ),
        carsale_tree AS (
            SELECT sl.id
            FROM stock_location sl, params p
            WHERE
                sl.id = ANY(p.carsale_root_ids)
                OR EXISTS (
                    SELECT 1
                    FROM unnest(p.carsale_root_ids) rid
                    WHERE sl.parent_path LIKE ('%%/' || rid || '/%%')
                )
        ),
        fg_tree AS (
            SELECT sl.id
            FROM stock_location sl, params p
            WHERE
                (p.fg_ids IS NOT NULL AND array_length(p.fg_ids, 1) > 0)
                AND (
                    sl.id = ANY(p.fg_ids)
                    OR EXISTS (
                        SELECT 1
                        FROM unnest(p.fg_ids) fg_id
                        WHERE sl.parent_path LIKE ('%%/' || fg_id || '/%%')
                    )
                )
        ),
        internal_pickings AS (
            SELECT
                sp.id,
                (sp.date_done AT TIME ZONE 'UTC' AT TIME ZONE %(tz)s)::date AS trip_day
            FROM stock_picking sp
            JOIN stock_picking_type spt ON spt.id = sp.picking_type_id
            JOIN params p ON TRUE
            WHERE sp.state = 'done'
            AND spt.code = 'internal'
            AND sp.date_done >= p.it_start_ts
            AND sp.date_done <  p.it_end_ts_excl
            AND sp.location_dest_id IN (SELECT id FROM carsale_tree)
            AND sp.location_id      IN (SELECT id FROM fg_tree)
        ),
        trip_days AS (
            SELECT
                trip_day,
                DENSE_RANK() OVER (ORDER BY trip_day) AS trip_no
            FROM (SELECT DISTINCT trip_day FROM internal_pickings) d
        ),
        pickings_with_trip AS (
            SELECT ip.id, td.trip_no
            FROM internal_pickings ip
            JOIN trip_days td ON td.trip_day = ip.trip_day
        ),
        transfer_lines AS (
            SELECT
                sml.product_id,
                pwt.trip_no,
                SUM(sml.quantity) AS qty
            FROM stock_move_line sml
            JOIN pickings_with_trip pwt ON pwt.id = sml.picking_id
            WHERE sml.state = 'done'
            GROUP BY sml.product_id, pwt.trip_no
        ),
        latest_by_product AS (
            SELECT
                sml.product_id,
                MAX((sp.date_done AT TIME ZONE 'UTC' AT TIME ZONE %(tz)s)::date) AS latest_trip_day
            FROM stock_move_line sml
            JOIN stock_picking sp ON sp.id = sml.picking_id
            JOIN stock_move sm ON sm.id = sml.move_id
            JOIN stock_picking_type spt ON spt.id = sp.picking_type_id
            JOIN params p ON TRUE
            WHERE sml.state = 'done'
            AND sp.state = 'done'
            AND spt.code = 'internal'
            AND sp.date_done >= p.it_start_ts
            AND sp.date_done <  p.it_end_ts_excl
            AND sp.location_dest_id IN (SELECT id FROM carsale_tree)
            AND sp.location_id      IN (SELECT id FROM fg_tree)
            GROUP BY sml.product_id
        ),
        transfer_totals AS (
            SELECT product_id, SUM(qty) AS total_qty
            FROM transfer_lines
            GROUP BY product_id
        ),
        trip_max AS (
            SELECT COALESCE(MAX(trip_no), 0) AS max_trip
            FROM trip_days
        )
        SELECT
            tl.product_id,
            tl.trip_no,
            tl.qty,
            tt.total_qty,
            tm.max_trip,
            lbp.latest_trip_day
        FROM transfer_lines tl
        JOIN transfer_totals tt ON tt.product_id = tl.product_id
        CROSS JOIN trip_max tm
        LEFT JOIN latest_by_product lbp ON lbp.product_id = tl.product_id
        ORDER BY tl.product_id, tl.trip_no
        """

        self.env.cr.execute(sql, {
            "it_start_ts": it_start_ts,
            "it_end_ts_excl": it_end_ts_excl,
            "fg_ids": fg_ids or [],
            "carsale_root_ids": carsale_root_ids or [],
            "tz": self.env.user.tz or "UTC",
        })
        rows = self._fetchall_dict()

        trip_qty_map = {}
        transfer_total_map = {}
        product_ids = set()
        max_trip = 0
        latest_trip_day_map = {}

        for r in rows:
            pid = r["product_id"]
            tno = r["trip_no"]
            qty = float(r["qty"] or 0.0)
            trip_qty_map[(pid, tno)] = qty
            transfer_total_map[pid] = float(r["total_qty"] or 0.0)
            product_ids.add(pid)
            max_trip = max(max_trip, int(r["max_trip"] or 0))
            if r.get("latest_trip_day"):
                latest_trip_day_map[pid] = r["latest_trip_day"]

        trip_nos = list(range(1, max_trip + 1)) if max_trip else []
        return {
            "trip_nos": trip_nos,
            "product_ids": list(product_ids),
            "trip_qty_map": trip_qty_map,
            "transfer_total_map": transfer_total_map,
            "latest_trip_day_map": latest_trip_day_map,
        }

    # ------------------------------------------------------------
    # SQL: OUT (carsale -> customer) + Invoice (posted) for correct accounting
    # ------------------------------------------------------------
    
    def _sql_sale_invoice_summary_all_carsale_by_salesperson(
        self,
        carsale_root_ids,
        salesperson_user_id,
        start_ts,
        end_ts_excl,
        start_date=None,
        end_date_excl=None,
    ):
        rel_candidates = ["account_move_line_sale_line_rel", "sale_order_line_invoice_rel"]
        last_error = None
        for rel_table in rel_candidates:
            try:
                # [FIX] เพิ่ม savepoint
                with self.env.cr.savepoint():
                    return self._sql_sale_invoice_summary_all_carsale_by_salesperson_with_rel(
                        carsale_root_ids=carsale_root_ids,
                        salesperson_user_id=salesperson_user_id,
                        start_ts=start_ts,
                        end_ts_excl=end_ts_excl,
                        start_date=start_date,
                        end_date_excl=end_date_excl,
                        rel_table=rel_table,
                    )
            except Exception as e:
                last_error = e

        return {
            "product_ids": [],
            "sold_qty_map": {},
            "inv_qty_map": {},
            "inv_amount_map": {},
            "unit_price_map": {},
            "_warning": f"Invoice relation table not found. Last error: {last_error}",
        }


    def _sql_sale_invoice_summary_all_carsale_by_salesperson_with_rel(
        self, carsale_root_ids, salesperson_user_id, start_ts, end_ts_excl,
        start_date, end_date_excl, rel_table
    ):
        if rel_table == "sale_order_line_invoice_rel":
            rel_aml_col = "invoice_line_id"
            rel_sol_col = "order_line_id"
        elif rel_table == "account_move_line_sale_line_rel":
            rel_aml_col = "account_move_line_id"
            rel_sol_col = "sale_order_line_id"
        else:
            raise ValueError(f"Unsupported relation table: {rel_table}")

        # กันข้อมูลหลุด: ถ้าไม่เจอ carsale root ให้คืนว่าง
        if not carsale_root_ids:
            return {"product_ids": [], "sold_qty_map": {}, "inv_qty_map": {}, "inv_amount_map": {}, "unit_price_map": {}}

        sql = f"""
        WITH
        params AS (
            SELECT
                %(start_ts)s::timestamp AS start_ts,
                %(end_ts_excl)s::timestamp AS end_ts_excl,
                %(start_date)s::date AS start_date,
                %(end_date_excl)s::date AS end_date_excl,
                %(carsale_root_ids)s::int[] AS carsale_root_ids,
                %(salesperson_user_id)s::int AS salesperson_user_id
        ),
        carsale_tree AS (
            SELECT sl.id
            FROM stock_location sl, params p
            WHERE
                sl.id = ANY(p.carsale_root_ids)
                OR EXISTS (
                    SELECT 1
                    FROM unnest(p.carsale_root_ids) rid
                    WHERE sl.parent_path LIKE ('%%/' || rid || '/%%')
                )
        ),
        out_pickings AS (
            SELECT sp.id
            FROM stock_picking sp
            JOIN stock_picking_type spt ON spt.id = sp.picking_type_id
            JOIN params p ON TRUE
            WHERE sp.state = 'done'
            AND spt.code = 'outgoing'
            AND sp.date_done >= p.start_ts
            AND sp.date_done <  p.end_ts_excl
        ),
        out_move_lines AS (
            SELECT
                sml.product_id,
                sml.quantity AS qty_done,
                sm.sale_line_id
            FROM stock_move_line sml
            JOIN stock_move sm ON sm.id = sml.move_id
            WHERE sml.state = 'done'
            AND sml.picking_id IN (SELECT id FROM out_pickings)
            AND sm.sale_line_id IS NOT NULL
            AND sml.location_id IN (SELECT id FROM carsale_tree)
            AND sml.quantity != 0
        ),
        so_lines AS (
            SELECT
                oml.product_id,
                oml.qty_done,
                sol.id AS sol_id,
                so.user_id AS salesperson_user_id
            FROM out_move_lines oml
            JOIN sale_order_line sol ON sol.id = oml.sale_line_id
            JOIN sale_order so ON so.id = sol.order_id
        ),
        filtered_sol AS (
            SELECT *
            FROM so_lines
            WHERE salesperson_user_id = (SELECT salesperson_user_id FROM params)
        ),
        sold_by_product AS (
            SELECT product_id, SUM(qty_done) AS sold_qty
            FROM filtered_sol
            GROUP BY product_id
        ),
        sale_lines AS (
            SELECT DISTINCT sol_id
            FROM filtered_sol
        ),
        invoice_lines AS (
            SELECT
                aml.id AS aml_id,
                aml.product_id,
                aml.quantity,
                aml.price_unit,
                aml.price_subtotal,
                am.move_type,
                am.invoice_date
            FROM account_move_line aml
            JOIN account_move am ON am.id = aml.move_id
            JOIN {rel_table} rel ON rel.{rel_aml_col} = aml.id
            JOIN sale_lines sl ON sl.sol_id = rel.{rel_sol_col}
            JOIN params p ON TRUE
            WHERE am.state = 'posted'
            AND am.move_type IN ('out_invoice', 'out_refund')
            AND am.invoice_date >= p.start_date
            AND am.invoice_date <  p.end_date_excl
            AND aml.display_type = 'product'

        ),
        inv_by_product AS (
            SELECT
                product_id,
                SUM(CASE WHEN move_type='out_refund' THEN -COALESCE(quantity,0) ELSE COALESCE(quantity,0) END) AS inv_qty,
                SUM(CASE WHEN move_type='out_refund' THEN -COALESCE(price_subtotal,0) ELSE COALESCE(price_subtotal,0) END) AS inv_amount,
                CASE
                    WHEN SUM(CASE WHEN move_type='out_refund' THEN -COALESCE(quantity,0) ELSE COALESCE(quantity,0) END) != 0
                    THEN
                        SUM(CASE WHEN move_type='out_refund'
                                THEN -(COALESCE(price_unit,0) * COALESCE(quantity,0))
                                ELSE  (COALESCE(price_unit,0) * COALESCE(quantity,0))
                            END)
                        / NULLIF(
                            SUM(CASE WHEN move_type='out_refund' THEN -COALESCE(quantity,0) ELSE COALESCE(quantity,0) END)
                        ,0)
                    ELSE 0
                END AS avg_price_unit
            FROM invoice_lines
            GROUP BY product_id
        )
        SELECT
            COALESCE(s.product_id, i.product_id) AS product_id,
            COALESCE(s.sold_qty, 0) AS sold_qty,
            COALESCE(i.inv_qty, 0) AS inv_qty,
            COALESCE(i.inv_amount, 0) AS inv_amount,
            COALESCE(i.avg_price_unit, 0) AS avg_unit_price
        FROM sold_by_product s
        FULL OUTER JOIN inv_by_product i ON i.product_id = s.product_id
        ORDER BY product_id
        """

        self.env.cr.execute(sql, {
            "carsale_root_ids": carsale_root_ids or [],
            "salesperson_user_id": salesperson_user_id or 0,
            "start_ts": start_ts,
            "end_ts_excl": end_ts_excl,
            "start_date": start_date or start_ts.date(),
            "end_date_excl": end_date_excl or end_ts_excl.date(),
        })
        rows = self._fetchall_dict()

        product_ids, sold_qty_map, inv_qty_map, inv_amount_map, unit_price_map = set(), {}, {}, {}, {}
        for r in rows:
            pid = r.get("product_id")
            if not pid:
                continue
            product_ids.add(pid)
            sold_qty_map[pid] = float(r.get("sold_qty") or 0.0)
            inv_qty_map[pid] = float(r.get("inv_qty") or 0.0)
            inv_amount_map[pid] = float(r.get("inv_amount") or 0.0)
            unit_price_map[pid] = float(r.get("avg_unit_price") or 0.0)

        return {
            "product_ids": list(product_ids),
            "sold_qty_map": sold_qty_map,
            "inv_qty_map": inv_qty_map,
            "inv_amount_map": inv_amount_map,
            "unit_price_map": unit_price_map,
            "_rel_table_used": rel_table,
        }

    def _sql_receipts_summary_all_carsale_by_salesperson(
        self,
        carsale_root_ids,
        salesperson_user_id,
        start_ts,
        end_ts_excl,
        start_date=None,
        end_date_excl=None,
    ):
        if not carsale_root_ids or not salesperson_user_id:
            return {
                "gross_sales": 0.0, "discount_total": 0.0, "net_sales": 0.0,
                "cash_received": 0.0, "transfer_received": 0.0, "cheque_received": 0.0,
                "received_total": 0.0, "ar_unpaid": 0.0,
            }

        rel_candidates = ["account_move_line_sale_line_rel", "sale_order_line_invoice_rel"]
        last_error = None
        for rel_table in rel_candidates:
            try:
                # [FIX] เพิ่ม savepoint
                with self.env.cr.savepoint():
                    return self._sql_receipts_summary_all_carsale_by_salesperson_with_rel(
                        carsale_root_ids=carsale_root_ids,
                        salesperson_user_id=salesperson_user_id,
                        start_ts=start_ts,
                        end_ts_excl=end_ts_excl,
                        start_date=start_date,
                        end_date_excl=end_date_excl,
                        rel_table=rel_table,
                    )
            except Exception as e:
                last_error = e
                _logger.exception("Receipts details failed with rel_table=%s", rel_table)

        return {
            "gross_sales": 0.0, "discount_total": 0.0, "net_sales": 0.0,
            "cash_received": 0.0, "transfer_received": 0.0, "cheque_received": 0.0,
            "received_total": 0.0, "ar_unpaid": 0.0,
            "_error": str(last_error) if last_error else None,
        }


    def _sql_receipts_summary_all_carsale_by_salesperson_with_rel(
        self,
        carsale_root_ids,
        salesperson_user_id,
        start_ts,
        end_ts_excl,
        start_date,
        end_date_excl,
        rel_table,
    ):
        if rel_table == "sale_order_line_invoice_rel":
            rel_aml_col = "invoice_line_id"
            rel_sol_col = "order_line_id"
        elif rel_table == "account_move_line_sale_line_rel":
            rel_aml_col = "account_move_line_id"
            rel_sol_col = "sale_order_line_id"
        else:
            raise ValueError(f"Unsupported relation table: {rel_table}")

        sql = f"""
        WITH
        params AS (
            SELECT
                %(start_ts)s::timestamp AS start_ts,
                %(end_ts_excl)s::timestamp AS end_ts_excl,
                %(start_date)s::date AS start_date,
                %(end_date_excl)s::date AS end_date_excl,
                %(carsale_root_ids)s::int[] AS carsale_root_ids,
                %(salesperson_user_id)s::int AS salesperson_user_id
        ),
        carsale_tree AS (
            SELECT sl.id
            FROM stock_location sl, params p
            WHERE sl.id = ANY(p.carsale_root_ids)
            OR EXISTS (
                SELECT 1
                FROM unnest(p.carsale_root_ids) rid
                WHERE sl.parent_path LIKE ('%%/' || rid || '/%%')
            )
        ),
        out_pickings AS (
            SELECT sp.id
            FROM stock_picking sp
            JOIN stock_picking_type spt ON spt.id = sp.picking_type_id
            JOIN params p ON TRUE
            WHERE sp.state = 'done'
            AND spt.code = 'outgoing'
            AND sp.date_done >= p.start_ts
            AND sp.date_done <  p.end_ts_excl
        ),
        out_move_lines AS (
            SELECT
                sml.product_id,
                sml.quantity AS qty_done,
                sm.sale_line_id
            FROM stock_move_line sml
            JOIN stock_move sm ON sm.id = sml.move_id
            WHERE sml.state = 'done'
            AND sml.picking_id IN (SELECT id FROM out_pickings)
            AND sm.sale_line_id IS NOT NULL
            AND sml.location_id IN (SELECT id FROM carsale_tree)
            AND sml.quantity != 0
        ),
        so_lines AS (
            SELECT DISTINCT sol.id AS sol_id
            FROM out_move_lines oml
            JOIN sale_order_line sol ON sol.id = oml.sale_line_id
            JOIN sale_order so ON so.id = sol.order_id
            JOIN params p ON TRUE
            WHERE so.user_id = p.salesperson_user_id
        ),
        invoice_lines AS (
            SELECT
                aml.id AS aml_id,
                aml.move_id,
                aml.quantity,
                aml.price_unit,
                aml.price_subtotal,
                am.move_type,
                am.invoice_date
            FROM account_move_line aml
            JOIN account_move am ON am.id = aml.move_id
            JOIN {rel_table} rel ON rel.{rel_aml_col} = aml.id
            JOIN so_lines sl ON sl.sol_id = rel.{rel_sol_col}
            JOIN params p ON TRUE
            WHERE am.state = 'posted'
            AND am.move_type IN ('out_invoice','out_refund')
            AND am.invoice_date >= p.start_date
            AND am.invoice_date <  p.end_date_excl
            AND aml.display_type = 'product'

        ),
        invoice_moves AS (
            SELECT DISTINCT move_id AS invoice_id
            FROM invoice_lines
        ),
        sales_sum AS (
            SELECT
                SUM(
                    CASE WHEN move_type = 'out_refund'
                        THEN -(COALESCE(quantity,0) * COALESCE(price_unit,0))
                        ELSE  (COALESCE(quantity,0) * COALESCE(price_unit,0))
                    END
                ) AS gross_sales,
                SUM(
                    CASE WHEN move_type = 'out_refund'
                        THEN -COALESCE(price_subtotal,0)
                        ELSE  COALESCE(price_subtotal,0)
                    END
                ) AS net_sales
            FROM invoice_lines
        ),
        inv_ar_lines AS (
            SELECT aml.id AS inv_ar_aml_id
            FROM account_move_line aml
            JOIN account_account aa ON aa.id = aml.account_id
            WHERE aa.account_type = 'asset_receivable'
            AND aml.display_type = 'payment_term'
            AND aml.move_id IN (SELECT invoice_id FROM invoice_moves)
        ),
        rec AS (
            SELECT
                pr.amount,
                CASE
                    WHEN pr.debit_move_id IN (SELECT inv_ar_aml_id FROM inv_ar_lines) THEN pr.debit_move_id
                    ELSE pr.credit_move_id
                END AS inv_ar_aml_id,
                CASE
                    WHEN pr.debit_move_id IN (SELECT inv_ar_aml_id FROM inv_ar_lines) THEN pr.credit_move_id
                    ELSE pr.debit_move_id
                END AS pay_ar_aml_id
            FROM account_partial_reconcile pr
            WHERE pr.debit_move_id IN (SELECT inv_ar_aml_id FROM inv_ar_lines)
            OR pr.credit_move_id IN (SELECT inv_ar_aml_id FROM inv_ar_lines)
        ),
        pay_moves AS (
            SELECT DISTINCT aml.move_id AS payment_move_id
            FROM account_move_line aml
            JOIN rec r ON r.pay_ar_aml_id = aml.id
        ),
        payments AS (
            SELECT
                ap.id,
                ap.date AS payment_date,
                ap.amount AS payment_amount,
                ap.journal_id,
                ap.payment_method_line_id,
                ap.move_id
            FROM account_payment ap
            JOIN pay_moves pm ON pm.payment_move_id = ap.move_id
            JOIN params p ON TRUE
            WHERE ap.state IN ('posted','reconciled','paid')
            AND ap.date >= p.start_date
            AND ap.date <  p.end_date_excl
        ),
        pay_cat AS (
            SELECT
                ap.payment_amount,
                j.type AS journal_type,
                COALESCE(pml.name, '') AS method_name
            FROM payments ap
            JOIN account_journal j ON j.id = ap.journal_id
            LEFT JOIN account_payment_method_line pml ON pml.id = ap.payment_method_line_id
        ),
        pay_sum AS (
            SELECT
                COALESCE(SUM(CASE WHEN journal_type = 'cash' THEN payment_amount ELSE 0 END), 0) AS cash_received,
                COALESCE(SUM(CASE WHEN journal_type = 'bank'
                            AND NOT (method_name ILIKE '%%cheque%%' OR method_name ILIKE '%%check%%' OR method_name ILIKE '%%เช็ค%%')
                            THEN payment_amount ELSE 0 END), 0) AS transfer_received,
                COALESCE(SUM(CASE WHEN (method_name ILIKE '%%cheque%%' OR method_name ILIKE '%%check%%' OR method_name ILIKE '%%เช็ค%%')
                            THEN payment_amount ELSE 0 END), 0) AS cheque_received
            FROM pay_cat
        ), 
        inv_amounts AS (
            SELECT
                SUM(CASE WHEN am.move_type='out_refund' THEN -COALESCE(am.amount_tax,0)   ELSE COALESCE(am.amount_tax,0) END)   AS vat_amount,
                SUM(CASE WHEN am.move_type='out_refund' THEN -COALESCE(am.amount_total,0) ELSE COALESCE(am.amount_total,0) END) AS total_amount
            FROM account_move am
            WHERE am.id IN (SELECT invoice_id FROM invoice_moves)
        ),
        refund_amounts AS (
            SELECT
                COALESCE(SUM(
                    CASE
                        WHEN am.move_type = 'out_refund' THEN -COALESCE(am.amount_total_signed, 0)
                        ELSE 0
                    END
                ), 0) AS refund_total_amount
            FROM account_move am
            WHERE am.id IN (SELECT invoice_id FROM invoice_moves)
        )
        SELECT
            COALESCE(s.gross_sales, 0) AS gross_sales,
            COALESCE(s.net_sales, 0) AS net_sales,
            (COALESCE(s.gross_sales,0) - COALESCE(s.net_sales,0)) AS discount_total,
            p.cash_received,
            p.transfer_received,
            p.cheque_received,
            COALESCE(a.vat_amount,0)   AS vat_amount,
            COALESCE(a.total_amount,0) AS total_amount,
            COALESCE(r.refund_total_amount,0) AS return_total_amount
        FROM sales_sum s
        CROSS JOIN pay_sum p
        CROSS JOIN inv_amounts a
        CROSS JOIN refund_amounts r;
        """

        self.env.cr.execute(sql, {
            "carsale_root_ids": carsale_root_ids or [],
            "salesperson_user_id": salesperson_user_id,
            "start_ts": start_ts,
            "end_ts_excl": end_ts_excl,
            "start_date": start_date or start_ts.date(),
            "end_date_excl": end_date_excl or end_ts_excl.date(),
        })
        row = self._fetchall_dict()
        row = row[0] if row else {}

        vat = float(row.get("vat_amount") or 0.0)
        total = float(row.get("total_amount") or 0.0)

        gross = float(row.get("gross_sales") or 0.0)
        net = float(row.get("net_sales") or 0.0)
        discount = float(row.get("discount_total") or 0.0)

        cash = float(row.get("cash_received") or 0.0)
        transfer = float(row.get("transfer_received") or 0.0)
        cheque = float(row.get("cheque_received") or 0.0)
        received_total = cash + transfer + cheque

        vat_amount = float(row.get("vat_amount") or 0.0)
        total_amount = float(row.get("total_amount") or (net + vat_amount))
        return_total_amount = float(row.get("return_total_amount") or 0.0)

        return {
            "gross_sales": gross,
            "discount_total": discount,
            "net_sales": net,

            "cash_received": cash,
            "transfer_received": transfer,
            "cheque_received": cheque,
            "received_total": received_total,

            "vat_amount": vat_amount,
            "total_amount": total_amount,
            "ar_unpaid": (total_amount - return_total_amount) - received_total,
            "return_total_amount": return_total_amount,
            "return_amount": return_total_amount,

            "_rel_table_used": rel_table,
        }
    # ------------------------------------------------------------
    # SQL: Receipts Detail Lists (By Salesperson / All Carsale)
    # ------------------------------------------------------------
    def _sql_receipts_details_all_carsale_by_salesperson(
        self,
        carsale_root_ids,
        salesperson_user_id,
        start_ts,
        end_ts_excl,
        start_date=None,
        end_date_excl=None,
    ):
        rel_candidates = ["account_move_line_sale_line_rel", "sale_order_line_invoice_rel"]
        last_error = None
        for rel_table in rel_candidates:
            try:
                # [FIX] เพิ่ม savepoint
                with self.env.cr.savepoint():
                    return self._sql_receipts_details_all_carsale_by_salesperson_with_rel(
                        carsale_root_ids=carsale_root_ids,
                        salesperson_user_id=salesperson_user_id,
                        start_ts=start_ts,
                        end_ts_excl=end_ts_excl,
                        start_date=start_date,
                        end_date_excl=end_date_excl,
                        rel_table=rel_table,
                    )
            except Exception as e:
                last_error = e

        return [], []

    def _sql_receipts_details_all_carsale_by_salesperson_with_rel(
        self,
        carsale_root_ids,
        salesperson_user_id,
        start_ts,
        end_ts_excl,
        start_date,
        end_date_excl,
        rel_table,
    ):
        if rel_table == "sale_order_line_invoice_rel":
            rel_aml_col = "invoice_line_id"
            rel_sol_col = "order_line_id"
        elif rel_table == "account_move_line_sale_line_rel":
            rel_aml_col = "account_move_line_id"
            rel_sol_col = "sale_order_line_id"
        else:
            raise ValueError(f"Unsupported relation table: {rel_table}")

        sql = f"""
        WITH
        params AS (
            SELECT
                %(start_ts)s::timestamp AS start_ts,
                %(end_ts_excl)s::timestamp AS end_ts_excl,
                %(start_date)s::date AS start_date,
                %(end_date_excl)s::date AS end_date_excl,
                %(carsale_root_ids)s::int[] AS carsale_root_ids,
                %(salesperson_user_id)s::int AS salesperson_user_id
        ),
        carsale_tree AS (
            SELECT sl.id
            FROM stock_location sl, params p
            WHERE sl.id = ANY(p.carsale_root_ids)
            OR EXISTS (
                SELECT 1
                FROM unnest(p.carsale_root_ids) rid
                WHERE sl.parent_path LIKE ('%%/' || rid || '/%%')
            )
        ),
        out_pickings AS (
            SELECT sp.id
            FROM stock_picking sp
            JOIN stock_picking_type spt ON spt.id = sp.picking_type_id
            JOIN params p ON TRUE
            WHERE sp.state = 'done'
            AND spt.code = 'outgoing'
            AND sp.date_done >= p.start_ts
            AND sp.date_done <  p.end_ts_excl
        ),
        out_move_lines AS (
            SELECT
                sml.product_id,
                sml.quantity AS qty_done,
                sm.sale_line_id
            FROM stock_move_line sml
            JOIN stock_move sm ON sm.id = sml.move_id
            WHERE sml.state = 'done'
            AND sml.picking_id IN (SELECT id FROM out_pickings)
            AND sm.sale_line_id IS NOT NULL
            AND sml.location_id IN (SELECT id FROM carsale_tree)
            AND sml.quantity != 0
        ),
        so_lines AS (
            SELECT DISTINCT sol.id AS sol_id
            FROM out_move_lines oml
            JOIN sale_order_line sol ON sol.id = oml.sale_line_id
            JOIN sale_order so ON so.id = sol.order_id
            JOIN params p ON TRUE
            WHERE so.user_id = p.salesperson_user_id
        ),
        invoice_moves AS (
            SELECT DISTINCT aml.move_id AS invoice_id
            FROM account_move_line aml
            JOIN account_move am ON am.id = aml.move_id
            JOIN {rel_table} rel ON rel.{rel_aml_col} = aml.id
            JOIN so_lines sl ON sl.sol_id = rel.{rel_sol_col}
            JOIN params p ON TRUE
            WHERE am.state = 'posted'
            AND am.move_type IN ('out_invoice','out_refund')
            AND am.invoice_date >= p.start_date
            AND am.invoice_date <  p.end_date_excl
            AND aml.display_type = 'product'

        ),
        inv_ar_lines AS (
            SELECT aml.id AS inv_ar_aml_id
            FROM account_move_line aml
            JOIN account_account aa ON aa.id = aml.account_id
            WHERE aa.account_type = 'asset_receivable'
            AND aml.display_type = 'payment_term'
            AND aml.move_id IN (SELECT invoice_id FROM invoice_moves)
        ),
        rec AS (
            SELECT
                pr.amount,
                CASE
                    WHEN pr.debit_move_id IN (SELECT inv_ar_aml_id FROM inv_ar_lines) THEN pr.debit_move_id
                    ELSE pr.credit_move_id
                END AS inv_ar_aml_id,
                CASE
                    WHEN pr.debit_move_id IN (SELECT inv_ar_aml_id FROM inv_ar_lines) THEN pr.credit_move_id
                    ELSE pr.debit_move_id
                END AS pay_ar_aml_id
            FROM account_partial_reconcile pr
            WHERE pr.debit_move_id IN (SELECT inv_ar_aml_id FROM inv_ar_lines)
            OR pr.credit_move_id IN (SELECT inv_ar_aml_id FROM inv_ar_lines)
        ),
        rec_moves AS (
            SELECT DISTINCT
                dml.move_id AS move_id
            FROM account_partial_reconcile pr
            JOIN account_move_line dml ON dml.id = pr.debit_move_id
            WHERE pr.debit_move_id IN (SELECT inv_ar_aml_id FROM inv_ar_lines)
            OR pr.credit_move_id IN (SELECT inv_ar_aml_id FROM inv_ar_lines)

            UNION

            SELECT DISTINCT
                cml.move_id AS move_id
            FROM account_partial_reconcile pr
            JOIN account_move_line cml ON cml.id = pr.credit_move_id
            WHERE pr.debit_move_id IN (SELECT inv_ar_aml_id FROM inv_ar_lines)
            OR pr.credit_move_id IN (SELECT inv_ar_aml_id FROM inv_ar_lines)
        ),
        pay_moves AS (
            SELECT rm.move_id
            FROM rec_moves rm
            WHERE rm.move_id NOT IN (SELECT invoice_id FROM invoice_moves)
        ),
        payments AS (
            SELECT
                ap.id,
                ap.date AS payment_date,
                ap.amount AS payment_amount,
                ap.partner_id,
                ap.journal_id,
                ap.payment_method_line_id,
                ap.move_id,
                am.ref AS ref,

                string_agg(DISTINCT cio.name, ', ') AS cheque_number,
                MAX(cio.cheque_date)               AS cheque_date_on_cheque,
                MAX(cio.id)                        AS cheque_id

            FROM account_payment ap
            JOIN pay_moves pm ON pm.move_id = ap.move_id   -- ✅ ต้องมี
            JOIN params p ON TRUE

            LEFT JOIN account_payment_cheque_inbound_outbound_rel rel
                ON rel.account_payment_id = ap.id
            LEFT JOIN cheque_inbound_outbound cio
                ON cio.id = rel.cheque_inbound_outbound_id

            JOIN account_move am ON am.id = ap.move_id
                
            WHERE ap.state IN ('posted','reconciled','paid')
            AND ap.date >= p.start_date
            AND ap.date <  p.end_date_excl

            GROUP BY
                ap.id, ap.date, ap.amount,
                ap.partner_id, ap.journal_id,
                ap.payment_method_line_id, ap.move_id,
                am.ref
        ),
        pay_info AS (
            SELECT
                ap.*,
                CASE
                    WHEN pg_typeof(j.name) = 'jsonb'::regtype THEN
                        COALESCE(j.name->>'en_US', j.name->>'th_TH', j.name->>'en_GB', j.name::text)
                    ELSE j.name::text
                END AS journal_name,
                j.type AS journal_type,
                COALESCE(pml.name,'') AS method_name,
                rp.name AS partner_name,
                COALESCE(jb.name, '') AS bank_name,
                COALESCE(jpb.acc_number, '') AS bank_acc_number
            FROM payments ap
            JOIN account_journal j ON j.id = ap.journal_id
            LEFT JOIN account_payment_method_line pml ON pml.id = ap.payment_method_line_id
            LEFT JOIN res_partner rp ON rp.id = ap.partner_id
            LEFT JOIN res_partner_bank jpb ON jpb.id = j.bank_account_id
            LEFT JOIN res_bank jb ON jb.id = jpb.bank_id
        )
        SELECT
            id AS payment_id,
            payment_date,
            partner_name,
            journal_name,
            journal_type,
            method_name,
            ref,
            payment_amount,
            cheque_id,
            cheque_number,
            cheque_date_on_cheque,
            bank_name,
            bank_acc_number
        FROM pay_info
        ORDER BY payment_date, id;
        """

        self.env.cr.execute(sql, {
            "carsale_root_ids": carsale_root_ids or [],
            "salesperson_user_id": salesperson_user_id,
            "start_ts": start_ts,
            "end_ts_excl": end_ts_excl,
            "start_date": start_date or start_ts.date(),
            "end_date_excl": end_date_excl or end_ts_excl.date(),
        })
        rows = self._fetchall_dict()

        bank_transfers, cheques = [], []
        for r in rows:
            method = (r.get("method_name") or "")
            jtype = (r.get("journal_type") or "")
            m = method.lower()

            # ตัดสินว่าเป็นเช็คครั้งเดียว
            is_cheque = bool(r.get("cheque_id")) or (
                r.get("journal_type") == "bank"
                and "cheque" in (r.get("method_name") or "").lower()
            )

            cheque_no_val = ""
            cheque_date_val = None

            # ตั้งค่า cheque fields ตามผล is_cheque
            if is_cheque:
                cheque_no_val = r.get("cheque_number") or ""
                cheque_date_val = r.get("cheque_date_on_cheque") or r.get("payment_date")
                bank_name = r.get("bank_name") or ""
                bank_acc = r.get("bank_acc_number") or ""
            else:
                bank_name = r.get("bank_name") or ""
                bank_acc = r.get("bank_acc_number") or ""

            item = {
                "payment_id": r.get("payment_id"),
                "payment_date": r.get("payment_date"),
                "partner_name": r.get("partner_name") or "",
                "journal_name": r.get("journal_name") or "",
                "bank_name": bank_name,
                "bank_acc_number": bank_acc,
                "method_name": method,
                "ref": r.get("ref") or "",

                # ✅ map ให้ QWeb ใช้ได้
                "amount": float(r.get("payment_amount") or 0.0),

                # ✅ cheque
                "cheque_number": r.get("cheque_number") or "",
                "cheque_date": r.get("cheque_date_on_cheque"),
            }

            if is_cheque:
                cheques.append(item)
            elif jtype == "bank":
                bank_transfers.append(item)

        return bank_transfers, cheques
