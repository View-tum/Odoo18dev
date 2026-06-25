# -*- coding: utf-8 -*-
from odoo import models
from datetime import datetime, timedelta, time
import pytz
import logging
import re

_logger = logging.getLogger(__name__)


class TripClosingQueries(models.AbstractModel):
    _name = "trip.closing.queries"
    _description = "Trip Closing SQL Queries"

    # Relation table candidates
    REL_CANDIDATES = [
        "account_move_line_sale_line_rel",
        "sale_order_line_invoice_rel",
    ]

    # ============================================================
    # Core Helpers
    # ============================================================
    
    def _fetchall_dict(self):
        """Fetch all rows as dict list."""
        cr = self.env.cr
        rows = cr.fetchall()
        cols = [c.name for c in cr.description] if cr.description else []
        return [dict(zip(cols, row)) for row in rows]

    def _get_tz(self):
        """Get user timezone."""
        return self.env.user.tz or "UTC"

    def _to_utc_start(self, date_obj):
        """Convert date to UTC datetime at start of day."""
        tz = pytz.timezone(self._get_tz())
        dt_local = tz.localize(datetime.combine(date_obj, time.min))
        return dt_local.astimezone(pytz.utc)

    def _next_day(self, date_obj):
        """Get next day (for exclusive end)."""
        return date_obj + timedelta(days=1)

    def _get_date_range(self, wizard):
        """Get UTC date range from wizard (exclusive end)."""
        if not getattr(wizard, "date_start", None) or not getattr(wizard, "date_end", None):
            raise ValueError("wizard.date_start and wizard.date_end must be set")
        start = self._to_utc_start(wizard.date_start)
        end_excl = self._to_utc_start(self._next_day(wizard.date_end))
        return start, end_excl

    def get_period_label(self, wizard):
        """Format period label."""
        ds = getattr(wizard, "date_start", None)
        de = getattr(wizard, "date_end", None)
        if ds and de:
            return f"{ds} - {de}"
        return ""

    # ============================================================
    # Location Helpers
    # ============================================================
    
    def _get_fg_locs(self):
        """Get FG locations."""
        names = ["GMP/Stock/FG", "GMP/SC01/FG"]
        return self.env["stock.location"].search([("complete_name", "in", names)])

    def _get_carsale_locs(self):
        """Get CARSALE locations."""
        return self.env["stock.location"].search([
            ("usage", "=", "internal"),
            ("complete_name", "ilike", "CARSALE"),
        ])

    # ============================================================
    # Relation Table Helpers
    # ============================================================
    
    def _get_rel_cols(self, rel_table):
        """Map relation table to column names."""
        if rel_table == "sale_order_line_invoice_rel":
            return "invoice_line_id", "order_line_id"
        elif rel_table == "account_move_line_sale_line_rel":
            return "account_move_line_id", "sale_order_line_id"
        else:
            raise ValueError(f"Unsupported relation table: {rel_table}")

    def _try_with_rel(self, func, *args, **kwargs):
        """
        Execute func with relation table fallback.
        Tries REL_CANDIDATES; returns first success or raises last exception.
        """
        last_exc = None
        for rel in self.REL_CANDIDATES:
            try:
                with self.env.cr.savepoint():
                    return func(*args, rel_table=rel, **kwargs)
            except Exception as e:
                last_exc = e
                _logger.debug("rel-table %s failed, trying next: %s", rel, e)
        raise last_exc

    # ============================================================
    # Summary Helpers
    # ============================================================
    
    def _build_summary(self, totals):
        """Build page summary from totals."""
        gross = float(totals.get("gross_sales") or 0.0)
        discount = float(totals.get("discount_total") or 0.0)
        untaxed = float(totals.get("net_sales") or 0.0)
        vat = float(totals.get("vat_amount") or 0.0)
        total = float(totals.get("total_amount") or (untaxed + vat))
        return_total = float(
            totals.get("return_total_amount")
            or totals.get("return_amount")
            or 0.0
        )
        net_after_return = total - return_total
        return {
            "gross_sales": gross,
            "discount_amount": discount,
            "untaxed_amount": untaxed,
            "vat_amount": vat,
            "total_amount": total,
            "return_amount": return_total,
            "net_sales": net_after_return,
        }

    def _strip_product_code(self, name):
        """Remove [CODE] prefix from product name."""
        return re.sub(r'^\[[^\]]*\]\s*', '', name or '').strip()

    # ============================================================
    # Main Builders
    # ============================================================
    
    def build_driver_data(self, wizard):
        """Build driver report data."""
        if not getattr(wizard, "date_start", None) or not getattr(wizard, "date_end", None):
            return {
                "vehicle_name": wizard.location_id.display_name if wizard.location_id else "ALL CARSALE",
                "trip_numbers": [],
                "date_start": wizard.date_start,
                "date_end": wizard.date_end,
                "lines": [],
                "totals": {},
            }

        if wizard.location_id:
            carsale_ids = [wizard.location_id.id]
            vehicle_name = wizard.location_id.display_name
        else:
            carsale_ids = self._get_carsale_locs().ids or []
            vehicle_name = "ALL CARSALE"

        return self._build_report(
            wizard=wizard,
            carsale_ids=carsale_ids,
            vehicle_name=vehicle_name,
        )

    def build_vehicle_data(self, wizard, carsale_loc):
        """Build vehicle report data."""
        if not getattr(wizard, "date_start", None) or not getattr(wizard, "date_end", None):
            return {
                "carsale_location_name": carsale_loc.display_name,
                "date_start": wizard.date_start,
                "date_end": wizard.date_end,
                "vehicle_name": carsale_loc.display_name,
                "trip_nos": [],
                "lines": [],
                "totals": {},
                "bank_transfers": [],
                "cheques": [],
            }

        return self._build_report(
            wizard=wizard,
            carsale_ids=[carsale_loc.id],
            vehicle_name=carsale_loc.display_name,
        )

    # ============================================================
    # Core Report Builder
    # ============================================================
    
    def _build_report(self, wizard, carsale_ids, vehicle_name):
        """Build complete report data."""
        ds, de = wizard.date_start, wizard.date_end
        start_ts, end_ts_excl = self._get_date_range(wizard)
        fg_ids = self._get_fg_locs().ids or []

        # Monthly window for trips
        month_start = ds.replace(day=1)
        next_month = (month_start + timedelta(days=32)).replace(day=1)

        # Fetch trip data
        trips = self._fetch_trips(
            self._to_utc_start(month_start),
            self._to_utc_start(next_month),
            fg_ids,
            carsale_ids,
        )

        # Fetch sales with fallback
        try:
            sales = self._try_with_rel(
                self._fetch_sales,
                carsale_ids=carsale_ids,
                salesperson_id=(wizard.driver_id.id if wizard.driver_id else 0),
                start_ts=start_ts,
                end_ts_excl=end_ts_excl,
                start_date=ds,
                end_date_excl=self._next_day(de),
            )
        except Exception:
            sales = {
                "product_ids": [],
                "sold_qty_map": {},
                "inv_qty_map": {},
                "inv_amount_map": {},
                "unit_price_map": {}
            }

        # Fetch receipts summary with fallback
        try:
            receipts = self._try_with_rel(
                self._fetch_receipts_summary,
                carsale_ids=carsale_ids,
                salesperson_id=(wizard.driver_id.id if wizard.driver_id else 0),
                start_ts=start_ts,
                end_ts_excl=end_ts_excl,
                start_date=ds,
                end_date_excl=self._next_day(de),
            )
        except Exception:
            receipts = {
                "gross_sales": 0.0,
                "discount_total": 0.0,
                "net_sales": 0.0,
                "cash_received": 0.0,
                "transfer_received": 0.0,
                "cheque_received": 0.0,
                "received_total": 0.0,
                "ar_unpaid": 0.0,
            }

        # Fetch receipts details with fallback
        try:
            transfers, cheques, cash = self._try_with_rel(
                self._fetch_receipts_details,
                carsale_ids=carsale_ids,
                salesperson_id=(wizard.driver_id.id if wizard.driver_id else 0),
                start_ts=start_ts,
                end_ts_excl=end_ts_excl,
                start_date=ds,
                end_date_excl=self._next_day(de),
            )
        except Exception:
            transfers, cheques, cash = [], [], []

        # Build lines
        lines = self._build_lines(trips, sales)

        # Build totals
        totals = {
            "sold_amount_total": sum(l["amount"] for l in lines),
            "sold_qty_total": sum(l["sold_qty"] for l in lines),
            "transfer_qty_total": sum(l["transfer_total"] for l in lines),
        }
        totals.update(receipts)
        summary = self._build_summary(totals)
        totals.update(summary)

        return {
            "vehicle_name": vehicle_name,
            "carsale_location_name": vehicle_name,
            "trip_numbers": trips["trip_nos"],
            "trip_nos": trips["trip_nos"],
            "trip_date_map": trips.get("trip_date_map", {}),
            "date_start": ds,
            "date_end": de,
            "lines": lines,
            "totals": totals,
            "summary": summary,
            "bank_transfers": transfers,
            "cheques": cheques,
            "cash_received_items": cash,
            "trip_info": {"odometer_start": 0, "odometer_end": 0, "distance": 0},
            "final_summary": {"grand_total": totals.get("net_sales", 0.0)},
            "cash_summary": {},
        }

    def _build_lines(self, trips, sales):
        """Build product lines from trip and sales data."""
        product_ids = sorted(
            set(trips.get("product_ids", [])) | 
            set(sales.get("product_ids", []))
        )
        products = self.env["product.product"].browse(product_ids).sudo()

        trip_nos = trips.get("trip_nos", [])
        trip_qty_map = trips.get("trip_qty_map", {})
        transfer_map = trips.get("transfer_total_map", {})
        latest_map = trips.get("latest_trip_day_map", {})

        sold_map = sales.get("sold_qty_map", {})
        price_map = sales.get("unit_price_map", {})
        amount_map = sales.get("inv_amount_map", {})

        # ใช้ Dict เพื่อจับกลุ่มสินค้าที่ชื่อเหมือนกัน (กรณีมีแยก Product [FREE])
        grouped_data = {}

        for p in products:
            raw_name = self._strip_product_code(p.display_name)
            is_free_item = "[FREE]" in p.display_name.upper()
            
            # ตัดคำว่า [FREE] ออก เพื่อให้สินค้าแถมกับปกติจับกลุ่มเป็นบรรทัดเดียวกัน
            clean_name = re.sub(r'(?i)\s*\[FREE\]\s*', '', raw_name).strip()

            if clean_name not in grouped_data:
                grouped_data[clean_name] = {
                    "product_id": p.id,
                    "product_code": p.default_code or "",
                    "product_name": clean_name,
                    "trip_qtys": [0.0] * len(trip_nos),
                    "transfer_total": 0.0,
                    "sold_qty": 0.0,
                    "free_qty": 0.0,  # ตัวแปรใหม่สำหรับช่อง 'ชดเชย'
                    "price": 0.0,
                    "amount": 0.0,    # <--- แก้ไข Error: เพิ่ม amount กลับเข้ามา
                    "amount_money": 0.0,
                    "latest_transfer_date": None,
                }

            group = grouped_data[clean_name]

            # ดึงค่าของสินค้านั้นๆ
            transfer_total = transfer_map.get(p.id, 0.0) or 0.0
            sold_qty = sold_map.get(p.id, 0.0) or 0.0
            price = price_map.get(p.id, 0.0) or 0.0
            
            # ดึงค่า amount ป้องกันค่าว่าง
            amount = amount_map.get(p.id)
            if amount is None:
                amount = sold_qty * price
            amount = float(amount or 0.0)

            # คำนวณราคาเฉลี่ยเผื่อกรณีราคาหาย
            if not price and sold_qty > 0 and amount > 0:
                price = amount / sold_qty

            amount_money = float((sold_qty or 0.0) * (price or 0.0))
            latest_date = latest_map.get(p.id)

            # --- เริ่มรวมยอดเข้ากลุ่ม ---
            for i, tno in enumerate(trip_nos):
                group["trip_qtys"][i] += (trip_qty_map.get((p.id, tno), 0.0) or 0.0)
            
            group["transfer_total"] += transfer_total

            # ตรวจจับสินค้าฟรี (ชื่อมี [FREE] หรือ ราคาเป็น 0)
            if is_free_item or (price == 0 and sold_qty > 0):
                group["free_qty"] += sold_qty
            else:
                group["sold_qty"] += sold_qty
                if price > 0:
                    group["price"] = price # ยึดราคาของตัวที่ไม่ได้แถม

            group["amount"] += amount         # <--- แก้ไข Error: ยอด amount รวม
            group["amount_money"] += amount_money

            if latest_date:
                if not group["latest_transfer_date"] or latest_date > group["latest_transfer_date"]:
                    group["latest_transfer_date"] = latest_date

        # แปลง Dict กลับเป็น List และเรียงตามชื่อสินค้า
        lines = list(grouped_data.values())
        lines.sort(key=lambda x: x["product_name"])

        return lines

    # ============================================================
    # SQL Queries - Trips
    # ============================================================
    
    def _fetch_trips(self, start_ts, end_ts_excl, fg_ids, carsale_ids):
        """Fetch trip matrix data."""
        if not start_ts or not end_ts_excl or not carsale_ids:
            return {
                "trip_nos": [],
                "product_ids": [],
                "trip_qty_map": {},
                "transfer_total_map": {},
                "latest_trip_day_map": {},
            }

        sql = """
        WITH
        params AS (
            SELECT
                %(it_start_ts)s::timestamptz AS it_start_ts,
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
                (sp.date_done AT TIME ZONE %(tz)s)::date AS trip_day
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
                MAX((sp.date_done AT TIME ZONE %(tz)s)::date) AS latest_trip_day
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
            td.trip_day,
            tl.qty,
            tt.total_qty,
            tm.max_trip,
            lbp.latest_trip_day
        FROM transfer_lines tl
        JOIN trip_days td ON td.trip_no = tl.trip_no
        JOIN transfer_totals tt ON tt.product_id = tl.product_id
        CROSS JOIN trip_max tm
        LEFT JOIN latest_by_product lbp ON lbp.product_id = tl.product_id
        ORDER BY tl.product_id, tl.trip_no
        """

        self.env.cr.execute(sql, {
            "it_start_ts": start_ts,
            "it_end_ts_excl": end_ts_excl,
            "fg_ids": fg_ids or [],
            "carsale_root_ids": carsale_ids or [],
            "tz": self._get_tz(),
        })
        rows = self._fetchall_dict()

        trip_qty_map = {}
        transfer_total_map = {}
        product_ids = set()
        max_trip = 0
        latest_map = {}
        trip_date_map = {}

        for r in rows:
            pid = r["product_id"]
            tno = r["trip_no"]
            qty = float(r["qty"] or 0.0)
            trip_qty_map[(pid, tno)] = qty
            transfer_total_map[pid] = float(r["total_qty"] or 0.0)
            product_ids.add(pid)
            max_trip = max(max_trip, int(r["max_trip"] or 0))
            if r.get("latest_trip_day"):
                latest_map[pid] = r["latest_trip_day"]
            if r.get("trip_day"):
                trip_date_map[int(r["trip_no"])] = r["trip_day"]

        trip_nos = list(range(1, max_trip + 1)) if max_trip else []
        return {
            "trip_nos": trip_nos,
            "product_ids": list(product_ids),
            "trip_qty_map": trip_qty_map,
            "transfer_total_map": transfer_total_map,
            "latest_trip_day_map": latest_map,
            "trip_date_map": trip_date_map,
        }

    # ============================================================
    # SQL Queries - Sales
    # ============================================================
    
    def _fetch_sales(
        self,
        carsale_ids,
        salesperson_id,
        start_ts,
        end_ts_excl,
        start_date,
        end_date_excl,
        rel_table
    ):
        """Fetch sales and invoice summary."""
        rel_aml_col, rel_sol_col = self._get_rel_cols(rel_table)

        if not carsale_ids:
            return {
                "product_ids": [],
                "sold_qty_map": {},
                "inv_qty_map": {},
                "inv_amount_map": {},
                "unit_price_map": {}
            }

        sql = f"""
        WITH
        params AS (
            SELECT
                %(start_ts)s::timestamptz AS start_ts,
                %(end_ts_excl)s::timestamptz AS end_ts_excl,
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
            AND sp.location_id IN (SELECT id FROM carsale_tree)
        ),
        out_move_lines AS (
            SELECT
                sml.product_id,
                sml.quantity AS qty_done,
                sm.sale_line_id
            FROM stock_move_line sml
            JOIN stock_move sm ON sm.id = sml.move_id
            JOIN stock_picking sp ON sp.id = sml.picking_id
            WHERE sml.state = 'done'
            AND sm.sale_line_id IS NOT NULL
            AND sml.quantity != 0
            AND sp.id IN (SELECT id FROM out_pickings)
        ),
        so_lines AS (
            SELECT
                oml.product_id,
                oml.qty_done,
                sol.id AS sol_id,
                sol.price_unit AS sol_price_unit,
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
            -- เฉพาะ SOL ที่ราคา > 0 (ไม่นับของแถม)
            SELECT product_id, SUM(qty_done) AS sold_qty
            FROM filtered_sol
            WHERE sol_price_unit > 0
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
            "carsale_root_ids": carsale_ids or [],
            "salesperson_user_id": salesperson_id or 0,
            "start_ts": start_ts,
            "end_ts_excl": end_ts_excl,
            "start_date": start_date or start_ts.date(),
            "end_date_excl": end_date_excl or end_ts_excl.date(),
        })
        rows = self._fetchall_dict()

        product_ids = set()
        sold_qty_map = {}
        inv_qty_map = {}
        inv_amount_map = {}
        unit_price_map = {}

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

    # ============================================================
    # SQL Queries - Receipts Summary
    # ============================================================
    
    def _fetch_receipts_summary(
        self,
        carsale_ids,
        salesperson_id,
        start_ts,
        end_ts_excl,
        start_date,
        end_date_excl,
        rel_table,
    ):
        """Fetch receipts summary with payment breakdown."""
        rel_aml_col, rel_sol_col = self._get_rel_cols(rel_table)

        sql = f"""
        WITH
        params AS (
            SELECT
                %(start_ts)s::timestamptz AS start_ts,
                %(end_ts_excl)s::timestamptz AS end_ts_excl,
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
            AND sp.date_done < p.end_ts_excl
            AND sp.location_id IN (SELECT id FROM carsale_tree)
        ),
        out_move_lines AS (
            SELECT DISTINCT sm.sale_line_id
            FROM stock_move_line sml
            JOIN stock_move sm ON sm.id = sml.move_id
            WHERE sml.picking_id IN (SELECT id FROM out_pickings)
            AND sml.state = 'done'
            AND sm.sale_line_id IS NOT NULL
        ),
        filtered_sale_orders AS (
            SELECT DISTINCT so.id AS order_id
            FROM sale_order_line sol
            JOIN sale_order so ON so.id = sol.order_id
            WHERE sol.id IN (SELECT sale_line_id FROM out_move_lines)
            AND so.user_id = (SELECT salesperson_user_id FROM params)
        ),
        sale_order_invoices AS (
            SELECT DISTINCT am.id AS invoice_id
            FROM account_move am
            JOIN account_move_line aml ON aml.move_id = am.id
            JOIN {rel_table} rel ON rel.{rel_aml_col} = aml.id
            JOIN sale_order_line sol ON sol.id = rel.{rel_sol_col}
            WHERE sol.order_id IN (SELECT order_id FROM filtered_sale_orders)
            AND am.state = 'posted'
            AND am.move_type IN ('out_invoice', 'out_refund')
            AND aml.display_type = 'product'
        ),
        invoice_summary AS (
            SELECT
                SUM(CASE 
                    WHEN am.move_type = 'out_invoice' THEN am.amount_untaxed_signed
                    WHEN am.move_type = 'out_refund' THEN -am.amount_untaxed_signed
                    ELSE 0 
                END) AS net_sales,
                SUM(CASE 
                    WHEN am.move_type = 'out_invoice' THEN am.amount_tax_signed
                    WHEN am.move_type = 'out_refund' THEN -am.amount_tax_signed
                    ELSE 0 
                END) AS vat_amount,
                SUM(CASE 
                    WHEN am.move_type = 'out_invoice' THEN am.amount_total_signed
                    WHEN am.move_type = 'out_refund' THEN -am.amount_total_signed
                    ELSE 0 
                END) AS total_amount,
                SUM(CASE 
                    WHEN am.move_type = 'out_refund' THEN -am.amount_total_signed
                    ELSE 0 
                END) AS return_total_amount
            FROM account_move am
            WHERE am.id IN (SELECT invoice_id FROM sale_order_invoices)
        ),
        invoice_line_discount AS (
            SELECT
                SUM(
                    CASE
                        WHEN am.move_type = 'out_refund'
                        THEN -(aml.discount / 100.0 * aml.price_unit * aml.quantity)
                        ELSE  (aml.discount / 100.0 * aml.price_unit * aml.quantity)
                    END
                ) AS discount_total
            FROM account_move_line aml
            JOIN account_move am ON am.id = aml.move_id
            WHERE aml.display_type = 'product'
            AND am.id IN (SELECT invoice_id FROM sale_order_invoices)
        ),
        invoice_ar_lines AS (
            SELECT aml.id AS ar_line_id
            FROM account_move_line aml
            JOIN account_account aa ON aa.id = aml.account_id
            WHERE aa.account_type = 'asset_receivable'
            AND aml.move_id IN (SELECT invoice_id FROM sale_order_invoices)
        ),
        payment_reconciles AS (
            SELECT DISTINCT
                CASE
                    WHEN pr.debit_move_id IN (SELECT ar_line_id FROM invoice_ar_lines)
                    THEN pr.credit_move_id
                    ELSE pr.debit_move_id
                END AS payment_aml_id
            FROM account_partial_reconcile pr
            WHERE pr.debit_move_id IN (SELECT ar_line_id FROM invoice_ar_lines)
            OR pr.credit_move_id IN (SELECT ar_line_id FROM invoice_ar_lines)
        ),
        payment_moves AS (
            SELECT DISTINCT aml.move_id AS payment_move_id
            FROM account_move_line aml
            WHERE aml.id IN (SELECT payment_aml_id FROM payment_reconciles)
        ),
        all_payments AS (
            SELECT DISTINCT
                ap.id,
                ap.amount AS payment_amount,
                ap.journal_id,
                ap.payment_method_line_id
            FROM account_payment ap
            WHERE ap.move_id IN (SELECT payment_move_id FROM payment_moves)
            AND ap.state IN ('posted', 'reconciled', 'paid')
        ),
        payment_summary AS (
            SELECT
                COALESCE(SUM(CASE WHEN j.type = 'cash' THEN ap.payment_amount ELSE 0 END), 0) AS cash_received,
                COALESCE(SUM(CASE WHEN j.type = 'bank' AND NOT (
                        COALESCE(pml.name, '') ILIKE '%%cheque%%' OR 
                        COALESCE(pml.name, '') ILIKE '%%check%%' OR 
                        COALESCE(pml.name, '') ILIKE '%%เช็ค%%'
                    ) THEN ap.payment_amount ELSE 0 END), 0) AS transfer_received,
                COALESCE(SUM(CASE WHEN j.type = 'bank' AND (
                        COALESCE(pml.name, '') ILIKE '%%cheque%%' OR 
                        COALESCE(pml.name, '') ILIKE '%%check%%' OR 
                        COALESCE(pml.name, '') ILIKE '%%เช็ค%%'
                    ) THEN ap.payment_amount ELSE 0 END), 0) AS cheque_received
            FROM all_payments ap
            JOIN account_journal j ON j.id = ap.journal_id
            LEFT JOIN account_payment_method_line pml ON pml.id = ap.payment_method_line_id
        )
        SELECT
            i.net_sales AS gross_sales,
            COALESCE(d.discount_total, 0) AS discount_total,
            i.net_sales,
            p.cash_received,
            p.transfer_received,
            p.cheque_received,
            (p.cash_received + p.transfer_received + p.cheque_received) AS received_total,
            i.vat_amount,
            i.total_amount,
            i.return_total_amount,
            i.return_total_amount AS return_amount,
            (i.total_amount - i.return_total_amount -
            (p.cash_received + p.transfer_received + p.cheque_received)
            ) AS ar_unpaid
        FROM invoice_summary i
        CROSS JOIN invoice_line_discount d
        CROSS JOIN payment_summary p;
        """
        
        self.env.cr.execute(sql, {
            "carsale_root_ids": carsale_ids or [],
            "salesperson_user_id": salesperson_id,
            "start_ts": start_ts,
            "end_ts_excl": end_ts_excl,
            "start_date": start_date or start_ts.date(),
            "end_date_excl": end_date_excl or end_ts_excl.date(),
        })
        
        row = self._fetchall_dict()
        row = row[0] if row else {}
        
        return {
            "gross_sales": float(row.get("gross_sales") or 0.0),
            "discount_total": float(row.get("discount_total") or 0.0),
            "net_sales": float(row.get("net_sales") or 0.0),
            "cash_received": float(row.get("cash_received") or 0.0),
            "transfer_received": float(row.get("transfer_received") or 0.0),
            "cheque_received": float(row.get("cheque_received") or 0.0),
            "received_total": float(row.get("received_total") or 0.0),
            "vat_amount": float(row.get("vat_amount") or 0.0),
            "total_amount": float(row.get("total_amount") or 0.0),
            "ar_unpaid": float(row.get("ar_unpaid") or 0.0),
            "return_total_amount": float(row.get("return_total_amount") or 0.0),
            "return_amount": float(row.get("return_amount") or 0.0),
        }

    # ============================================================
    # SQL Queries - Receipts Details
    # ============================================================
    
    def _fetch_receipts_details(
        self,
        carsale_ids,
        salesperson_id,
        start_ts,
        end_ts_excl,
        start_date,
        end_date_excl,
        rel_table,
    ):
        """Fetch payment details: bank transfers, cheques, cash."""
        rel_aml_col, rel_sol_col = self._get_rel_cols(rel_table)
        
        sql = f"""
        WITH
        params AS (
            SELECT 
                %(start_date)s::date AS start_date,
                %(end_date_excl)s::date AS end_date_excl,
                %(carsale_root_ids)s::int[] AS carsale_root_ids,
                %(salesperson_user_id)s::int AS salesperson_user_id,
                %(start_ts)s::timestamptz AS start_ts,
                %(end_ts_excl)s::timestamptz AS end_ts_excl
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
            AND sp.date_done < p.end_ts_excl
            AND sp.location_id IN (SELECT id FROM carsale_tree)
        ),
        out_move_lines AS (
            SELECT DISTINCT sm.sale_line_id
            FROM stock_move_line sml
            JOIN stock_move sm ON sm.id = sml.move_id
            WHERE sml.picking_id IN (SELECT id FROM out_pickings)
            AND sml.state = 'done'
            AND sm.sale_line_id IS NOT NULL
        ),
        filtered_sale_orders AS (
            SELECT DISTINCT so.id AS order_id
            FROM sale_order_line sol
            JOIN sale_order so ON so.id = sol.order_id
            WHERE sol.id IN (SELECT sale_line_id FROM out_move_lines)
            AND so.user_id = (SELECT salesperson_user_id FROM params)
        ),
        sale_order_invoices AS (
            SELECT DISTINCT am.id AS invoice_id
            FROM account_move am
            JOIN account_move_line aml ON aml.move_id = am.id
            JOIN {rel_table} rel ON rel.{rel_aml_col} = aml.id
            JOIN sale_order_line sol ON sol.id = rel.{rel_sol_col}
            WHERE sol.order_id IN (SELECT order_id FROM filtered_sale_orders)
            AND am.state = 'posted'
            AND am.move_type IN ('out_invoice', 'out_refund')
            AND aml.display_type = 'product'
        ),
        invoice_ar_lines AS (
            SELECT aml.id AS ar_line_id,
                aml.move_id AS invoice_id
            FROM account_move_line aml
            JOIN account_account aa ON aa.id = aml.account_id
            WHERE aa.account_type = 'asset_receivable'
            AND aml.move_id IN (SELECT invoice_id FROM sale_order_invoices)
        ),
        payment_reconciles AS (
            SELECT DISTINCT
                CASE
                    WHEN pr.debit_move_id IN (SELECT ar_line_id FROM invoice_ar_lines)
                    THEN pr.credit_move_id
                    ELSE pr.debit_move_id
                END AS payment_aml_id
            FROM account_partial_reconcile pr
            WHERE pr.debit_move_id IN (SELECT ar_line_id FROM invoice_ar_lines)
            OR pr.credit_move_id IN (SELECT ar_line_id FROM invoice_ar_lines)
        ),
        payment_moves AS (
            SELECT DISTINCT aml.move_id AS payment_move_id
            FROM account_move_line aml
            WHERE aml.id IN (SELECT payment_aml_id FROM payment_reconciles)
        ),
        all_payments AS (
            SELECT DISTINCT
                ap.id,
                ap.date AS payment_date,
                ap.amount AS payment_amount,
                ap.partner_id,
                ap.journal_id,
                ap.payment_method_line_id,
                ap.move_id,
                am.ref AS ref,
                am.name AS payment_name
            FROM account_payment ap
            JOIN account_move am ON am.id = ap.move_id
            WHERE ap.move_id IN (SELECT payment_move_id FROM payment_moves)
            AND ap.state IN ('posted', 'reconciled', 'paid')
        ),
        payments_with_details AS (
            SELECT
                ap.*,
                string_agg(DISTINCT cio.name, ', ') AS cheque_number,
                MAX(cio.cheque_date) AS cheque_date_on_cheque,
                MAX(cio.id) AS cheque_id
            FROM all_payments ap
            LEFT JOIN account_payment_cheque_inbound_outbound_rel rel
                ON rel.account_payment_id = ap.id
            LEFT JOIN cheque_inbound_outbound cio
                ON cio.id = rel.cheque_inbound_outbound_id
            GROUP BY ap.id, ap.payment_date, ap.payment_amount, 
                    ap.partner_id, ap.journal_id, 
                    ap.payment_method_line_id, ap.move_id, 
                    ap.ref, ap.payment_name
        ),
        final_payments AS (
            SELECT
                pwd.*,
                CASE
                    WHEN pg_typeof(j.name) = 'jsonb'::regtype THEN
                        COALESCE(j.name->>'en_US', j.name->>'th_TH', j.name->>'en_GB', j.name::text)
                    ELSE j.name::text
                END AS journal_name,
                j.type AS journal_type,
                COALESCE(pml.name, '') AS method_name,
                rp.name AS partner_name,
                COALESCE(jb.name, '') AS bank_name,
                COALESCE(jpb.acc_number, '') AS bank_acc_number
            FROM payments_with_details pwd
            JOIN account_journal j ON j.id = pwd.journal_id
            LEFT JOIN account_payment_method_line pml 
                ON pml.id = pwd.payment_method_line_id
            LEFT JOIN res_partner rp ON rp.id = pwd.partner_id
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
        FROM final_payments
        ORDER BY payment_date, id;
        """
        
        self.env.cr.execute(sql, {
            "carsale_root_ids": carsale_ids or [],
            "salesperson_user_id": salesperson_id,
            "start_ts": start_ts,
            "end_ts_excl": end_ts_excl,
            "start_date": start_date,
            "end_date_excl": end_date_excl,
        })
        
        rows = self._fetchall_dict()
        
        # Classify payments
        transfers = []
        cheques = []
        cash = []
        
        for r in rows:
            item = {
                "payment_id": r.get("payment_id"),
                "payment_date": r.get("payment_date"),
                "partner_name": r.get("partner_name") or "",
                "journal_name": r.get("journal_name") or "",
                "bank_name": r.get("bank_name") or "",
                "bank_acc_number": r.get("bank_acc_number") or "",
                "method_name": r.get("method_name") or "",
                "ref": r.get("ref") or "",
                "amount": float(r.get("payment_amount") or 0.0),
                "cheque_number": r.get("cheque_number") or "",
                "cheque_date": r.get("cheque_date_on_cheque"),
            }
            
            jtype = (r.get("journal_type") or "").lower()
            method = (r.get("method_name") or "").lower()
            
            is_cheque = (
                r.get("cheque_id") is not None
                or "cheque" in method
                or "check" in method
                or "เช็ค" in method
            )
            
            if is_cheque:
                cheques.append(item)
            elif jtype == "bank":
                transfers.append(item)
            elif jtype == "cash":
                cash.append(item)
        
        _logger.debug( f"Receipts: {len(transfers)} bank, {len(cheques)} cheque, {len(cash)} cash")
        
        return transfers, cheques, cash