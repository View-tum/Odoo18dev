from odoo import _, models
from odoo.tools.misc import format_date


class MrpProductionSchedule(models.Model):
    _inherit = "mrp.production.schedule"

    def action_replenish(self, based_on_lead_time=False, **kwargs):
        selected_indices = self.env.context.get("mps_selected_period_indices")

        if selected_indices is None:
            return super().action_replenish(based_on_lead_time=based_on_lead_time, **kwargs)

        if not selected_indices:
            return

        production_schedules_to_replenish = self.filtered(
            lambda p: p.replenish_trigger != "never"
        )
        production_schedule_states = (
            production_schedules_to_replenish.get_production_schedule_view_state()
        )
        production_schedule_states = {
            mps["id"]: mps for mps in production_schedule_states
        }
        procurements = []
        forecasts_values = []
        forecasts_to_set_as_launched = self.env["mrp.product.forecast"]

        for production_schedule in production_schedules_to_replenish:
            production_schedule_state = production_schedule_states[
                production_schedule.id
            ]

            bom = self.env["mrp.bom"]._bom_find(
                production_schedule.product_id,
                company_id=production_schedule.company_id.id,
                bom_type="phantom",
            )[production_schedule.product_id]
            product_ratio = []
            if bom:
                dummy, bom_lines = bom.explode(production_schedule.product_id, 1)
                product_ids = [l[0].product_id.id for l in bom_lines]
                product_ids_with_forecast = (
                    self.env["mrp.production.schedule"]
                    .search(
                        [
                            ("company_id", "=", production_schedule.company_id.id),
                            ("warehouse_id", "=", production_schedule.warehouse_id.id),
                            ("product_id", "in", product_ids),
                        ]
                    )
                    .product_id.ids
                )
                product_ratio += [
                    (l[0], l[0].product_qty * l[1]["qty"])
                    for l in bom_lines
                    if l[0].product_id.id not in product_ids_with_forecast
                ]

            replenishment_field = (
                based_on_lead_time and "to_replenish" or "forced_replenish"
            )
            forecasts_to_replenish = [
                (idx, f)
                for idx, f in enumerate(
                    production_schedule_state["forecast_ids"]
                )
                if f[replenishment_field] and idx in selected_indices
            ]

            for _idx, forecast in forecasts_to_replenish:
                existing_forecasts = production_schedule.forecast_ids.filtered(
                    lambda p: p.date >= forecast["date_start"]
                    and p.date <= forecast["date_stop"]
                )

                week_name = self._get_mps_week_name(
                    forecast["date_start"], forecast["date_stop"]
                )
                extra_values = production_schedule._get_procurement_extra_values(
                    forecast
                )
                extra_values["mps_week_name"] = week_name

                quantity = forecast["replenish_qty"] - forecast["incoming_qty"]
                if not bom:
                    procurements.append(
                        self.env["procurement.group"].Procurement(
                            production_schedule.product_id,
                            quantity,
                            production_schedule.product_uom_id,
                            production_schedule.warehouse_id.lot_stock_id,
                            production_schedule.product_id.name,
                            "MPS",
                            production_schedule.company_id,
                            extra_values,
                        )
                    )
                else:
                    for bom_line, qty_ratio in product_ratio:
                        procurements.append(
                            self.env["procurement.group"].Procurement(
                                bom_line.product_id,
                                quantity * qty_ratio,
                                bom_line.product_uom_id,
                                production_schedule.warehouse_id.lot_stock_id,
                                bom_line.product_id.name,
                                "MPS",
                                production_schedule.company_id,
                                extra_values,
                            )
                        )

                if existing_forecasts:
                    forecasts_to_set_as_launched |= existing_forecasts
                else:
                    forecasts_values.append(
                        {
                            "forecast_qty": 0,
                            "date": forecast["date_stop"],
                            "procurement_launched": True,
                            "production_schedule_id": production_schedule.id,
                        }
                    )

        if procurements:
            self.env["procurement.group"].with_context(
                skip_lead_time=True
            ).run(procurements)

        forecasts_to_set_as_launched.write({"procurement_launched": True})
        if forecasts_values:
            self.env["mrp.product.forecast"].create(forecasts_values)

    def _get_mps_week_name(self, date_start, date_stop):
        period = self.env.company.manufacturing_period
        if period == "week":
            return _(
                "Week %(week_num)s (%(start_date)s-%(end_date)s/%(month)s)",
                week_num=format_date(self.env, date_start, date_format="w"),
                start_date=format_date(self.env, date_start, date_format="d"),
                end_date=format_date(self.env, date_stop, date_format="d"),
                month=format_date(self.env, date_stop, date_format="MMM"),
            )
        elif period == "month":
            return format_date(self.env, date_start, date_format="MMM yyyy")
        elif period == "day":
            return format_date(self.env, date_start, date_format="MMM d")
        else:
            return format_date(self.env, date_start, date_format="yyyy")
