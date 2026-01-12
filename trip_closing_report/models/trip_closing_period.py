# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import date, timedelta

class TripClosingPeriod(models.Model):
    _name = "trip.closing.period"
    _description = "Trip Closing Period (Monthly)"
    _order = "code desc"

    name = fields.Char(required=True, index=True)
    code = fields.Char(required=True, index=True)  # เช่น 2025-11
    date_start = fields.Date(required=True)
    date_end = fields.Date(required=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("code_unique", "unique(code)", "Period code must be unique."),
    ]

    def _compute_display_name(self):
        for record in self:
            record.display_name = record.code

    @api.model
    def ensure_periods(self, years_back=1, years_forward=0):
        """สร้าง period รายเดือนให้พอใช้งาน (ย้อนหลัง/ล่วงหน้า)"""
        today = fields.Date.context_today(self)
        y_start = today.year - int(years_back or 0)
        y_end = today.year + int(years_forward or 0)

        existing = set(self.search([("code", "!=", False)]).mapped("code"))
        to_create = []

        for y in range(y_start, y_end + 1):
            for m in range(1, 13):
                code = f"{y}-{m:02d}"
                if code in existing:
                    continue

                start = date(y, m, 1)
                end = date(y, 12, 31) if m == 12 else date(y, m + 1, 1) - timedelta(days=1)

                to_create.append({
                    "name": code,
                    "code": code,
                    "date_start": start,
                    "date_end": end,
                })

        if to_create:
            self.create(to_create)
        return True
