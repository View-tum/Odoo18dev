# trip_closing_report/report/report_trip_closing.py
# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import date, datetime
import pytz


TH_MONTHS = [
    "", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
]

class ReportTripClosing(models.AbstractModel):
    _name = "report.trip_closing_report.report_trip_closing"
    _description = "Trip Closing Report"

    # -----------------------------
    # TH Date Formatter (พ.ศ. dd/mm/yy)
    # -----------------------------
    def _to_user_tz(self, dt):
        """UTC naive datetime -> user timezone naive datetime"""
        if not dt:
            return dt
        if isinstance(dt, str):
            dt = fields.Datetime.from_string(dt)
        if not isinstance(dt, datetime):
            return dt

        tz = pytz.timezone(self.env.user.tz or "UTC")
        dt_utc = pytz.utc.localize(dt)  # treat naive as UTC
        return dt_utc.astimezone(tz).replace(tzinfo=None)

    def format_th_date(self, d):
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

    def format_th_datetime(self, dt):
        """Return พ.ศ. dd/mm/yy (ถ้าจะเอาเวลา ค่อยขยายทีหลัง)"""
        if not dt:
            return ""
        if isinstance(dt, str):
            dt = fields.Datetime.from_string(dt)
        if isinstance(dt, datetime):
            dt = self._to_user_tz(dt)
            return self.format_th_date(dt.date())
        return self.format_th_date(dt)

    def format_th_date_long(self, d):
        """Return: 'วันที่ 1 ธันวาคม พ.ศ. 2568' """
        if not d:
            return ""
        if isinstance(d, str):
            d = fields.Date.from_string(d)
        if isinstance(d, datetime):
            d = self._to_user_tz(d).date()
        if not isinstance(d, date):
            return ""

        be_year = d.year + 543
        month_name = TH_MONTHS[d.month]
        return f"วันที่ {d.day} {month_name} พ.ศ. {be_year}"

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}
        wizard_id = (data.get("wizard_id") or (docids and docids[0]))
        wizard = self.env["trip.closing.wizard"].browse(wizard_id).exists()
        if not wizard:
            raise UserError(_("Wizard not found."))

        queries = self.env["trip.closing.queries"]
        vehicles_data = []

        if wizard.location_id:
            vehicles_data = [queries.build_vehicle_data(wizard, wizard.location_id)]
        else:
            vehicles_data = [queries.build_driver_data(wizard)]

        # ✅ period_label เป็น พ.ศ.
        # หาเลขครั้งล่าสุดจาก trip_nos / trip_numbers
        last_trip_no = 0
        for v in (vehicles_data or []):
            tnos = v.get("trip_numbers") or v.get("trip_nos") or v.get("trip_nos") or []
            if tnos:
                try:
                    last_trip_no = max(last_trip_no, max([int(x) for x in tnos if x]))
                except Exception:
                    pass

        ds = wizard.date_start
        de = wizard.date_end

        # สร้าง period label ตามที่ต้องการ
        period_label = ""
        if ds and de:
            ds_long = self.format_th_date_long(ds)
            de_long = self.format_th_date_long(de)
            if last_trip_no:
                period_label = f"ครั้งที่ {last_trip_no} {ds_long} ถึง {de_long}"
            else:
                period_label = f"{ds_long} ถึง {de_long}"

        # ✅ report_date เป็น พ.ศ.
        report_date = self.format_th_date(fields.Date.context_today(wizard))

        return {
            "doc_ids": [wizard.id],
            "doc_model": "trip.closing.wizard",
            "docs": wizard,
            "vehicles_data": vehicles_data,
            "period_label": period_label,
            "report_date": report_date,

            # ✅ ส่ง formatter ให้ QWeb เรียกใช้
            "format_th_date": self.format_th_date,
            "format_th_datetime": self.format_th_datetime,
            "format_th_date_long": self.format_th_date_long,
        }
