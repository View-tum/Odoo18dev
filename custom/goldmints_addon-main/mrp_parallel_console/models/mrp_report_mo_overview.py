from odoo import models


class ReportMoOverview(models.AbstractModel):
    _inherit = "report.mrp.report_mo_overview"

    def _compute_employee_prorated_cost(self, employee, workorder):
        Productivity = self.env["mrp.workcenter.productivity"]
        logs = Productivity.search([
            ("workorder_id", "=", workorder.id),
            ("employee_id", "=", employee.id),
            ("date_start", "!=", False),
            ("date_end", "!=", False),
        ])
        if not logs:
            return 0.0

        min_start = min(logs.mapped("date_start"))
        max_end = max(logs.mapped("date_end"))

        all_logs = Productivity.search([
            ("employee_id", "=", employee.id),
            ("date_start", "<", max_end),
            ("date_end", ">", min_start),
        ])

        boundaries = set()
        for log in all_logs:
            boundaries.add(log.date_start)
            boundaries.add(log.date_end)

        points = sorted(list(boundaries))
        pro_rated_hours = 0.0
        hourly_rates = []

        for idx in range(len(points) - 1):
            start, end = points[idx], points[idx + 1]

            active_wo = logs.filtered(
                lambda log, s=start, e=end: log.date_start <= s and log.date_end >= e
            )
            if not active_wo:
                continue

            active_all = all_logs.filtered(
                lambda log, s=start, e=end: log.date_start <= s and log.date_end >= e
            )

            n_wo = len(active_wo)
            n_all = len(active_all)

            if n_all > 0:
                weight = n_wo / n_all
                duration = (end - start).total_seconds() / 3600.0
                pro_rated_hours += duration * weight

                for log in active_wo:
                    rate = (
                        getattr(log, "employee_cost", 0.0)
                        or getattr(log.workcenter_id, "employee_costs_hour", 0.0)
                        or getattr(log.workorder_id.workcenter_id, "employee_costs_hour", 0.0)
                        or getattr(employee, "hourly_cost", 0.0)
                        or getattr(employee, "timesheet_cost", 0.0)
                    )
                    if rate:
                        hourly_rates.append(rate)

        hourly_cost = max(hourly_rates) if hourly_rates else 0.0
        return pro_rated_hours * hourly_cost

    def _compute_workorder_employee_cost(self, workorder):
        employees = workorder.time_ids.mapped("employee_id")
        total = 0.0
        for emp in employees:
            if emp:
                total += self._compute_employee_prorated_cost(emp, workorder)
        return total

    def _get_operations_data(self, production, level=0, current_index=False):
        result = super()._get_operations_data(production, level, current_index)

        wo_cost_map = {}
        for wo in production.workorder_ids:
            wo_cost_map[wo.id] = self._compute_workorder_employee_cost(wo)

        total_employee_cost = 0.0
        for op in result.get("details", []):
            if op.get("model") != "mrp.workorder":
                continue
            wo_id = op.get("id")
            if wo_id and wo_id in wo_cost_map:
                emp_cost = wo_cost_map[wo_id]
                op["employee_cost"] = emp_cost
                op["real_cost"] = op.get("real_cost", 0.0) + emp_cost
                total_employee_cost += emp_cost

        if result.get("summary"):
            result["summary"]["employee_cost"] = total_employee_cost
            result["summary"]["real_cost"] = (
                result["summary"].get("real_cost", 0.0) + total_employee_cost
            )

        return result

    def _get_finished_operation_data(self, production, level=0, current_index=False):
        result = super()._get_finished_operation_data(production, level, current_index)

        currency = result.get("summary", {}).get("currency")
        if not currency:
            currency = (production.company_id or self.env.company).currency_id

        emp_cost_map = {}
        for wo in production.workorder_ids:
            for emp in wo.time_ids.mapped("employee_id"):
                if emp:
                    key = (wo.id, emp.id)
                    emp_cost_map[key] = self._compute_employee_prorated_cost(emp, wo)

        total_prorated_adjustment = 0.0
        details = result.get("details", [])

        workorder_list = list(production.workorder_ids)
        for idx, op in enumerate(details):
            index_str = op.get("index", "")

            if "WE" in index_str:
                name = op.get("name", "")
                if ": " in name:
                    emp_name = name.split(": ")[0]
                    wo_display = name.split(": ")[1] if len(name.split(": ")) > 1 else ""

                    matched_wo = None
                    matched_emp = None
                    for wo in production.workorder_ids:
                        if wo.display_name in wo_display or wo_display in wo.display_name:
                            for emp in wo.time_ids.mapped("employee_id"):
                                if emp and emp.display_name == emp_name:
                                    matched_wo = wo
                                    matched_emp = emp
                                    break
                            if matched_wo:
                                break

                    if matched_wo and matched_emp:
                        key = (matched_wo.id, matched_emp.id)
                        prorated_cost = emp_cost_map.get(key, 0.0)
                        original_cost = op.get("real_cost", 0.0)
                        adjustment = prorated_cost - original_cost
                        op["real_cost"] = currency.round(prorated_cost)
                        op["employee_cost"] = currency.round(prorated_cost)
                        total_prorated_adjustment += adjustment
            elif idx < len(workorder_list):
                wo = workorder_list[idx]
                emp_cost = self._compute_workorder_employee_cost(wo)
                op["employee_cost"] = emp_cost
                op["real_cost"] = op.get("real_cost", 0.0) + emp_cost

        if result.get("summary") and total_prorated_adjustment != 0:
            result["summary"]["real_cost"] = currency.round(
                result["summary"].get("real_cost", 0.0) + total_prorated_adjustment
            )
            result["summary"]["employee_cost"] = sum(
                emp_cost_map.values()
            )

        return result
