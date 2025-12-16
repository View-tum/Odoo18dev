# -*- coding: utf-8 -*-
from odoo import api, fields, models


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        string="Currency",
        readonly=True,
    )
    employee_cost_total = fields.Monetary(
        string="Employee Cost (Real)",
        currency_field="currency_id",
        compute="_compute_employee_cost_total",
        store=True,
        help="Total direct labor cost computed by merging overlapping time logs per employee.",
    )
    employee_cost_line_ids = fields.One2many(
        "mrp.production.employee.cost.line",
        "production_id",
        string="Employee Cost Breakdown",
        readonly=True,
        copy=False,
    )
    labor_move_id = fields.Many2one(
        "account.move",
        string="Labor Journal Entry",
        readonly=True,
        copy=False,
    )

    @api.depends(
        "workorder_ids.time_ids.date_start",
        "workorder_ids.time_ids.date_end",
        "workorder_ids.time_ids.employee_id",
        "workorder_ids.operation_id.parallel_mode",
        "workorder_ids.workcenter_id.employee_costs_hour",
        "state",
    )
    def _compute_employee_cost_total(self):
        Productivity = self.env["mrp.workcenter.productivity"]

        for production in self:
            commands = [(5, 0, 0)]
            lines = Productivity.search(
                [
                    ("workorder_id.production_id", "=", production.id),
                    ("employee_id", "!=", False),
                    ("date_start", "!=", False),
                    ("date_end", "!=", False),
                ]
            )

            if not lines:
                production.employee_cost_total = 0.0
                production.employee_cost_line_ids = commands
                continue

            total_cost = 0.0

            for employee in lines.mapped("employee_id"):
                emp_lines = lines.filtered(lambda l, emp=employee: l.employee_id == emp)
                intervals = sorted(
                    [
                        (l.date_start, l.date_end)
                        for l in emp_lines
                        if l.date_end and l.date_end > l.date_start
                    ],
                    key=lambda pair: pair[0],
                )
                if not intervals:
                    continue

                merged = []
                current_start, current_end = intervals[0]
                for next_start, next_end in intervals[1:]:
                    if next_start <= current_end:
                        current_end = max(current_end, next_end)
                    else:
                        merged.append((current_start, current_end))
                        current_start, current_end = next_start, next_end
                merged.append((current_start, current_end))

                total_seconds = sum(
                    (end - start).total_seconds() for start, end in merged
                )
                hours = total_seconds / 3600.0

                workcenters = emp_lines.mapped("workorder_id.workcenter_id")
                wc_rates = [
                    getattr(wc, "employee_costs_hour", 0.0)
                    for wc in workcenters
                    if getattr(wc, "employee_costs_hour", 0.0)
                ]
                hourly_cost = max(wc_rates) if wc_rates else 0.0
                if not hourly_cost:
                    hourly_cost = getattr(employee, "hourly_cost", 0.0) or getattr(
                        employee, "timesheet_cost", 0.0
                    )

                cost = hours * hourly_cost
                total_cost += cost

                commands.append(
                    (
                        0,
                        0,
                        {
                            "employee_id": employee.id,
                            "duration_hours": hours,
                            "hourly_rate": hourly_cost,
                            "cost": cost,
                        },
                    )
                )

            production.employee_cost_total = total_cost
            production.employee_cost_line_ids = commands

    def _create_labor_cost_move(self):
        Move = self.env["account.move"]
        Journal = self.env["account.journal"]
        ValuationLayer = self.env["stock.valuation.layer"]

        for mo in self:
            if mo.labor_move_id or mo.employee_cost_total <= 0:
                continue

            workcenters = mo.workorder_ids.mapped("workcenter_id")
            expense_account = workcenters.filtered("expense_account_id")[:1].expense_account_id
            product_accounts = mo.product_id.product_tmpl_id.get_product_accounts()
            debit_account = self._get_wip_debit_account(mo, product_accounts)

            journal = Journal.search(
                [("code", "=", "STJ"), ("company_id", "=", mo.company_id.id)],
                limit=1,
            )
            if not journal:
                journal = Journal.search(
                    [("code", "=", "DL"), ("company_id", "=", mo.company_id.id)],
                    limit=1,
                )
            if not journal:
                journal = Journal.search(
                    [("type", "=", "general"), ("company_id", "=", mo.company_id.id)],
                    limit=1,
                )

            if not expense_account or not debit_account or not journal:
                continue

            # หา finished_move ก่อน เพื่อป้องกันการลงบัญชีแต่ไม่มีของให้เพิ่มมูลค่า
            finished_move = mo.move_finished_ids.filtered(
                lambda m: m.state == "done" and m.product_id == mo.product_id
            )[:1]
            if not finished_move:
                finished_move = mo.move_finished_ids.filtered(
                    lambda m: m.state != "cancel" and m.product_id == mo.product_id
                )[:1]

            if not finished_move:
                continue

            ref_name = f"{mo.name} - Employee Cost"
            amount = mo.employee_cost_total

            move_vals = {
                "journal_id": journal.id,
                "date": fields.Date.context_today(mo),
                "ref": ref_name,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": ref_name,
                            "account_id": debit_account.id,
                            "sequence": 10,
                            "debit": amount,
                            "credit": 0.0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": ref_name,
                            "account_id": expense_account.id,
                            "sequence": 20,
                            "debit": 0.0,
                            "credit": amount,
                        },
                    ),
                ],
            }

            move = Move.create(move_vals)
            move.action_post()
            mo.labor_move_id = move.id

            if finished_move:
                ValuationLayer.sudo().create(
                    {
                        "company_id": mo.company_id.id,
                        "product_id": mo.product_id.id,
                        "stock_move_id": finished_move.id,
                        "account_move_id": move.id,
                        "quantity": 0.0,
                        "value": amount,
                        "description": ref_name,
                    }
                )

    @staticmethod
    def _get_wip_debit_account(mo, product_accounts):
        production_locations = []
        production_locations += [
            loc
            for loc in mo.move_raw_ids.mapped("location_dest_id")
            if loc.usage == "production"
        ]
        production_locations += [
            loc
            for loc in mo.move_finished_ids.mapped("location_id")
            if loc.usage == "production"
        ]
        production_location = production_locations[0] if production_locations else False

        if production_location:
            account = (
                production_location.valuation_in_account_id
                or production_location.valuation_out_account_id
            )
            if account:
                return account

        return (
            product_accounts.get("production")
            or product_accounts.get("stock_valuation")
            or product_accounts.get("stock_output")
        )

    def button_mark_done(self):
        self._compute_employee_cost_total()
        res = super().button_mark_done()
        self._create_labor_cost_move()
        return res

    def _post_labour(self):
        """
        Override to rename 'Labour' to 'Overhead' in the generated journal entry.
        This is safer than copy-pasting the entire method.
        """
        # 1. Let Odoo create the standard 'Labour' entry
        super()._post_labour()

        # 2. Find and rename it to 'Overhead'
        # Note: We use _() to match the translation if any, but we force 'Overhead' in English.
        for mo in self:
            # Reconstruct the Ref that Odoo just created
            # Odoo code: desc = _('%s - Labour', mo.name)
            # We need to match exactly what Odoo generated (including translation)
            # But since we want to change it, we search for the 'Labour' one.

            # Warning: If the system language is not English, _('... - Labour') might return Thai.
            # We assume we want to change whatever Odoo generated.

            # To be safe, we search for the move created today with the MO name in Ref.
            # Since _post_labour doesn't link the move to MO, we have to search.

            # Construct the search domain
            # We search for moves where ref starts with MO name and contains "Labour" (or translated equivalent)
            # But simpler is to just search for the exact string Odoo uses.
            from odoo import _

            labour_ref = _('%s - Labour', mo.name)

            moves = self.env["account.move"].search(
                [
                    ("ref", "=", labour_ref),
                    ("date", "=", fields.Date.context_today(mo)),
                    ("journal_id.type", "in", ["general", "sale", "purchase"]),  # Optimization
                    ("company_id", "=", mo.company_id.id),
                ]
            )

            if moves:
                new_ref = _('%s - Overhead', mo.name)
                # Update the move header
                moves.write({"ref": new_ref})
                # Update the move lines (Label)
                moves.mapped("line_ids").write({"name": new_ref})


class MrpProductionEmployeeCostLine(models.Model):
    _name = "mrp.production.employee.cost.line"
    _description = "Employee Labor Cost per MO"
    _order = "cost desc"

    production_id = fields.Many2one("mrp.production", ondelete="cascade")
    employee_id = fields.Many2one("hr.employee", string="Employee")
    duration_hours = fields.Float(string="Real Hours", digits=(16, 4))
    hourly_rate = fields.Monetary(
        string="Rate/Hr",
        currency_field="currency_id",
    )
    cost = fields.Monetary(string="Total Cost", currency_field="currency_id")
    currency_id = fields.Many2one(
        "res.currency",
        related="production_id.currency_id",
        store=True,
        readonly=True,
    )
