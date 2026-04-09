# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.tools import format_amount


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
            mo_logs = Productivity.search(
                [
                    ("workorder_id.production_id", "=", production.id),
                    ("employee_id", "!=", False),
                    ("date_start", "!=", False),
                    ("date_end", "!=", False),
                ]
            )

            if not mo_logs:
                production.employee_cost_total = 0.0
                production.employee_cost_line_ids = commands
                continue

            total_cost = 0.0
            commands_map = {}  # (employee_id, workorder_id) -> values

            for employee in mo_logs.mapped("employee_id"):
                emp_mo_logs = mo_logs.filtered(lambda log: log.employee_id == employee)
                if not emp_mo_logs:
                    continue

                min_start = min(emp_mo_logs.mapped("date_start"))
                max_end = max(emp_mo_logs.mapped("date_end"))

                all_logs = Productivity.search(
                    [
                        ("employee_id", "=", employee.id),
                        ("date_start", "<", max_end),
                        ("date_end", ">", min_start),
                    ]
                )

                # Collect all relevant boundaries
                boundaries = set()
                for log in all_logs:
                    boundaries.add(log.date_start)
                    boundaries.add(log.date_end)

                points = sorted(list(boundaries))

                for idx in range(len(points) - 1):
                    start, end = points[idx], points[idx + 1]

                    active_mo_logs = emp_mo_logs.filtered(
                        lambda log: log.date_start <= start and log.date_end >= end
                    )
                    if not active_mo_logs:
                        continue

                    active_all = all_logs.filtered(
                        lambda log: log.date_start <= start and log.date_end >= end
                    )

                    n_mo = len(active_mo_logs)
                    n_all = len(active_all)

                    if n_all > 0:
                        # Weight is shared across all concurrent work by the employee
                        # But further shared equally among concurrent MO logs if multiple
                        total_weight = n_mo / n_all
                        duration = (end - start).total_seconds() / 3600.0
                        prorated_duration = duration * (total_weight / n_mo)

                        for log in active_mo_logs:
                            rate = (
                                getattr(log.workcenter_id, "employee_costs_hour", 0.0)
                                or getattr(
                                    log.workorder_id.workcenter_id,
                                    "employee_costs_hour",
                                    0.0,
                                )
                                or getattr(log.workcenter_id, "costs_hour", 0.0)
                                or getattr(employee, "hourly_cost", 0.0)
                                or getattr(employee, "timesheet_cost", 0.0)
                            )
                            cost = prorated_duration * rate
                            total_cost += cost

                            # We create/update commands based on (employee, workorder)
                            key = (employee.id, log.workorder_id.id)
                            if key not in commands_map:
                                commands_map[key] = {
                                    "employee_id": employee.id,
                                    "workorder_id": log.workorder_id.id,
                                    "workcenter_id": log.workorder_id.workcenter_id.id,
                                    "duration_hours": 0.0,
                                    "hourly_rate": rate,
                                    "cost": 0.0,
                                }
                            commands_map[key]["duration_hours"] += prorated_duration
                            commands_map[key]["cost"] += cost
                            # Keep highest rate if it varies (safety)
                            commands_map[key]["hourly_rate"] = max(commands_map[key]["hourly_rate"], rate)

            production.employee_cost_total = total_cost
            for val in commands_map.values():
                commands.append((0, 0, val))
            production.employee_cost_line_ids = commands

    def _create_labor_cost_move(self):
        Move = self.env["account.move"]
        Journal = self.env["account.journal"]
        ValuationLayer = self.env["stock.valuation.layer"]

        for mo in self:
            if mo.labor_move_id or mo.employee_cost_total <= 0:
                continue

            workcenters = mo.workorder_ids.mapped("workcenter_id")
            expense_account = workcenters.filtered("expense_account_id")[
                :1
            ].expense_account_id
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
        
        for production in self:
            # Check for variance alerts
            actual = production.employee_cost_total
            # Estimated is sum of expected duration * wc cost for all workorders
            estimated = sum(
                (wo.duration_expected / 60.0) * wo.workcenter_id.costs_hour
                for wo in production.workorder_ids
            )
            
            if estimated > 0:
                variance_ratio = (actual - estimated) / estimated
                if abs(variance_ratio) > 0.10: # 10% threshold
                    production._notify_labor_cost_variance(actual, estimated, variance_ratio)
        return res

    def _notify_labor_cost_variance(self, actual, estimated, variance_ratio):
        """
        Notify users in the 'Labor Cost Variance Alerts' group about significant cost deviations.
        """
        self.ensure_one()
        group = self.env.ref("mrp_parallel_console.group_mrp_labor_cost_alerts", raise_if_not_found=False)
        if not group:
            return

        recipients = group.users.partner_id
        if not recipients:
            return

        variance_pct = variance_ratio * 100
        direction = _("Higher than STD") if variance_ratio > 0 else _("Lower than STD")
        
        subject = _("Alert: Labor Cost Variance for MO %s (%s)") % (self.name, direction)
        body = (
            _("<p>Manufacturing Order <b>%s</b> has a labor cost variance from standard:</p>") % self.name +
            "<ul>"
            "<li>" + _("Actual Labor Cost: %s") % format_amount(self.env, actual, self.currency_id) + "</li>"
            "<li>" + _("Standard Labor Cost: %s") % format_amount(self.env, estimated, self.currency_id) + "</li>"
            "<li>" + _("Variance: <b>%+.2f%%</b>") % variance_pct + "</li>"
            "</ul>"
            "<p>" + _("Please review the labor logs for this order.") + "</p>"
        )

        self.message_post(
            body=body,
            subject=subject,
            partner_ids=recipients.ids,
            message_type="notification",
            subtype_xmlid="mail.mt_note",
        )

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

            labour_ref = _("%s - Labour", mo.name)

            moves = self.env["account.move"].search(
                [
                    ("ref", "=", labour_ref),
                    ("date", "=", fields.Date.context_today(mo)),
                    (
                        "journal_id.type",
                        "in",
                        ["general", "sale", "purchase"],
                    ),  # Optimization
                    ("company_id", "=", mo.company_id.id),
                ]
            )

            if moves:
                new_ref = _("%s - Overhead", mo.name)
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
    workorder_id = fields.Many2one("mrp.workorder", string="Operation")
    workcenter_id = fields.Many2one(
        "mrp.workcenter",
        related="workorder_id.workcenter_id",
        string="Work Center",
        store=True,
    )
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
