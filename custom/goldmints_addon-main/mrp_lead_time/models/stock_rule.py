from dateutil.relativedelta import relativedelta

from odoo import fields, models


class StockRule(models.Model):
    _inherit = "stock.rule"

    def _prepare_mo_vals(self, product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values, bom):
        res = super()._prepare_mo_vals(
            product_id,
            product_qty,
            product_uom,
            location_dest_id,
            name,
            origin,
            company_id,
            values,
            bom,
        )
        lead_days = values.get("mfg_lead_time")
        if lead_days in (None, False):
            lead_days = product_id.mfg_lead_time
        lead_days = int(lead_days or 0)
        if lead_days <= 0:
            return res

        deadline = values.get("date_deadline") or values.get("date_planned") or res.get("date_deadline")
        deadline = fields.Datetime.to_datetime(deadline)
        if not deadline:
            return res

        res["date_deadline"] = deadline
        res["date_start"] = deadline - relativedelta(days=lead_days)
        return res
