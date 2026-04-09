# -*- coding: utf-8 -*-
import calendar

# -*- coding: utf-8 -*-
from datetime import date, datetime, time, timedelta
from typing import Optional

import pytz
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

WEEKDAY_SELECTION = [
    ("mon", "วันจันทร์"),
    ("tue", "วันอังคาร"),
    ("wed", "วันพุธ"),
    ("thu", "วันพฤหัสบดี"),
    ("fri", "วันศุกร์"),
    ("sat", "วันเสาร์"),
    ("sun", "วันอาทิตย์"),
]

WEEK_RULE_SELECTION = [
    ("every", "ทุกสัปดาห์"),
    ("1", "สัปดาห์ที่ 1"),
    ("2", "สัปดาห์ที่ 2"),
    ("3", "สัปดาห์ที่ 3"),
    ("4", "สัปดาห์ที่ 4"),
]


def float_to_hour_minute(value: Optional[float]) -> tuple[int, int]:
    """Convert a float-time (e.g. 9.5) into (hour, minute)."""
    if value is None:
        return (9, 0)
    hours = int(value)
    minutes = int(round((value - hours) * 60.0))
    if minutes >= 60:
        hours += 1
        minutes -= 60
    hours = min(max(hours, 0), 23)
    minutes = min(max(minutes, 0), 59)
    return (hours, minutes)


class PpsWeekday(models.Model):
    _name = "pps.weekday"
    _description = "Payment Weekday"
    _order = "sequence, id"

    name = fields.Char(required=True)
    code = fields.Selection(
        selection=WEEKDAY_SELECTION,
        required=True,
        help="Internal code for the weekday.",
    )
    sequence = fields.Integer(default=10)

    _sql_constraints = [
        ("pps_weekday_unique_code", "unique(code)", "Weekday code must be unique."),
    ]

    @api.depends("code")
    def _compute_display_name(self):
        code_map = dict(WEEKDAY_SELECTION)
        for rec in self:
            rec.display_name = code_map.get(rec.code) or rec.name


class PpsDomDay(models.Model):
    _name = "pps.dom_day"
    _description = "Payment Day of Month"
    _order = "day asc"

    name = fields.Char(required=True, help="ชื่อที่แสดง เช่น '1', '15', '30'")
    day = fields.Integer(required=True, help="วันที่ 1-31")

    _sql_constraints = [
        ("pps_dom_day_unique_day", "unique(day)", "Day value must be unique."),
    ]


