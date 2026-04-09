# -*- coding: utf-8 -*-

from odoo import fields, models


class StockRule(models.Model):
    _inherit = "stock.rule"

    def _make_po_get_domain(self, company_id, values, partner):
        domain = super()._make_po_get_domain(company_id, values, partner)
        # MPS sets skip_lead_time and compares against date_planned_mps.
        # Normalize to date so the same day merges into the existing draft PO.
        if self.env.context.get("skip_lead_time") and values.get("date_planned"):
            planned_date = fields.Date.to_date(values["date_planned"])
            new_domain = []
            replaced = False
            for term in domain:
                if isinstance(term, (list, tuple)) and len(term) >= 3 and term[0] == "date_planned_mps":
                    new_domain.append((term[0], term[1], planned_date))
                    replaced = True
                else:
                    new_domain.append(term)
            if not replaced:
                new_domain.append(("date_planned_mps", "=", planned_date))
            domain = tuple(new_domain)
        return domain
