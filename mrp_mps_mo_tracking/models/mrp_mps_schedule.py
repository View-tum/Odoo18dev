# -*- coding: utf-8 -*-
from odoo import models


class MrpProductionSchedule(models.Model):
    _inherit = "mrp.production.schedule"

    # Removed mps_mo_count and related logic as requested

    def action_replenish(self, based_on_lead_time=False, **kwargs):
        batch = self.env["mrp.mps.batch"].create({
            "note": "Created from MPS Replenish",
        })
        return super(MrpProductionSchedule, self.with_context(
            mps_active_batch_id=batch.id
        )).action_replenish(based_on_lead_time=based_on_lead_time)

    def name_get(self):
        result = []
        for rec in self:
            product = getattr(rec, "product_id", False) or getattr(rec, "product_tmpl_id", False)
            wh = getattr(rec, "warehouse_id", False)
            parts = []
            if product:
                parts.append(product.display_name)
            if wh:
                parts.append(wh.display_name)
            label = " / ".join(parts) if parts else "MPS Line"
            result.append((rec.id, f"MPS: {label} (#{rec.id})"))
        return result