class PpsSchedule(models.Model):
    _name = "pps.schedule"
    _description = "Customer Payment Schedule"
    _rec_name = "name"
    _order = "partner_id, name, id"

    partner_id = fields.Many2one(
        "res.partner", required=True, ondelete="cascade", index=True
    )
    active = fields.Boolean(default=True)
    schedule_type = fields.Selection(
        selection=[("payment", "รับชำระเงิน"), ("billing", "วางบิล")],
        default=lambda self: self.env.context.get("default_schedule_type", "payment"),
        required=True,
    )
    mode = fields.Selection(
        selection=[("dom", "ระบุวันที่"), ("dow", "ระบุวันในสัปดาห์")],
        required=True,
        default="dom",
        help="เลือกรูปแบบการกำหนดรอบ",
    )

    dom_day_ids = fields.Many2many(
        "pps.dom_day",
        "pps_schedule_dom_rel",
        "schedule_id",
        "dom_id",
        string="วันที่",
        help="เลือกวันที่ เช่น 1, 15, 30",
    )
    dom_everyday = fields.Boolean(
        string="ทุกวัน",
        help="หากเปิดใช้งาน รอบนี้จะรันทุกวัน",
    )

    dow_weekday_ids = fields.Many2many(
        "pps.weekday",
        "pps_schedule_weekday_rel",
        "schedule_id",
        "weekday_id",
        string="วันในสัปดาห์",
        help="เลือกวันในสัปดาห์",
    )
    week_rule = fields.Selection(
        selection=WEEK_RULE_SELECTION,
        default="every",
        help="เลือก 'ทุกสัปดาห์' หรือระบุสัปดาห์ที่ต้องการ",
    )

    time_float = fields.Float(
        string="เวลา",
        default=9.0,
        help="เวลา (HH:MM) ที่จะเก็บเงิน",
    )
    description = fields.Char(string="หมายเหตุ")
    next_run = fields.Datetime(
        string="รอบถัดไป",
        compute="_compute_next_run",
        store=True,
        readonly=True,
        help="วันเวลาที่ระบบคำนวณให้",
    )
    name = fields.Char(
        string="ชื่อเรียก",
        compute="_compute_name",
        store=True,
        readonly=True,
    )

    partner_display_name = fields.Char(
        related="partner_id.display_name", string="พาร์ทเนอร์", store=False
    )

    @api.constrains("mode", "dom_day_ids", "dom_everyday", "dow_weekday_ids")
    def _check_selection(self):
        for rec in self:
            if rec.mode == "dom" and not rec.dom_everyday and not rec.dom_day_ids:
                raise ValidationError(
                    _("สำหรับโหมด 'ระบุวันที่' ต้องเลือกวันที่ หรือเปิดใช้งาน 'ทุกวัน'")
                )
            if rec.mode == "dow" and not rec.dow_weekday_ids:
                raise ValidationError(
                    _("สำหรับโหมด 'ระบุวันในสัปดาห์' ต้องเลือกวันอย่างน้อยหนึ่งวัน")
                )

    @api.depends(
        "active",
        "mode",
        "dom_everyday",
        "dom_day_ids",
        "dom_day_ids.day",
        "dow_weekday_ids",
        "dow_weekday_ids.code",
        "week_rule",
        "time_float",
    )
    def _compute_next_run(self):
        """Compute the next occurrence in the user's timezone, then store in UTC."""
        for rec in self:
            rec.next_run = rec._get_next_run_datetime()

    def _get_next_run_datetime(self):
        self.ensure_one()
        if not self.active:
            return False

        now_utc = fields.Datetime.now()
        now_local = fields.Datetime.context_timestamp(self, now_utc)
        user_tz = pytz.timezone(self._get_user_timezone())
        now_local_naive = now_local.replace(tzinfo=None)

        candidate_local = self._compute_candidate_local(now_local_naive)
        if not candidate_local:
            return False

        hh, mm = float_to_hour_minute(self.time_float or 9.0)
        candidate_local = candidate_local.replace(
            hour=hh, minute=mm, second=0, microsecond=0
        )

        candidate_local = self._ensure_future_candidate(
            candidate_local, now_local_naive, hh, mm
        )
        if not candidate_local:
            return False

        if candidate_local.tzinfo is None:
            candidate_local = user_tz.localize(candidate_local)
        candidate_utc = candidate_local.astimezone(pytz.UTC)
        return candidate_utc.replace(tzinfo=None)

    def _compute_candidate_local(self, reference: datetime) -> Optional[datetime]:
        if self.mode == "dom":
            return self._next_local_dom(reference)
        return self._next_local_dow(reference)

    def _ensure_future_candidate(
        self, candidate: datetime, reference: datetime, hh: int, mm: int
    ) -> Optional[datetime]:
        if candidate > reference:
            return candidate
        next_candidate = self._compute_candidate_local(reference + timedelta(days=1))
        if not next_candidate:
            return None
        return next_candidate.replace(hour=hh, minute=mm, second=0, microsecond=0)

    @api.depends(
        "mode",
        "dom_everyday",
        "dom_day_ids",
        "dom_day_ids.day",
        "dow_weekday_ids",
        "dow_weekday_ids.code",
        "week_rule",
        "time_float",
    )
    def _compute_name(self):
        week_rule_labels = {key: _(label) for key, label in WEEK_RULE_SELECTION}
        weekday_labels = {key: _(label) for key, label in WEEKDAY_SELECTION}
        for rec in self:
            hh, mm = float_to_hour_minute(rec.time_float or 9.0)
            time_part = f"{hh:02d}:{mm:02d}"
            pattern = rec._describe_pattern(weekday_labels, week_rule_labels)
            rec.name = f"{pattern} @ {time_part}" if pattern else time_part

    def _describe_pattern(
        self,
        weekday_labels: dict[str, str],
        week_rule_labels: dict[str, str],
    ) -> str:
        self.ensure_one()
        if self.mode == "dom":
            return self._describe_dom_pattern()
        return self._describe_dow_pattern(weekday_labels, week_rule_labels)

    def _describe_dom_pattern(self) -> str:
        if self.dom_everyday:
            return _("ทุกวัน")
        days = self.dom_day_ids.sorted("day").mapped("day")
        if not days:
            return _("(ไม่ระบุ)")
        return ", ".join(str(day) for day in days)

    def _describe_dow_pattern(
        self,
        weekday_labels: dict[str, str],
        week_rule_labels: dict[str, str],
    ) -> str:
        records = self.dow_weekday_ids.sorted("sequence")
        codes = records.mapped("code")
        if not codes:
            return _("(ไม่ระบุ)")
        label_list = [weekday_labels.get(code, code.title()) for code in codes]
        pattern = ", ".join(label_list)
        if self.week_rule and self.week_rule != "every":
            return _(
                "%(number)s · %(pattern)s",
                number=week_rule_labels.get(self.week_rule, self.week_rule),
                pattern=pattern,
            )
        return pattern

    def _get_user_timezone(self) -> str:
        self.ensure_one()
        return self.env.context.get("tz") or self.env.user.tz or "UTC"

    # ---------- Helpers (local-time arithmetic) ----------

    def _next_local_dom(self, ref_dt: datetime) -> Optional[datetime]:
        """Next date for Day-of-Month mode from a local reference datetime (naive)."""
        self.ensure_one()
        if self.dom_everyday:
            return ref_dt

        days = sorted(self.dom_day_ids.mapped("day"))
        if not days:
            return None

        yr, mo = ref_dt.year, ref_dt.month
        last_day = calendar.monthrange(yr, mo)[1]
        today = ref_dt.date()
        candidates: list[date] = []
        for day_value in days:
            day_clamped = min(day_value, last_day)
            candidate_date = date(yr, mo, day_clamped)
            if candidate_date >= today:
                candidates.append(candidate_date)
        if candidates:
            return datetime.combine(min(candidates), time(hour=ref_dt.hour, minute=ref_dt.minute))

        mo2 = mo + 1
        yr2 = yr + (1 if mo2 > 12 else 0)
        mo2 = 1 if mo2 > 12 else mo2
        last_day2 = calendar.monthrange(yr2, mo2)[1]
        cand2 = min(days)
        cand2 = min(cand2, last_day2)
        return datetime(yr2, mo2, cand2, ref_dt.hour, ref_dt.minute)

    def _next_local_dow(self, ref_dt: datetime) -> Optional[datetime]:
        """Next date for Day-of-Week mode (supports Every or Week #1-#4)."""
        self.ensure_one()
        weekday_indices = self._weekday_indices()
        if not weekday_indices:
            return None

        if self.week_rule == "every":
            return self._next_dow_every(ref_dt, weekday_indices)
        return self._next_dow_specific_week(ref_dt, weekday_indices)

    def _next_dow_every(self, ref_dt: datetime, weekday_indices: list[int]) -> datetime:
        for offset in range(0, 8):
            candidate = ref_dt + timedelta(days=offset)
            if candidate.weekday() in weekday_indices:
                return candidate
        return ref_dt + timedelta(days=7)

    def _next_dow_specific_week(self, ref_dt: datetime, weekday_indices: list[int]) -> Optional[datetime]:
        week_no = int(self.week_rule)
        today = ref_dt.date()
        current = self._nth_weekday_candidates(ref_dt.year, ref_dt.month, weekday_indices, week_no, not_before=today)
        if current:
            return datetime.combine(min(current), time(hour=ref_dt.hour, minute=ref_dt.minute))

        next_month_date = self._first_of_next_month(ref_dt)
        upcoming = self._nth_weekday_candidates(next_month_date.year, next_month_date.month, weekday_indices, week_no)
        if upcoming:
            return datetime.combine(min(upcoming), time(hour=ref_dt.hour, minute=ref_dt.minute))
        return ref_dt + timedelta(days=7)

    def _weekday_indices(self) -> list[int]:
        code2idx = {code: idx for idx, (code, _label) in enumerate(WEEKDAY_SELECTION)}
        return sorted(
            code2idx[code] for code in self.dow_weekday_ids.mapped("code") if code in code2idx
        )

    def _nth_weekday_candidates(
        self,
        year: int,
        month: int,
        weekday_indices: list[int],
        week_no: int,
        *,
        not_before: Optional[date] = None,
    ) -> list[date]:
        results: list[date] = []
        for idx in weekday_indices:
            candidate = self._nth_weekday_in_month(year, month, idx, week_no)
            if candidate and (not not_before or candidate >= not_before):
                results.append(candidate)
        return results

    @staticmethod
    def _first_of_next_month(ref_dt: datetime) -> date:
        month = ref_dt.month + 1
        year = ref_dt.year + (1 if month > 12 else 0)
        month = 1 if month > 12 else month
        return date(year, month, 1)

    @staticmethod
    def _nth_weekday_in_month(y: int, m: int, weekday_idx: int, n: int) -> Optional[date]:
        first = date(y, m, 1)
        delta = (weekday_idx - first.weekday()) % 7
        day = 1 + delta + (n - 1) * 7
        last_day_month = calendar.monthrange(y, m)[1]
        if day > last_day_month:
            return None
        return date(y, m, day)


class ResPartner(models.Model):
    _inherit = "res.partner"

    pps_schedule_ids = fields.One2many(
        "pps.schedule",
        "partner_id",
        string="ตารางวางบิล/รับเช็ค (Payment)",
        domain=[("schedule_type", "=", "payment")],
        help="กำหนดรอบวางบิล/รับเช็คสำหรับลูกค้า",
    )
    pps_billing_schedule_ids = fields.One2many(
        "pps.schedule",
        "partner_id",
        string="ตารางวางบิล (Billing)",
        domain=[("schedule_type", "=", "billing")],
        help="กำหนดรอบวางบิลสำหรับลูกค้า",
    )
