# account_accrual_wizard/models/account_accrual.py
import logging
from datetime import date

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ResCompany(models.Model):
    _inherit = "res.company"

    accrual_tolerance = fields.Float(
        string="Accrual Match Tolerance",
        help="Maximum difference allowed when auto-matching vendor bills with accruals.",
        default=0.0,
    )


class AccountAccrual(models.Model):
    _name = "account.accrual"
    _description = "Accrual Record"
    _order = "date desc, id desc"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    # HEADER
    name = fields.Char(
        string="Sequence",
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _("New"),
    )

    description = fields.Char(string="Description", required=True, tracking=True)

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        tracking=True,
    )
    # ... (fields kept same) ...

    @api.model
    def create(self, vals):
        if vals.get("name", _("New")) == _("New"):
            vals["name"] = self.env["ir.sequence"].next_by_code("account.accrual") or _(
                "New"
            )
        return super().create(vals)

    date = fields.Date(
        string="Accrual Date",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    period_start = fields.Date(string="Period Start")
    period_end = fields.Date(string="Period End")

    # Optional global account (fallback), but we prefer product's account
    accrual_account_id = fields.Many2one(
        "account.account",
        string="Header Accrual Account",
        required=False,  # made optional
        domain=[("deprecated", "=", False)],
        help="Fallback account if product doesn't specify one.",
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )

    journal_id = fields.Many2one(
        "account.journal",
        string="Journal",
        required=True,
        domain="[('type', '=', 'general')]",
        default=lambda self: self._get_default_journal(),
        help="Journal used for the generated entries.",
    )

    # LINES
    line_ids = fields.One2many(
        "account.accrual.line",
        "accrual_id",
        string="Accrual Lines",
    )

    # STATUS / TOTALS
    amount_total = fields.Monetary(
        string="Total Accrued Amount",
        currency_field="currency_id",
        compute="_compute_amount_total",
        store=True,
    )
    # ... (rest of fields maintained) ...
    amount_open = fields.Monetary(
        string="Open Amount",
        currency_field="currency_id",
        compute="_compute_amount_open",
        store=True,
    )
    days_outstanding = fields.Integer(
        string="Days Outstanding",
        compute="_compute_days_outstanding",
        store=True,
    )

    move_id = fields.Many2one(
        "account.move",
        string="Accrual Journal Entry",
        readonly=True,
    )
    reverse_move_id = fields.Many2one(
        "account.move",
        string="Reverse Journal Entry",
        readonly=True,
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("posted", "Posted"),
            ("reversed", "Reversed"),
        ],
        string="Status",
        default="draft",
        tracking=True,
    )

    # ATTACHMENTS
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "account_accrual_attachment_rel",
        "accrual_id",
        "attachment_id",
        string="Supporting Documents",
    )

    # SMART BUTTONS
    matched_bill_ids = fields.Many2many(
        "account.move",
        string="Matched Vendor Bills",
        domain=[("move_type", "=", "in_invoice")],
        copy=False,
    )
    entry_count = fields.Integer(compute="_compute_counts")
    bill_count = fields.Integer(compute="_compute_counts")

    @api.depends("move_id", "reverse_move_id", "matched_bill_ids")
    def _compute_counts(self):
        for rec in self:
            entries = self.env["account.move"]
            if rec.move_id:
                entries += rec.move_id
            if rec.reverse_move_id:
                entries += rec.reverse_move_id
            rec.entry_count = len(entries)
            rec.bill_count = len(rec.matched_bill_ids)

    def action_view_entries(self):
        self.ensure_one()
        entries = self.env["account.move"]
        if self.move_id:
            entries += self.move_id
        if self.reverse_move_id:
            entries += self.reverse_move_id

        action = self.env["ir.actions.act_window"]._for_xml_id(
            "account.action_move_journal_line"
        )
        if len(entries) > 1:
            action["domain"] = [("id", "in", entries.ids)]
        elif len(entries) == 1:
            form_view = [(self.env.ref("account.view_move_form").id, "form")]
            if "views" in action:
                action["views"] = form_view + [
                    (v, k) for v, k in action["views"] if k != "form"
                ]
            else:
                action["views"] = form_view
            action["res_id"] = entries.id
        else:
            action = {"type": "ir.actions.act_window_close"}

        action["context"] = dict(self.env.context, create=False)
        return action

    def action_view_bills(self):
        self.ensure_one()
        bills = self.matched_bill_ids
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "account.action_move_in_invoice_type"
        )
        if len(bills) > 1:
            action["domain"] = [("id", "in", bills.ids)]
        elif len(bills) == 1:
            form_view = [(self.env.ref("account.view_move_form").id, "form")]
            if "views" in action:
                action["views"] = form_view + [
                    (v, k) for v, k in action["views"] if k != "form"
                ]
            else:
                action["views"] = form_view
            action["res_id"] = bills.id
        else:
            action = {"type": "ir.actions.act_window_close"}

        action["context"] = dict(self.env.context, create=False)
        return action

    # ------------------------------------------------------------
    # COMPUTE
    # ------------------------------------------------------------
    @api.depends("line_ids.amount")
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = sum(rec.line_ids.mapped("amount"))

    @api.depends("amount_total", "reverse_move_id", "reverse_move_id.state")
    def _compute_amount_open(self):
        for rec in self:
            if rec.reverse_move_id and rec.reverse_move_id.state == "posted":
                rec.amount_open = 0.0
            else:
                rec.amount_open = rec.amount_total or 0.0

    @api.depends("date", "state")
    def _compute_days_outstanding(self):
        today = date.today()
        for rec in self:
            if rec.state == "posted" and rec.date:
                rec.days_outstanding = (today - rec.date).days
            else:
                rec.days_outstanding = 0

    # ------------------------------------------------------------
    # ACTIONS
    # ------------------------------------------------------------
    def action_post(self):
        """Create and post accrual journal entry."""
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Only draft accruals can be posted."))

            if not rec.line_ids:
                raise UserError(_("Please add at least one accrual line."))

            move_vals = rec._prepare_move_vals()
            move = self.env["account.move"].create(move_vals)
            move.action_post()

            rec.move_id = move
            rec.state = "posted"
            rec.message_post(
                body=_("Accrual posted with journal entry %s.") % move.display_name
            )
        return True

    def _prepare_move_vals(self):
        self.ensure_one()
        # No longer check self.accrual_account_id strictly here, check per line/group

        company = self.company_id
        move_lines = []

        # Debit: one line per accrual line (Expense)
        # Credit: grouped by Product's Accrual Account
        credit_groups = {}  # {account_id: amount}

        for line in self.line_ids:
            if not line.expense_account_id:
                raise UserError(
                    _("Please set an Expense Account on line '%s'.")
                    % (line.name or "/")
                )
            if not line.amount:
                continue

            # Debit Line
            move_lines.append(
                (
                    0,
                    0,
                    {
                        "name": line.name or self.name,
                        "account_id": line.expense_account_id.id,
                        "debit": line.amount if line.amount > 0 else 0.0,
                        "credit": 0.0,
                        "analytic_distribution": {str(line.analytic_account_id.id): 100}
                        if line.analytic_account_id
                        else False,
                        "partner_id": line.partner_id.id or False,
                        "product_id": line.product_id.id or False,
                        "company_id": company.id,
                    },
                )
            )

            # Determine Credit Account
            credit_acc = False
            if line.product_id:
                credit_acc = line.product_id.property_account_accrual_id
                if not credit_acc and line.product_id.categ_id:
                    credit_acc = line.product_id.categ_id.property_account_accrual_id

            if not credit_acc:
                credit_acc = self.accrual_account_id

            if not credit_acc:
                raise UserError(
                    _(
                        "No Accrual Account found for product '%s' and no header account set."
                    )
                    % (
                        line.product_id.display_name
                        if line.product_id
                        else "No Product"
                    )
                )

            if credit_acc.id not in credit_groups:
                credit_groups[credit_acc.id] = 0.0
            credit_groups[credit_acc.id] += line.amount

        if not move_lines:
            raise UserError(_("No debit lines to create for this accrual."))

        # Create Credit Lines (Grouped)
        for acc_id, amount in credit_groups.items():
            move_lines.append(
                (
                    0,
                    0,
                    {
                        "name": self.name + " (Accrual Reversal)",
                        "account_id": acc_id,
                        "debit": 0.0,
                        "credit": amount,
                        "partner_id": False,
                        "company_id": company.id,
                    },
                )
            )

        move_vals = {
            "ref": self.name,
            "date": self.date,
            "journal_id": self.journal_id.id,
            "company_id": company.id,
            "line_ids": move_lines,
        }
        return move_vals

    def _get_default_journal(self):
        company = self.company_id or self.env.company
        # Priority 1: Journal with code 'ACCR'
        journal = self.env["account.journal"].search(
            [
                ("code", "=", "ACCR"),
                ("type", "=", "general"),
                ("company_id", "=", company.id),
            ],
            limit=1,
        )
        if journal:
            return journal

        # Priority 2: First General Journal
        journal = self.env["account.journal"].search(
            [("type", "=", "general"), ("company_id", "=", company.id)],
            limit=1,
        )
        if not journal:
            # Fallback (rare)
            return self.env["account.journal"]

        return journal

    def action_reverse(self):
        """Reverse the whole accrual (full document)."""
        for rec in self:
            if rec.state != "posted":
                raise UserError(_("Only posted accruals can be reversed."))
            if not rec.move_id or rec.move_id.state != "posted":
                raise UserError(_("Accrual journal entry must be posted."))

            reversal_move = rec._create_reversal_move()
            reversal_move.action_post()
            rec.reverse_move_id = reversal_move
            rec.state = "reversed"
            rec.message_post(
                body=_("Accrual reversed by journal entry %s.")
                % reversal_move.display_name
            )
        return True

    def _create_reversal_move(self):
        self.ensure_one()
        move = self.move_id
        reversal_vals = {
            "ref": _("%s (Reversal)") % (move.ref or self.name),
            "date": fields.Date.context_today(self),
            "journal_id": move.journal_id.id,
            "company_id": move.company_id.id,
            "line_ids": [],
        }
        line_vals = []
        for line in move.line_ids:
            line_vals.append(
                (
                    0,
                    0,
                    {
                        "name": line.name,
                        "account_id": line.account_id.id,
                        "debit": line.credit,
                        "credit": line.debit,
                        "analytic_distribution": line.analytic_distribution,
                        "partner_id": line.partner_id.id or False,
                        "company_id": line.company_id.id,
                    },
                )
            )
        reversal_vals["line_ids"] = line_vals
        reversal_move = self.env["account.move"].create(reversal_vals)
        return reversal_move

    @api.model
    def _cron_auto_reverse(self):
        """
        Scheduled Action to reverse accruals that have reached their Period End date.
        """
        today = fields.Date.context_today(self)
        accruals = self.search(
            [
                ("state", "=", "posted"),
                ("reverse_move_id", "=", False),  # Not yet reversed
                ("period_end", "!=", False),
                ("period_end", "<=", today),  # Date reached or passed
            ]
        )

        for accrual in accruals:
            try:
                accrual.action_reverse()
                _logger = logging.getLogger(__name__)
                _logger.info(
                    "Auto-reversed Accrual %s (Period End: %s)",
                    accrual.name,
                    accrual.period_end,
                )
            except Exception as e:
                # Log but don't stop the cron for other records
                _logger = logging.getLogger(__name__)
                _logger.error(
                    "Failed to auto-reverse Accrual %s: %s", accrual.name, str(e)
                )

    # ------------------------------------------------------------
    # AUTO MATCHING LOGIC
    # ------------------------------------------------------------
    @api.model
    def _auto_match_accrual_for_bill(self, move):
        """
        Called when a Vendor Bill (in_invoice) is posted.
        Logic:
        1. Find all Posted Accruals (not yet reversed).
        2. Match Bill Lines with Accrual Lines based on Product.
        3. If matched, we can Log a note or Auto-Reverse.

        Current Implementation:
        - Strict matching: Same Product
        - If bill has product X, check if any open accrual line has product X.
        - If found, Log activity on the Accrual.
        - OPTIONAL: Auto-reverse if configured (future).
        """
        if not move.line_ids or move.move_type != "in_invoice":
            return

        # Group Bill Lines by Product
        bill_products = move.invoice_line_ids.mapped("product_id")
        if not bill_products:
            return

        # Find Posted Accruals matching these products
        # We search for lines first
        AccrualLine = self.env["account.accrual.line"]
        matched_lines = AccrualLine.search(
            [
                ("accrual_id.state", "=", "posted"),
                ("accrual_id.company_id", "=", move.company_id.id),
                ("product_id", "in", bill_products.ids),
                ("accrual_id.reverse_move_id", "=", False),  # Not yet reversed
            ]
        )

        accruals = matched_lines.mapped("accrual_id")

        for accrual in accruals:
            # Check if this specific bill matches roughly (by product overlap)
            common_products = [
                p for p in bill_products if p in accrual.line_ids.mapped("product_id")
            ]
            if common_products:
                # Log Activity
                msg = _(
                    "Vendor Bill %s posted containing products in this accrual: %s. Please check if reversal is needed."
                ) % (move.display_name, ", ".join([p.name for p in common_products]))
                accrual.activity_schedule(
                    "mail.mail_activity_data_todo", note=msg, user_id=self.env.user.id
                )
                accrual.message_post(body=msg)

                # [NEW] Link the bill
                accrual.matched_bill_ids = [(4, move.id)]


