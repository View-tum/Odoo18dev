# -*- coding: utf-8 -*-
from odoo import api, models


class MrpCostStructure(models.AbstractModel):
    _inherit = "report.mrp_account_enterprise.mrp_cost_structure"

    @api.model
    def get_lines(self, productions):
        lines = super().get_lines(productions)
        Production = self.env["mrp.production"]

        for line in lines:
            # Match MOs for that product (standard report aggregates by product)
            mos = productions.filtered(lambda m: m.product_id == line.get("product"))

            # Aggregate operations to remove duplicates if needed, though standard already does some.
            # But here we focus on Labors.

            raw_operations = list(line.get("operations") or [])

            # Helper to extract properly
            def get_op_data(op):
                # Standard: [wc_name, op_id, wo_name, duration, cost]
                if isinstance(op, list):
                    return {"name": op[0], "time": op[3], "total_cost": op[4]}
                # Custom/Already processed: Dict
                return op

            processed_ops = [get_op_data(op) for op in raw_operations]
            raw_ops_total = sum(op.get("total_cost", 0.0) for op in processed_ops)

            grouped_ops = {}
            for op in processed_ops:
                key = op.get("name")
                if key in grouped_ops:
                    grouped_ops[key]["time"] += op.get("time", 0.0)
                    grouped_ops[key]["total_cost"] += op.get("total_cost", 0.0)
                else:
                    grouped_ops[key] = op.copy()
            line["operations"] = list(grouped_ops.values())

            # Collect labor costs from ALL matching MOs
            labors = []
            for mo in mos:
                labors.extend(
                    [
                        {
                            "name": cost_line.employee_id.display_name,
                            "time": cost_line.duration_hours,
                            "cost_hourly": cost_line.hourly_rate,
                            "total_cost": cost_line.cost,
                        }
                        for cost_line in mo.employee_cost_line_ids
                    ]
                )
            line["labors"] = labors

            total_machine_cost = sum(
                op.get("total_cost", 0.0) for op in line["operations"]
            )
            total_labor_cost = sum(entry["total_cost"] for entry in labors)
            material_cost = line.get("total_cost", 0.0) - raw_ops_total
            line["total_cost"] = material_cost + total_machine_cost + total_labor_cost

        return lines
