from odoo import models, fields
import io
import xlsxwriter
from datetime import datetime, timedelta, date
import pytz


class TripClosingXlsx(models.AbstractModel):
    _name = "trip.closing.xlsx"
    _description = "XLSX generator for Trip Closing Report"

    # =========================================================
    # Helpers
    # =========================================================
    def _to_user_tz(self, dt):
        """UTC naive datetime -> user timezone naive datetime"""
        if not dt:
            return dt
        if isinstance(dt, str):
            dt = fields.Datetime.from_string(dt)
        if not isinstance(dt, datetime):
            return dt

        tz = pytz.timezone(self.env.user.tz or "UTC")
        if dt.tzinfo:
            dt_utc = dt.astimezone(pytz.utc)
        else:
            dt_utc = pytz.utc.localize(dt)
        return dt_utc.astimezone(tz).replace(tzinfo=None)
    
    def _fmt_date(self, d):
        """Return พ.ศ. dd/mm/yy"""
        if not d:
            return ""
        if isinstance(d, str):
            d = fields.Date.from_string(d)
        if isinstance(d, datetime):
            d = self._to_user_tz(d).date()
        if not isinstance(d, date):
            return ""

        yy = (d.year + 543) % 100
        return f"{d.day:02d}/{d.month:02d}/{yy:02d}"
    
    def _get_bank_acc(self, l):
        return (
            l.get("bank_acc_number")
            or l.get("bank_account")
            or ""
        )
    
    # =========================================================
    # Main
    # =========================================================
    def generate_xlsx(self, wizard):
        wizard.ensure_one()

        queries = self.env["trip.closing.queries"]
        data = (
            queries.build_vehicle_data(wizard, wizard.location_id)
            if wizard.location_id
            else queries.build_driver_data(wizard)
        )

        trip_count = len(data.get("trip_nos", []))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet("Trip Closing")
        sheet_payment = workbook.add_worksheet("Payments")

        # ---------- Page setup ----------
        sheet.set_landscape()
        sheet.set_paper(9)
        sheet.set_margins(0.5, 0.5, 0.75, 0.75)

        # ---------- Column layout (QWeb aligned) ----------
        sheet.set_column("A:A", 18)        # วันที่
        sheet.set_column("B:C", 32)        # รายการ (merge)
        sheet.set_column(3, 3 + trip_count - 1, 7)  # ครั้งที่ (dynamic)

        base_col = 3 + trip_count
        sheet.set_column(base_col, base_col + 9, 11)

        # ---------- Styles ----------
        fmt = self._build_formats(workbook)

        row = 0
        row = self._render_header(sheet, row, wizard, data, fmt)
        row = self._render_product_table(sheet, row, data, fmt)
        row = self._render_summary_and_travel(sheet, row, wizard, data, fmt)

        all_bank_transfers = []
        all_cheques = []

        vehicles_data = [data]

        for v in vehicles_data:
            all_bank_transfers += v.get("bank_transfers", [])
            all_cheques += v.get("cheques", [])

        data["__all_bank_transfers"] = all_bank_transfers
        data["__all_cheques"] = all_cheques

        self._render_payment_sheet(sheet_payment, wizard, data, fmt)

        workbook.close()
        output.seek(0)
        return output.read()

    # =========================================================
    # Format
    # =========================================================
    def _build_formats(self, workbook):
        return {
            "title": workbook.add_format({
                "bold": True, "font_size": 16, "align": "center",
                "bg_color": "#2F2F2F", "font_color": "white", "border": 1
            }),
            "subtitle": workbook.add_format({
                "bold": True, "font_size": 13, "align": "center",
                "bg_color": "#D3D3D3", "border": 1
            }),
            "th": workbook.add_format({
                "bold": True, "align": "center", "valign": "vcenter",
                "bg_color": "#2F2F2F", "font_color": "white",
                "border": 1, "text_wrap": True
            }),
            "cell": workbook.add_format({"border": 1}),
            "cell_c": workbook.add_format({"border": 1, "align": "center"}),
            "num": workbook.add_format({
                "border": 1, "align": "right", "num_format": "#,##0.00"
            }),
            "box_l": workbook.add_format({
                "bold": True, "border": 1, "bg_color": "#E8E8E8"
            }),
            "box_v": workbook.add_format({
                "border": 1, "align": "right", "num_format": "#,##0.00"
            }),
            "cell_wrap": workbook.add_format({
                "border": 1, "text_wrap": True, "valign": "top",
            }),
            "payment_subtitle": workbook.add_format({
                "bold": True,
                "align": "left",
                "valign": "vcenter",
                "border": 1,
                "font_size": 11,
                "text_wrap": False,
            }),
            "box_head": workbook.add_format({
                "align": "left",
                "valign": "top",
                "text_wrap": True,
                "top": 1,
                "left": 1,
                "right": 1,
                # ❌ ไม่มี bottom
            }),

            "box_body": workbook.add_format({
                "align": "right",
                "valign": "bottom",
                "num_format": "#,##0.00",
                "text_wrap": True,
                "left": 1,
                "right": 1,
                "bottom": 1,
                # ❌ ไม่มี top
            }),
            "sign_head": workbook.add_format({
                "align": "center",
                "valign": "vcenter",
                "font_size": 11,
                "top": 1,
                "left": 1,
                "right": 1,
                # ❌ no bottom
            }),
            "sign_line": workbook.add_format({
                "align": "center",
                "valign": "bottom",
                "left": 1,
                "right": 1,
                # ❌ no top / bottom
            }),
            "sign_name": workbook.add_format({
                "align": "center",
                "valign": "top",
                "left": 1,
                "right": 1,
                "bottom": 1,
            }),
        }

    # =========================================================
    # Header
    # =========================================================
    def _render_header(self, sheet, row, wizard, data, f):
        report = self.env["report.trip_closing_report.report_trip_closing"]
        values = report._get_report_values([wizard.id], {"wizard_id": wizard.id})
        period_label = values.get("period_label", "")

        sheet.merge_range(row, 0, row, 14, "สรุปปิดการปฏิบัติงานหน่วยรถขายนอก", f["title"])
        row += 1
        sheet.merge_range(row, 0, row, 14, period_label, f["subtitle"])
        row += 2

        sheet.merge_range(row, 0, row, 7, f"หน่วยรถขาย: {data.get('carsale_location_name','')}", f["cell"])
        sheet.merge_range(row, 8, row, 14, f"ช่วงวันที่: {self._fmt_date(wizard.date_start)} - {self._fmt_date(wizard.date_end)}", f["cell"])
        row += 1

        sheet.merge_range(row, 0, row, 7, f"พนักงานขาย/คนขับ: {wizard.driver_id.name}", f["cell"])
        sheet.merge_range(
            row, 8, row, 14,
            f"วันที่พิมพ์รายงาน: {self._fmt_date(fields.Date.context_today(self))}",
            f["cell"]
        )
        return row + 2

    # =========================================================
    # Product Table
    # =========================================================
    def _render_product_table(self, sheet, row, data, f):
        trip_nos = data.get("trip_nos", [])
        trip_count = len(trip_nos)

        sheet.merge_range(row, 0, row + 1, 0, "ว.ด.ป.", f["th"])
        sheet.merge_range(row, 1, row + 1, 2, "รายการ", f["th"])

        if trip_count:
            sheet.merge_range(row, 3, row, 3 + trip_count - 1, "ครั้งที่", f["th"])

        base_col = 3 + trip_count
        tail_headers = [
            "รวม", "เหลือ", "ชดเชย", "ชดเชยพิเศษ",
            "ตัวอย่าง", "แปลงสินค้าออก", "รับสินค้าเข้า\nจากการแปลง",
            "ขาย", "ราคา", "จำนวนเงิน"
        ]

        for i, h in enumerate(tail_headers):
            sheet.merge_range(row, base_col + i, row + 1, base_col + i, h, f["th"])

        row += 1
        for i, t in enumerate(trip_nos):
            val = " " if not t or int(t) == 0 else str(t)
            sheet.write(row, 3 + i, val, f["th"])

        row += 1

        for l in data.get("lines", []):
            sheet.write(row, 0, self._fmt_date(l.get("latest_transfer_date")), f["cell_c"])
            sheet.merge_range(row, 1, row, 2, l.get("product_name", ""), f["cell"])

            for i in range(trip_count):
                qtys = l.get("trip_qtys", [])
                q = qtys[i] if i < len(qtys) else None
                sheet.write(row, 3 + i, "" if not q else q, f["cell_c"])

            col = base_col
            sheet.write(row, col, l.get("transfer_total", 0), f["num"]); col += 1
            for _ in range(6):
                sheet.write(row, col, "", f["cell"]); col += 1
            sheet.write(row, col, l.get("sold_qty", 0), f["num"]); col += 1
            sheet.write(row, col, l.get("price", 0), f["num"]); col += 1
            sheet.write(row, col, l.get("amount_money", 0), f["num"])
            row += 1

        return row + 2

    # =========================================================
    # Summary + Travel (same row plane)
    # =========================================================
    def _render_summary_and_travel(self, sheet, row, wizard, data, f):
        totals = data.get("totals", {})

        # -------------------------
        # LEFT : mileage / misc
        # -------------------------
        left_labels = [
            "เลขไมล์ไป",
            "เลขไมล์กลับ",
            "(ส่วนต่าง)",
            "ค่าน้ำมันรถ",
            "ผู้แทนเข้าบริหารวันที่",
            "มอบบัญชีวันที่",
        ]

        start = row
        for lbl in left_labels:
            sheet.merge_range(row, 0, row, 1, lbl, f["cell"])
            sheet.write(row, 2, "", f["cell"])   # ❗ ไม่ merge ตามที่ขอ
            row += 1

        # -------------------------
        # MIDDLE : travel dates (same plane)
        # -------------------------
        sheet.merge_range(start, 4, start, 5, "วันที่เดินทาง", f["box_l"])
        sheet.write(start, 6, "", f["cell"])

        sheet.merge_range(start + 1, 4, start + 1, 5, "วันที่กลับ", f["box_l"])
        sheet.write(start + 1, 6, "", f["cell"])

        # -------------------------
        # RIGHT : summary (MATCH QWEB)
        # -------------------------
        summary = [
            ("ยอดขายก่อนส่วนลด", totals.get("gross_sales", 0.0)),
            ("หัก ส่วนลด", totals.get("discount_amount", 0.0)),
            ("ยอดขายหลังส่วนลด (ไม่รวม VAT)", totals.get("untaxed_amount", 0.0)),
            ("VAT", totals.get("vat_amount", 0.0)),
            ("ยอดขายรวมภาษี", totals.get("total_amount", 0.0)),
            ("หัก คืนของ/ลดหนี้", totals.get("return_amount", 0.0)),
        ]

        r = start
        for label, val in summary:
            sheet.merge_range(r, 9, r, 12, label, f["box_l"])
            sheet.merge_range(r, 13, r, 14, val, f["box_v"])
            r += 1

        # -------------------------
        # FINAL TOTAL (bold / highlight)
        # -------------------------
        sheet.merge_range(r, 9, r, 12, "ยอดขายสุทธิ", f["box_l"])
        sheet.merge_range(
            r, 13, r, 14,
            totals.get("net_sales", 0.0),
            f["box_v"]
        )

        return max(row, r) + 1

    def _render_payment_sheet(self, sheet, wizard, data, f):
        # ---------- Page setup ----------
        sheet.set_landscape()
        sheet.set_paper(9)
        sheet.set_margins(0.5, 0.5, 0.75, 0.75)

        # ---------- Columns ----------
        sheet.set_column("A:A", 22)  # ชื่อลูกค้า / เลขที่เช็ค
        sheet.set_column("B:B", 22)  # เลขอ้างอิง / วันที่
        sheet.set_column("C:C", 20)
        sheet.set_column("D:D", 20)
        sheet.set_column("E:E", 18)
        sheet.set_column("F:F", 14)

        row = 0

        sheet.merge_range(
            row, 0, row, 5,
            "รายการโอนเงินเข้าบัญชีและเช็คที่ได้รับ",
            f["title"]
        )
        row += 2

        sheet.merge_range(
            row, 0, row, 3,
            f"หน่วยรถขาย: {data.get('carsale_location_name','')}",
            f["cell"]
        )
        sheet.merge_range(
            row, 4, row, 5,
            f"ช่วงวันที่: {self._fmt_date(wizard.date_start)} - {self._fmt_date(wizard.date_end)}",
            f["cell"]
        )
        row += 2

        # -------------------------
        # 1) รายการลูกค้าโอนเงินเข้าบัญชี
        # -------------------------
        sheet.merge_range(
            row, 0, row, 5,
            "1) รายการลูกค้าโอนเงินเข้าบัญชี",
            f["payment_subtitle"]
        )
        row += 1

        headers = [
            "ชื่อลูกค้า",
            "เลขที่อ้างอิง / ใบแจ้งหนี้",
            "วันที่โอน",
            "ธนาคาร",
            "เลขที่บัญชี",
            "จำนวนเงิน",
        ]

        for col, h in enumerate(headers):
            sheet.write(row, col, h, f["th"])
        row += 1

        total_transfer = 0.0

        for l in data.get("__all_bank_transfers", []):
            sheet.write(row, 0, l.get("partner_name",""), f["cell"])
            sheet.write(row, 1, l.get("ref") or l.get("communication",""), f["cell"])
            sheet.write(row, 2, self._fmt_date(l.get("payment_date")), f["cell_c"])
            sheet.write(row, 3, l.get("bank_name") or l.get("journal_name",""), f["cell"])
            sheet.write(row, 4, self._get_bank_acc(l), f["cell"])
            sheet.write(row, 5, l.get("amount",0.0), f["num"])
            total_transfer += l.get("amount", 0.0)
            row += 1

        sheet.merge_range(row, 0, row, 4, "รวมยอดโอนทั้งหมด", f["box_l"])
        sheet.write(row, 5, total_transfer, f["box_v"])
        row += 2

        # -------------------------
        # 2) รายการเช็คที่ได้รับจากลูกค้า
        # -------------------------
        sheet.merge_range(
            row, 0, row, 5,
            "2) รายการเช็คที่ได้รับจากลูกค้า",
            f["payment_subtitle"]
        )
        row += 1

        headers = [
            "เลขที่เช็ค",
            "วันที่เช็ค",
            "ชื่อลูกค้า",
            "ธนาคาร",
            "เลขที่บัญชี",
            "จำนวนเงิน",
        ]

        for col, h in enumerate(headers):
            sheet.write(row, col, h, f["th"])
        row += 1

        total_cheque = 0.0

        summary = data.get("final_summary", {})
        grand_total = summary.get("grand_total", 0.0)

        for l in data.get("__all_cheques", []):
            sheet.write(row, 0, l.get("cheque_number",""), f["cell"])
            sheet.write(row, 1, self._fmt_date(l.get("cheque_date")), f["cell_c"])
            sheet.write(row, 2, l.get("partner_name",""), f["cell"])
            sheet.write(row, 3, l.get("bank_name") or l.get("journal_name",""), f["cell"])
            sheet.write(row, 4, self._get_bank_acc(l), f["cell"])
            sheet.write(row, 5, l.get("amount",0.0), f["num"])
            total_cheque += l.get("amount", 0.0)
            row += 1

        sheet.merge_range(row, 0, row, 4, "รวมเช็คทั้งหมด", f["box_l"])
        sheet.write(row, 5, total_cheque, f["box_v"])
        row += 2

        sheet.merge_range(row, 0, row, 4, "ยอดรวมทั้งหมด", f["box_l"])
        sheet.write(row, 5, grand_total, f["box_v"])

        row += 2

        # ---------- Remark / Cash boxes ----------
        # ซ้าย
        sheet.merge_range(
            row, 0, row + 1, 1,
            "จ่ายเงินสดให้บริษัท (รอบถัดไป)",
            f["box_head"]
        )

        # ช่องกรอก
        sheet.merge_range(
            row + 2, 0, row + 2, 1,
            "",
            f["box_body"]
        )

        # กลาง
        sheet.merge_range(
            row, 2, row + 1, 3,
            "ลูกหนี้ที่มีเงื่อนไขซึ่งไม่คิด %\nผู้แทนต้องนำส่งเงินสด (รอบถัดไป)",
            f["box_head"]
        )

        sheet.merge_range(
            row + 2, 2, row + 2, 3,
            "",
            f["box_body"]
        )

        # ขวา (ยอดรวมทั้งหมด ซ้ำตาม QWeb)
        sheet.merge_range(
            row, 4, row + 1, 5,
            "ยอดรวมทั้งหมด",
            f["box_head"]
        )

        sheet.merge_range(
            row + 2, 4, row + 2, 5,
            f"{grand_total:,.2f}",
            f["box_body"]
        )

        row += 4

        # ---------- Signature Block ----------
        box_height = 5

        labels = [
            "ผู้รับเงิน / พนักงานขาย",
            "ผู้ตรวจนับสินค้า",
            "บัญชี / การเงิน",
        ]

        for i, label in enumerate(labels):
            col_start = i * 2
            col_end = col_start + 1

            # 1) Header — ไม่ merge แนวตั้ง (merge เฉพาะ column)
            sheet.merge_range(
                row, col_start, row, col_end,
                label,
                f["sign_head"]
            )

            # 2) เส้นเซ็น ____________________ (merge 2 แถว)
            sheet.merge_range(
                row + 1, col_start, row + 2, col_end,
                "______________________________",
                f["sign_line"]
            )

            # 3) ชื่อในวงเล็บ (merge 2 แถว)
            sheet.merge_range(
                row + 3, col_start, row + 4, col_end,
                "(........................................)",
                f["sign_name"]
            )

        row += box_height + 1