class AccountAccrualLine(models.Model):
    _name = "account.accrual.line"
    _description = "Accrual Line (SO-style)"

    accrual_id = fields.Many2one(
        "account.accrual",
        string="Accrual",
        required=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        related="accrual_id.company_id",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        related="accrual_id.currency_id",
        store=True,
        readonly=True,
    )

    # [NEW] Product centric
    product_id = fields.Many2one(
        "product.product",
        string="Product",
        required=True,  # Enforce product usage
    )

    partner_id = fields.Many2one(
        "res.partner",
        string="Vendor",
    )
    name = fields.Char(
        string="Description",
        help="Description for this accrual line.",
    )
    expense_account_id = fields.Many2one(
        "account.account",
        string="Expense Account",
        domain=[("deprecated", "=", False)],
        compute="_compute_expense_account_id",
        store=True,
        readonly=False,
        required=True,
    )
    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Analytic Account / Cost Center",
    )

    amount = fields.Monetary(
        string="Amount",
        currency_field="currency_id",
    )

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.display_name
            # Default Expense account
            self.expense_account_id = (
                self.product_id.property_account_expense_id
                or self.product_id.categ_id.property_account_expense_categ_id
            )

    @api.depends("product_id")
    def _compute_expense_account_id(self):
        for rec in self:
            if rec.product_id and not rec.expense_account_id:
                rec.expense_account_id = (
                    rec.product_id.property_account_expense_id
                    or rec.product_id.categ_id.property_account_expense_categ_id
                )
