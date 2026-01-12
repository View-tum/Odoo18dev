# -*- coding: utf-8 -*-
from odoo import api, models

class MrpCostStructure(models.AbstractModel):
    _inherit = "report.mrp_account_enterprise.mrp_cost_structure"

    @api.model
    def get_lines(self, productions):
        lines = super().get_lines(productions)

        for line in lines:
            molds = []
            # base groups by product; match MOs for that product
            mos = productions.filtered(lambda m: m.product_id == line.get("product"))
            for wo in self.env["mrp.workorder"].search([("production_id", "in", mos.ids)]):
                if not wo.mold_ids:
                    continue
                duration_hour = (wo.duration or wo.duration_expected or 0.0) / 60.0
                for mold in wo.mold_ids:
                    cost_per_hour = mold.mold_cost_hour or 0.0
                    total_cost = duration_hour * cost_per_hour
                    molds.append(
                        {
                            "name": mold.name,
                            "time": duration_hour,
                            "cost_hourly": cost_per_hour,
                            "total_cost": total_cost,
                        }
                    )

            line["molds"] = molds
            total_mold_cost = sum(m["total_cost"] for m in molds)
            line["total_cost_molds"] = total_mold_cost
            line["total_cost"] += total_mold_cost

        return lines
