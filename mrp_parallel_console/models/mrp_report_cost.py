# -*- coding: utf-8 -*-
from odoo import api, models


class MrpCostStructure(models.AbstractModel):
    _inherit = "report.mrp_account_enterprise.mrp_cost_structure"

    @api.model
    def get_lines(self, productions):
        lines = super().get_lines(productions)
        Production = self.env["mrp.production"]

        for line in lines:
            mo = Production.browse(line.get("id"))
            if not mo:
                continue

            raw_operations = list(line.get("operations") or [])
            raw_ops_total = sum(op.get("total_cost", 0.0) for op in raw_operations)

            grouped_ops = {}
            for op in raw_operations:
                key = op.get("name")
                if key in grouped_ops:
                    grouped_ops[key]["time"] += op.get("time", 0.0)
                    grouped_ops[key]["total_cost"] += op.get("total_cost", 0.0)
                else:
                    grouped_ops[key] = op.copy()
            line["operations"] = list(grouped_ops.values())

            labors = [
                {
                    "name": cost_line.employee_id.display_name,
                    "time": cost_line.duration_hours,
                    "cost_hourly": cost_line.hourly_rate,
                    "total_cost": cost_line.cost,
                }
                for cost_line in mo.employee_cost_line_ids
            ]
            line["labors"] = labors

            total_machine_cost = sum(op.get("total_cost", 0.0) for op in line["operations"])
            total_labor_cost = sum(entry["total_cost"] for entry in labors)
            material_cost = line.get("total_cost", 0.0) - raw_ops_total
            line["total_cost"] = material_cost + total_machine_cost + total_labor_cost

        return lines
