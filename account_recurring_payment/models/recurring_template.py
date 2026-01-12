from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.fields import Command
from dateutil.relativedelta import relativedelta


class AccountRecurringTemplate(models.Model):
    _name = "account.recurring.template"
    _description = "Recurring Payment Template"

    name = fields.Char(required=True)
    state = fields.Selection([
        ("draft", "Draft"),
        ("running", "Running"),
    ], default="draft")
    journal_id = fields.Many2one(
        "account.journal",
        required=True,
        domain=[("type", "in", ("purchase", "general"))],
    )
    debit_account_id = fields.Many2one("account.account", required=True)
    credit_account_id = fields.Many2one("account.account", required=True)
    partner_id = fields.Many2one("res.partner", required=True, domain=[("supplier_rank", ">", 0)])
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one("res.currency", related="company_id.currency_id", store=True, readonly=True)
    amount = fields.Monetary()
    recurring_period = fields.Selection([
        ("days", "Days"),
        ("weeks", "Weeks"),
        ("months", "Months"),
        ("years", "Years"),
    ])
    recurring_invoicing_type = fields.Selection([
        ("specific_date", "Specific Date"),
        ("first_day", "First Day of Month"),
        ("last_day", "Last Day of Month"),
    ], default="specific_date", string="Invoicing Date")
    recurring_interval = fields.Integer(default=1)
    start_date = fields.Date(required=True)
    end_date = fields.Date()
    next_schedule = fields.Date(compute="_compute_next_schedule", store=True)
    generate_journal_as = fields.Selection([
        ("draft", "Unposted"),
        ("posted", "Posted"),
    ], default="draft")
    recurring_line_ids = fields.One2many("account.recurring.line", "template_id")

    @api.depends("recurring_line_ids.date", "recurring_line_ids.state")
    def _compute_next_schedule(self):
        for template in self:
            pending_dates = template.recurring_line_ids.filtered(lambda l: l.state == "pending").mapped("date")
            template.next_schedule = min(pending_dates) if pending_dates else False

    def _get_delta(self):
        self.ensure_one()
        interval = self.recurring_interval or 1
        if self.recurring_period == "days":
            return relativedelta(days=interval)
        if self.recurring_period == "weeks":
            return relativedelta(weeks=interval)
        if self.recurring_period == "months":
            return relativedelta(months=interval)
        if self.recurring_period == "years":
            return relativedelta(years=interval)
        return relativedelta()

    def action_compute_schedule(self):
        for template in self:
            if not template.recurring_period:
                raise ValidationError("Recurring period is required.")

            pending_to_clear = template.recurring_line_ids.filtered(lambda l: l.state == "pending")
            if pending_to_clear:
                pending_to_clear.unlink()

            today = fields.Date.today()
            start = template.start_date or today
            if start < today:
                start = today

            done_dates = template.recurring_line_ids.filtered(lambda l: l.state == "done").mapped("date")
            if done_dates:
                last_done = max(done_dates)
                if last_done and last_done >= start:
                    start = last_done + template._get_delta()

            delta = template._get_delta()
            dates = []
            current = start
            horizon_count = 24
            while True:
                effective_date = current
                if template.recurring_invoicing_type == 'first_day':
                    effective_date = current.replace(day=1)
                elif template.recurring_invoicing_type == 'last_day':
                    effective_date = current + relativedelta(day=31)

                if template.end_date and effective_date > template.end_date:
                    break
                dates.append(effective_date)
                if template.end_date is None and len(dates) >= horizon_count:
                    break
                current = effective_date + delta

            commands = []
            for dt in dates:
                commands.append(Command.create({
                    "date": dt,
                    "amount": template.amount,
                    "name": template.name,
                    "state": "pending",
                }))

            if commands:
                template.write({"recurring_line_ids": commands})

    def action_set_running(self):
        for template in self:
            has_pending = bool(template.recurring_line_ids.filtered(lambda l: l.state == "pending"))
            if not has_pending:
                raise ValidationError("Compute schedule before starting.")
            template.state = "running"

    def action_set_draft(self):
        self.write({"state": "draft"})

    @api.model
    def _cron_generate_recurring_moves(self):
        today = fields.Date.today()
        templates = self.search([("state", "=", "running")])
        Move = self.env["account.move"]
        for template in templates:
            lines = template.recurring_line_ids.filtered(lambda l: l.state == "pending" and l.date and l.date <= today)
            for line in lines:
                amount = line.amount or 0.0
                move_vals = {
                    "move_type": "in_invoice",
                    "journal_id": template.journal_id.id,
                    "partner_id": template.partner_id.id,
                    "invoice_date": line.date,
                    "ref": line.name or template.name,
                    "invoice_line_ids": [
                        Command.create({
                            "name": line.name or template.name,
                            "account_id": template.debit_account_id.id,
                            "quantity": 1.0,
                            "price_unit": amount,
                        })
                    ],
                }
                move = Move.create(move_vals)
                if template.generate_journal_as == "posted":
                    move.action_post()
                line.write({"state": "done", "move_id": move.id})


class AccountRecurringLine(models.Model):
    _name = "account.recurring.line"
    _description = "Recurring Payment Line"

    template_id = fields.Many2one("account.recurring.template", required=True, ondelete="cascade")
    date = fields.Date(required=True)
    amount = fields.Monetary()
    name = fields.Char()
    state = fields.Selection([
        ("pending", "Pending"),
        ("done", "Done"),
    ], default="pending")
    move_id = fields.Many2one("account.move", readonly=True)
    currency_id = fields.Many2one("res.currency", related="template_id.currency_id", store=True, readonly=True)
    company_id = fields.Many2one("res.company", related="template_id.company_id", store=True, readonly=True)
    state = fields.Selection([
        ("pending", "Pending"),
        ("done", "Done"),
    ], default="pending")
    move_id = fields.Many2one("account.move", readonly=True)
    currency_id = fields.Many2one("res.currency", related="template_id.currency_id", store=True, readonly=True)
    company_id = fields.Many2one("res.company", related="template_id.company_id", store=True, readonly=True)
