# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo import tools


class MrpEmployeeCostAnalysis(models.Model):
    _name = "mrp.employee.cost.analysis"
    _description = "Employee Cost Analysis (Merged Parallel Work)"
    _auto = False
    _order = "date desc, employee_id"

    employee_id = fields.Many2one("hr.employee", string="Employee", readonly=True)
    date = fields.Date(string="Date", readonly=True)
    total_hours = fields.Float(string="Total Hours (Merged)", readonly=True)
    total_cost = fields.Monetary(
        string="Total Cost", currency_field="currency_id", readonly=True
    )
    currency_id = fields.Many2one("res.currency", string="Currency", readonly=True)
    workcenter_id = fields.Many2one("mrp.workcenter", string="Work Center", readonly=True)
    operation_id = fields.Many2one("mrp.routing.workcenter", string="Operation", readonly=True)

    def init(self):
        """
        Keep a lightweight SQL view so Odoo registry does not warn
        "Model ... has no table" for this _auto = False model.
        Real report rows are still provided by search_read/read_group.
        """
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute(
            f"""
            CREATE VIEW {self._table} AS (
                SELECT
                    0::bigint AS id,
                    NULL::integer AS employee_id,
                    NULL::date AS date,
                    0::double precision AS total_hours,
                    0::numeric AS total_cost,
                    NULL::integer AS currency_id,
                    NULL::integer AS workcenter_id,
                    NULL::integer AS operation_id
                WHERE FALSE
            )
            """
        )

    @api.model
    def _get_merged_data(self, date_from=False, date_to=False, employee_ids=False):
        """
        Core logic to fetch productivity logs and merge them globally.
        This provides the 'Payroll' scale view of employee time.
        """
        domain = [
            ("employee_id", "!=", False),
            ("date_start", "!=", False),
            ("date_end", "!=", False),
        ]
        if date_from:
            domain.append(("date_start", ">=", date_from))
        if date_to:
            domain.append(("date_start", "<=", date_to))
        if employee_ids:
            domain.append(("employee_id", "in", employee_ids))

        logs = self.env["mrp.workcenter.productivity"].search(domain)
        if not logs:
            return []

        # Group by Date and Employee
        data_by_key = {}  # (date, employee_id) -> [intervals]

        for log in logs:
            log_date = log.date_start.date()
            # Group by Date, Employee, and Workcenter/Operation for the global scale
            key = (log_date, log.employee_id, log.workcenter_id, log.workorder_id.operation_id)
            if key not in data_by_key:
                data_by_key[key] = {"intervals": [], "rates": []}

            if log.date_end > log.date_start:
                data_by_key[key]["intervals"].append((log.date_start, log.date_end))
                # Get rate from WC or Employee with fallbacks
                rate = (
                    getattr(log.workcenter_id, "employee_costs_hour", 0.0)
                    or getattr(
                        log.workorder_id.workcenter_id, "employee_costs_hour", 0.0
                    )
                    or getattr(log.workcenter_id, "costs_hour", 0.0)
                    or getattr(log.employee_id, "hourly_cost", 0.0)
                    or getattr(log.employee_id, "timesheet_cost", 0.0)
                )
                data_by_key[key]["rates"].append(rate)
                data_by_key[key]["workcenter_id"] = log.workcenter_id.id
                data_by_key[key]["operation_id"] = log.workorder_id.operation_id.id

        results = []
        for key, info in data_by_key.items():
            log_date, employee, _, _ = key
            intervals = sorted(info["intervals"], key=lambda x: x[0])
            if not intervals:
                continue

            merged = []
            curr_start, curr_end = intervals[0]
            for nxt_start, nxt_end in intervals[1:]:
                if nxt_start <= curr_end:
                    curr_end = max(curr_end, nxt_end)
                else:
                    merged.append((curr_start, curr_end))
                    curr_start, curr_end = nxt_start, nxt_end
            merged.append((curr_start, curr_end))

            log_date, employee, wc_id, op_id = key
            total_seconds = sum((end - start).total_seconds() for start, end in merged)
            hours = total_seconds / 3600.0

            # Use max rate found for that day/employee
            hourly_rate = max(info["rates"]) if info["rates"] else 0.0

            results.append(
                {
                    "employee_id": employee.id,
                    "date": log_date,
                    "workcenter_id": info.get("workcenter_id", False),
                    "operation_id": info.get("operation_id", False),
                    "total_hours": hours,
                    "total_cost": hours * hourly_rate,
                    "currency_id": self.env.company.currency_id.id,
                }
            )

        return results

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        """
        Override search_read to return computed data.
        Since this is an 'Analysis' view, it's easier to mock the records.
        """
        # For a truly robust report, we'd usually use a stored table refreshed by a cron or action.
        # But for limited scale, we can compute on the fly.
        data = self._get_merged_data()

        # Simple mocking for the list view
        mock_records = []
        for i, row in enumerate(data):
            row["id"] = i + 1
            mock_records.append(row)

        # TODO: Apply domain/limit/offset if needed for large datasets
        return mock_records

    @api.model
    def read_group(
        self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True
    ):
        """
        Override read_group to support Pivot/Graph views.
        """
        data = self._get_merged_data()

        if not groupby:
            return []

        # Basic aggregation logic for Pivot
        gb = (
            groupby[0].split(":")[0]
            if isinstance(groupby, list)
            else groupby.split(":")[0]
        )

        groups = {}
        for row in data:
            val = row.get(gb)
            if hasattr(val, "id"):  # Many2one
                val = (val.id, val.display_name)

            if val not in groups:
                groups[val] = {
                    "__count": 0,
                    "total_hours": 0.0,
                    "total_cost": 0.0,
                }
            groups[val]["__count"] += 1
            groups[val]["total_hours"] += row["total_hours"]
            groups[val]["total_cost"] += row["total_cost"]

        res = []
        for val, stats in groups.items():
            stats[gb] = val
            res.append(stats)

        return res
