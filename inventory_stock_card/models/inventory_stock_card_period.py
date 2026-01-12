# inventory_stock_card/models/inventory_stock_card_period.py
from odoo import models, fields, api
from datetime import date, timedelta

class InventoryStockCardPeriod(models.Model):
    _name = "inventory.stock.card.period"
    _description = "Month Period"
    _order = "code desc"

    name = fields.Char(required=True, index=True)
    code = fields.Char(required=True, index=True)
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [("code_unique", "unique(code)", "Period code must be unique.")]

    def name_get(self):
        return [(r.id, r.code) for r in self]

    @api.model
    def ensure_current_year_periods(self):
        today = fields.Date.context_today(self)
        year = today.year
        existing = set(self.search([("code", "ilike", f"M{year}-")]).mapped("code"))
        to_create = []
        for m in range(1, today.month + 1):
            code = f"M{year}-{m:02d}"
            if code in existing: continue
            start = date(year, m, 1)
            end = date(year, 12, 31) if m == 12 else date(year, m + 1, 1) - timedelta(days=1)
            to_create.append({"name": code, "code": code, "date_from": start, "date_to": end})
        if to_create:
            self.create(to_create)
        return True