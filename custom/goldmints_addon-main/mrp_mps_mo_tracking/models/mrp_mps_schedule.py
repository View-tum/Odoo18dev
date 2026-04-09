# -*- coding: utf-8 -*-
from odoo import models


class MrpProductionSchedule(models.Model):
    _inherit = "mrp.production.schedule"

    # Removed mps_mo_count and related logic as requested

    def action_replenish(self, based_on_lead_time=False, **kwargs):
        batch_id = self.env.context.get("mps_active_batch_id")
        if not batch_id:
            batch = self.env["mrp.mps.batch"].create({
                "note": "Created from MPS Replenish",
            })
            batch_id = batch.id
            self = self.with_context(mps_active_batch_id=batch_id)

        return super(MrpProductionSchedule, self).action_replenish(
            based_on_lead_time=based_on_lead_time, **kwargs
        )

    def _get_forecasts_state(self, production_schedule_states, date_range, procurement_date):
        """
        Keep standard behavior, but if user manually edits replenish qty in a future
        period, prioritize that period for the row-level Order button.
        """
        forecasts_state = super()._get_forecasts_state(
            production_schedule_states, date_range, procurement_date
        )
        for schedule in self:
            schedule_states = forecasts_state.get(schedule.id) or []
            schedule_values = (
                production_schedule_states.get(schedule.id, {}).get("forecast_ids") or []
            )
            manual_indexes = []
            for index, value in enumerate(schedule_values):
                if index >= len(schedule_states):
                    continue
                state = schedule_states[index]
                if state.get("state") in ("launched", "to_correct"):
                    continue
                replenish_qty = value.get("replenish_qty") or 0.0
                incoming_qty = value.get("incoming_qty") or 0.0
                if value.get("replenish_qty_updated") and (replenish_qty - incoming_qty) > 0:
                    manual_indexes.append(index)

            if not manual_indexes:
                continue

            for state in schedule_states:
                state["forced_replenish"] = False
            schedule_states[min(manual_indexes)]["forced_replenish"] = True

        return forecasts_state

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
