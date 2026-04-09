# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import base64
from datetime import datetime, time, timedelta
import pytz


class TripClosingWizard(models.TransientModel):
    _name = "trip.closing.wizard"
    _description = "ตัวช่วยสร้างรายงานปิดทริป"

    period_id = fields.Many2one(
        "trip.closing.period",
        string="งวดรายงาน",
        domain="[('active','=',True)]",
    )

    date_start = fields.Date(string="วันที่เริ่มต้น", required=True)
    date_end = fields.Date(string="วันที่สิ้นสุด", required=True)

    driver_id = fields.Many2one(
        "res.users",
        string="พนักงานขาย / ผู้รับผิดชอบ",
        required=True,
    )

    location_id = fields.Many2one(
        "stock.location",
        string="คลัง/ตำแหน่งสินค้า (Carsale)",
        domain=[("usage", "=", "internal"), ("complete_name", "ilike", "CARSALE")],
        help="คลัง/ตำแหน่งรถขาย",
        ondelete="restrict",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        self.env["trip.closing.period"].sudo().ensure_periods(years_back=1, years_forward=0)
        return res

    @api.onchange("period_id")
    def _onchange_period_id(self):
        if self.period_id:
            today = fields.Date.context_today(self)
            self.date_start = min(self.period_id.date_start, today)
            self.date_end = min(self.period_id.date_end, today)

    @api.onchange("date_start", "date_end")
    def _onchange_dates_clear_period(self):
        if self.period_id and self.date_start and self.date_end:
            if (self.date_start != self.period_id.date_start) or (self.date_end != self.period_id.date_end):
                self.period_id = False

    @api.constrains("date_start", "date_end")
    def _check_dates(self):
        for rec in self:
            if rec.date_start and rec.date_end and rec.date_start > rec.date_end:
                raise UserError(_("วันที่เริ่มต้นต้องน้อยกว่าหรือเท่ากับวันที่สิ้นสุด"))

    @api.constrains("date_start", "date_end")
    def _check_dates_not_future(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.date_start and rec.date_start > today:
                raise ValidationError("วันที่เริ่มต้นต้องไม่เกินวันที่ปัจจุบัน")
            if rec.date_end and rec.date_end > today:
                raise ValidationError("วันที่สิ้นสุดต้องไม่เกินวันที่ปัจจุบัน")

    def _get_utc_dt_range_exclusive(self):
        """ใช้ตอนกรองฟิลด์ที่เป็น datetime: [start, end_exclusive)"""
        self.ensure_one()
        tz = pytz.timezone(self.env.user.tz or "UTC")

        start_local = tz.localize(datetime.combine(self.date_start, time.min))
        end_local_excl = tz.localize(datetime.combine(self.date_end + timedelta(days=1), time.min))

        start_utc = start_local.astimezone(pytz.utc).replace(tzinfo=None)
        end_utc_excl = end_local_excl.astimezone(pytz.utc).replace(tzinfo=None)
        return start_utc, end_utc_excl

    @api.constrains("date_start", "date_end")
    def _check_date_range(self):
        for rec in self:
            if rec.date_start and rec.date_end and rec.date_start > rec.date_end:
                raise ValidationError(_("วันที่เริ่มต้นต้องน้อยกว่าวันที่สิ้นสุด"))

            # แนะนำให้รายงานนี้ทำเป็น "รายเดือนเดียว" เพื่อให้ logic งวด 1-14 ชัดเจน
            if rec.date_start and rec.date_end:
                if (rec.date_start.year, rec.date_start.month) != (rec.date_end.year, rec.date_end.month):
                    raise ValidationError(_("รายงานนี้รองรับการออกรายงานครั้งละ 1 เดือนเท่านั้น (วันที่เริ่มต้น/สิ้นสุดต้องอยู่ในเดือนเดียวกัน)"))

    # ---------------- ช่วยสร้างชื่อไฟล์ ----------------
    def _safe_filename_part(self, s: str) -> str:
        return (s or "").replace("/", "_").replace("\\", "_").strip() or "NA"

    def _get_pdf_filename(self):
        self.ensure_one()
        dt = fields.Datetime.context_timestamp(self, fields.Datetime.now())
        ts = dt.strftime("%Y%m%d-%H%M%S")
        who = self._safe_filename_part(self.driver_id.name or "ไม่ระบุผู้รับผิดชอบ")
        return f"รายงานปิดทริป_{who}_{ts}.pdf"

    def _get_xlsx_filename(self):
        self.ensure_one()
        dt = fields.Datetime.context_timestamp(self, fields.Datetime.now())
        ts = dt.strftime("%Y%m%d-%H%M%S")
        who = self._safe_filename_part(self.driver_id.name or "ไม่ระบุผู้รับผิดชอบ")
        return f"รายงานปิดทริป_{who}_{ts}.xlsx"

    # ---------------- การเรียกรายงาน ----------------
    def _report_action(self, report_type="qweb-pdf"):
        self.ensure_one()
        action = self.env.ref("trip_closing_report.action_report_trip_closing").report_action(
            self, data={"wizard_id": self.id}
        )
        action["report_type"] = report_type
        return action

    def action_view_html(self):
        return self._report_action(report_type="qweb-html")

    def action_print_pdf(self):
        self.ensure_one()
        report = self.env["ir.actions.report"]
        pdf_content, _ = report._render_qweb_pdf(
            "trip_closing_report.report_trip_closing",
            res_ids=[self.id],
        )

        filename = self._get_pdf_filename()
        att = self.env["ir.attachment"].create({
            "name": filename,
            "type": "binary",
            "datas": base64.b64encode(pdf_content),
            "res_model": self._name,
            "res_id": self.id,
            "mimetype": "application/pdf",
            "public": False,
        })
        return {"type": "ir.actions.act_url", "url": f"/web/content/{att.id}?download=true", "target": "self"}

    def action_export_xlsx(self):
        self.ensure_one()
        xlsx_bytes = self.env["trip.closing.xlsx"].generate_xlsx(self)
        filename = self._get_xlsx_filename()

        att = self.env["ir.attachment"].create({
            "name": filename,
            "type": "binary",
            "datas": base64.b64encode(xlsx_bytes),
            "res_model": self._name,
            "res_id": self.id,
            "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "public": False,
        })
        return {"type": "ir.actions.act_url", "url": f"/web/content/{att.id}?download=1", "target": "self"}
