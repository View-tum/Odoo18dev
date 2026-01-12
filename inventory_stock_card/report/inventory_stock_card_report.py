# inventory_stock_card/report/inventory_stock_card_report.py
from odoo import models, api, fields
from ..utils.inventory_stock_card_utils import fmt, money, qty, thdate

class InventoryStockCardReport(models.AbstractModel):
    _name = "report.inventory_stock_card.report_stock_card"
    _description = "Stock Card QWeb Data Provider"

    period_id = fields.Many2one("inventory.stock.card.period", string="Period")

    @api.onchange("period_id")
    def _onchange_period_id_fill_dates(self):
        if self.period_id:
            self.date_from = self.period_id.date_from
            self.date_to = self.period_id.date_to

    @api.onchange("company_id")
    def _onchange_company_id_limit_periods(self):
        self.env["inventory.stock.card.period"].ensure_current_year_periods()
        year = fields.Date.context_today(self).year
        return {"domain": {"period_id": [("code", "ilike", f"M{year}-")]}}

    @api.model
    def _get_report_values(self, docids, data=None):
        wizard = None
        payload = {}
        # แก้ไข Model Name ในการ browse
        if data and data.get("wizard_id"):
            wizard = self.env["inventory.stock.card.wizard"].browse(data["wizard_id"])
        elif docids:
            wizard = self.env["inventory.stock.card.wizard"].browse(docids[:1])
            
        if wizard and wizard.exists():
            payload = wizard._build_report_payload() or {}

        # Wrapper functions เพื่อส่ง env/wizard
        def qweb_fmt(value, dp=None, monetary=False, currency=None, digits=None):
            return fmt(self.env, value, dp=dp, monetary=monetary, currency=currency, digits=digits, wizard=wizard)
        def qweb_money(value, currency=None, show_symbol=True):
            return money(self.env, value, currency=currency, wizard=wizard, show_symbol=show_symbol)
        def qweb_qty(value, uom_name=None):
            return qty(self.env, value, uom_name=uom_name)
        def qweb_thdate(dt_in):
            return thdate(self.env, dt_in)

        return {
            "doc_ids": docids,
            "doc_model": "inventory.stock.card.wizard",
            "docs": wizard,
            "payload": payload,
            "fmt": qweb_fmt,
            "thdate": qweb_thdate,
            "money": qweb_money,
            "qty": qweb_qty,
        }