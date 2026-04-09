import logging

from odoo import Command, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AdvanceCashLog(models.Model):
    _name = "advance.cash.log"
    _description = "Advance Cash Log"
    _order = "date desc, id desc"
    _inherit = ["mail.thread", "mail.activity.mixin", "analytic.mixin"]

    name = fields.Char("Document Number", default="New", readonly=True)
    date = fields.Date(
        "Date", default=fields.Date.context_today, required=True, tracking=True
    )

    # 1. Transaction Type
    transaction_type = fields.Selection(
        [
            ("payout", "Payout"),
            ("expense", "Clear Advance (Expense)"),
            ("return", "Return Advance"),
        ],
        string="Transaction Type",
        default="payout",
        required=True,
        tracking=True,
    )

    employee_id = fields.Many2one(
        "hr.employee",
        "Employee",
        required=True,
        tracking=True,
        default=lambda self: self.env.user.employee_id,
    )

    description = fields.Char("Description", required=True, tracking=True)

    # Journal & Account Config
    def _default_journal(self):
        if self.env.company.advance_cash_journal_id:
            return self.env.company.advance_cash_journal_id

        configured_journal = self.env["account.journal"].search(
            [("advance_account_id", "!=", False)], limit=1
        )
        if configured_journal:
            return configured_journal
        return self.env["account.journal"].search(
            [("code", "=", "ADV1"), ("type", "=", "general")], limit=1
        ) or self.env["account.journal"].search([("type", "=", "general")], limit=1)

    journal_id = fields.Many2one(
        "account.journal",
        string="Journal",
        required=True,
        default=_default_journal,
        domain=[("type", "in", ["general", "cash"])],
    )

    # Multi-Line Support
    line_ids = fields.One2many("advance.cash.log.line", "log_id", string="Lines")
    amount = fields.Float(
        "Amount", compute="_compute_amount_total", store=True, readonly=False
    )

    @api.depends("line_ids.amount", "transaction_type")
    def _compute_amount_total(self):
        for rec in self:
            if rec.transaction_type == "expense" and rec.line_ids:
                rec.amount = sum(rec.line_ids.mapped("amount"))

    amount_signed = fields.Float(
        "Balance (Signed)", compute="_compute_amount_signed", store=True
    )

    @api.depends("amount", "transaction_type")
    def _compute_amount_signed(self):
        for rec in self:
            if rec.transaction_type == "payout":
                rec.amount_signed = rec.amount
            else:
                rec.amount_signed = -rec.amount

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    analytic_distribution = fields.Json(
        string="Analytic Distribution",
        default=lambda self: self.env.company.advance_cash_analytic_distribution,
    )

    analytic_precision = fields.Integer(
        related="company_id.analytic_precision",
        readonly=True,
    )

    # Split Balance for List View
    amount_posted = fields.Float(
        "Posted Balance", compute="_compute_split_balance", store=True
    )
    amount_pending = fields.Float(
        "Pending Balance", compute="_compute_split_balance", store=True
    )

    @api.depends("amount_signed", "state")
    def _compute_split_balance(self):
        for rec in self:
            if rec.state == "posted":
                rec.amount_posted = rec.amount_signed
                rec.amount_pending = 0.0
            else:
                rec.amount_posted = 0.0
                rec.amount_pending = rec.amount_signed

    current_balance = fields.Float(
        "Current Advance Balance", related="employee_id.advance_balance"
    )

    amount_net = fields.Float("Net Amount", compute="_compute_amount_net", store=True)

    move_id = fields.Many2one("account.move", string="Journal Entry", readonly=True)

    def action_open_journal_entry(self):
        self.ensure_one()
        return {
            "name": "Journal Entry",
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "form",
            "res_id": self.move_id.id,
        }

    def action_sync_employee_balance(self):
        self.ensure_one()
        return self.employee_id.action_sync_balance()

    @api.model
    def create(self, vals):
        if vals.get("name", "New") == "New":
            vals["name"] = (
                self.env["ir.sequence"].next_by_code("easy.advance.cash") or "ADV-LOG"
            )
        return super(AdvanceCashLog, self).create(vals)

    def write(self, vals):
        if not self.env.su:
            protected_fields = [
                "transaction_type",
                "employee_id",
                "date",
                "amount",
                "line_ids",
                "journal_id",
                "description",
            ]
            if any(f in vals for f in protected_fields):
                for rec in self:
                    if rec.state not in ["draft"]:
                        raise UserError(
                            f"Cannot edit {rec.name} in '{rec.state}' state."
                        )
        return super(AdvanceCashLog, self).write(vals)

    def _get_payment_journal_account(
        self, journal, payment_type="outbound", payment_method_line=False
    ):
        self.ensure_one()
        if (
            payment_method_line
            and payment_method_line.journal_id == journal
            and payment_method_line.payment_type == payment_type
            and payment_method_line.payment_account_id
        ):
            return payment_method_line.payment_account_id
        if journal.default_account_id:
            return journal.default_account_id

        method_line = self.env["account.payment.method.line"].search(
            [
                ("journal_id", "=", journal.id),
                ("payment_type", "=", payment_type),
                ("payment_account_id", "!=", False),
            ],
            limit=1,
        )
        if method_line:
            return method_line.payment_account_id
        return False

    @api.depends("amount", "transaction_type")
    def _compute_amount_net(self):
        for rec in self:
            rec.amount_net = rec.amount

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("manager_approved", "Manager Approved"),
            ("approved", "Account Approved"),
            ("posted", "Posted"),
        ],
        default="draft",
        string="Status",
        tracking=True,
    )

    manager_id = fields.Many2one(
        "hr.employee",
        string="Manager",
        tracking=True,
        compute="_compute_manager",
        store=True,
        readonly=False,
    )

    def _get_accountant_domain(self):
        """Return domain to show only users in Accounting groups"""
        group_xml_ids = [
            "account.group_account_invoice",
            "account.group_account_user",
            "account.group_account_manager",
        ]
        group_ids = []
        for xml_id in group_xml_ids:
            group = self.env.ref(xml_id, raise_if_not_found=False)
            if group:
                group_ids.append(group.id)
        return [("groups_id", "in", group_ids)]

    accountant_id = fields.Many2one(
        "res.users",
        string="Accountant",
        tracking=True,
        domain=lambda self: self._get_accountant_domain(),
        help="Accountant user who will perform the final approval",
    )

    @api.depends("employee_id")
    def _compute_manager(self):
        for rec in self:
            rec.manager_id = rec.employee_id.parent_id

    manager_approval_user_id = fields.Many2one(
        "res.users", string="Manager Approved By", readonly=True, copy=False
    )
    manager_approval_date = fields.Datetime(
        string="Manager Approved On", readonly=True, copy=False
    )
    account_approval_user_id = fields.Many2one(
        "res.users", string="Account Approved By", readonly=True, copy=False
    )
    account_approval_date = fields.Datetime(
        string="Account Approved On", readonly=True, copy=False
    )

    def action_submit(self):
        self.ensure_one()
        if self.state != "draft":
            return
        if self.transaction_type == "return" and not self.amount > 0:
            raise UserError("Return amount must be greater than 0")
        self.state = "submitted"
        if self.manager_id and self.manager_id.user_id:
            self.activity_schedule(
                "mail.mail_activity_data_todo",
                user_id=self.manager_id.user_id.id,
                summary=f"Approve Advance: {self.name}",
                note=f"Employee {self.employee_id.name} requests approval for {self.transaction_type}",
            )

    def action_manager_approve(self):
        for rec in self:
            if rec.state != "submitted":
                raise UserError("Only Submitted records can be approved by Manager.")
            rec.write(
                {
                    "state": "manager_approved",
                    "manager_approval_user_id": self.env.user.id,
                    "manager_approval_date": fields.Datetime.now(),
                }
            )
            rec.message_post(body=f"✅ Approved by Manager: {self.env.user.name}")
            rec.activity_feedback(["mail.mail_activity_data_todo"])

            # Notify Accountant
            if rec.accountant_id:
                rec.activity_schedule(
                    "mail.mail_activity_data_todo",
                    user_id=rec.accountant_id.id,
                    summary=f"Final Approval: {rec.name}",
                    note="Manager has approved. Please perform final accounting approval.",
                )

    def action_approve(self):
        for rec in self:
            if rec.state != "manager_approved":
                raise UserError(
                    "Only Manager Approved records can be approved by Account."
                )
            rec.write(
                {
                    "state": "approved",
                    "account_approval_user_id": self.env.user.id,
                    "account_approval_date": fields.Datetime.now(),
                }
            )
            rec.message_post(body=f"✅ Approved by Account: {self.env.user.name}")

    def action_reject(self):
        self.ensure_one()
        self.state = "draft"
        self.message_post(body=f"❌ Rejected by {self.env.user.name}")
        self.activity_feedback(["mail.mail_activity_data_todo"])

    def action_confirm(self, payment_data=None):
        self.ensure_one()
        if self.state != "approved":
            raise UserError("Only Account Approved records can be confirmed.")

        if self.transaction_type == "return":
            # Validation: Trust the computed balance on Employee (which handles Advance + Reimb Account)
            current_balance = self.employee_id.advance_balance
            # Note: advance_balance is Net (Advance - Reimb).
            # If we have 2000 in Reimb (Dr) and 0 in Advance, Balance is 2000.
            if self.amount > current_balance:
                raise UserError(
                    f"Insufficient balance ({current_balance:,.2f}) to return {self.amount:,.2f}"
                )

        if self.move_id:
            self.write({"state": "posted"})
            return

        # Use advance_account_id if configured, otherwise fall back to default_account_id (like Petty Cash)
        advance_account = (
            self.journal_id.advance_account_id or self.journal_id.default_account_id
        )
        if not advance_account:
            raise UserError(
                f"Please configure 'Employee Advance Account' or 'Default Account' in Journal '{self.journal_id.name}'."
            )

        if self.transaction_type in ("payout", "return"):
            if not payment_data:
                return {
                    "name": "Confirm Payment",
                    "type": "ir.actions.act_window",
                    "res_model": "advance.cash.payment.wizard",
                    "view_mode": "form",
                    "target": "new",
                    "context": {"default_advance_id": self.id},
                }

            pj = payment_data.get("payment_journal_id")
            if not pj:
                raise UserError("Payment Journal is required.")

            memo = self.name + (f" - {self.description}" if self.description else "")

            # Get accounts (advance_account already defined above with fallback)
            bank_account = self._get_payment_journal_account(
                pj,
                payment_type=(
                    "outbound" if self.transaction_type == "payout" else "inbound"
                ),
                payment_method_line=payment_data.get("payment_method_line_id"),
            )
            if not bank_account:
                raise UserError(
                    f"Please configure a default/payment account for journal {pj.name}"
                )
            if self.transaction_type == "payout":
                dr_account = advance_account
                cr_account = bank_account
            else:
                dr_account = bank_account

                reimburse_account = (
                    self.company_id.advance_cash_reimbursement_account_id
                )
                return_account = self.company_id.advance_cash_return_account_id

                cr_account = advance_account

                if return_account:
                    domain = [
                        ("account_id", "=", return_account.id),
                        ("partner_id", "=", self.employee_id.work_contact_id.id),
                        ("parent_state", "=", "posted"),
                    ]

                    aml_obj = self.env["account.move.line"]
                    return_debit = 0.0
                    stats = aml_obj.read_group(
                        domain=domain, fields=["balance"], groupby=["partner_id"]
                    )
                    if stats:
                        return_debit = stats[0]["balance"]

                    if return_debit > 0:
                        cr_account = return_account

                elif reimburse_account:
                    domain = [
                        ("account_id", "=", reimburse_account.id),
                        ("partner_id", "=", self.employee_id.work_contact_id.id),
                        ("parent_state", "=", "posted"),
                    ]
                    aml_obj = self.env["account.move.line"]
                    reimb_debit = 0.0
                    stats = aml_obj.read_group(
                        domain=domain, fields=["balance"], groupby=["partner_id"]
                    )
                    if stats:
                        reimb_debit = stats[0]["balance"]

                    if reimb_debit > 0:
                        cr_account = reimburse_account

            move_vals = {
                "move_type": "entry",
                "date": payment_data.get("payment_date") or self.date,
                "ref": self.name,
                "journal_id": pj.id,
                "line_ids": [
                    Command.create(
                        {
                            "name": memo,
                            "account_id": dr_account.id,
                            "debit": self.amount,
                            "credit": 0.0,
                            "partner_id": self.employee_id.work_contact_id.id
                            if self.employee_id.work_contact_id
                            else False,
                            "analytic_distribution": self.analytic_distribution,
                        }
                    ),
                    Command.create(
                        {
                            "name": memo,
                            "account_id": cr_account.id,
                            "debit": 0.0,
                            "credit": self.amount,
                            "partner_id": self.employee_id.work_contact_id.id
                            if self.employee_id.work_contact_id
                            else False,
                            "analytic_distribution": self.analytic_distribution,
                        }
                    ),
                ],
                "advance_id": self.id,
            }

            move = self.env["account.move"].create(move_vals)
            move.action_post()

            # Handle Cheque Logic if selected (Payout only for outgoing cheque)
            if payment_data.get("is_cheque_method"):
                if self.transaction_type == "payout":
                    if payment_data.get("cheque_id"):
                        cheque = payment_data["cheque_id"]
                        cheque.write(
                            {
                                "status": "used",
                                "used_date": move.date,
                                "amount": self.amount,
                            }
                        )
                elif self.transaction_type == "return" and payment_data.get(
                    "cheque_number_in"
                ):
                    pass

            self.move_id = move.id
            self.write({"state": "posted"})
            return

        elif self.transaction_type == "expense":
            if not self.line_ids:
                raise UserError("No Expense Lines.")
            currency = self.currency_id or self.env.company.currency_id
            m_lines, t_debit, t_credit = [], 0.0, 0.0

            for line in self.line_ids:
                base = line.amount_untaxed
                taxes = line.vat_tax_id | line.wht_tax_id
                res = taxes.with_context(force_price_include=False).compute_all(
                    base,
                    currency=currency,
                    quantity=1.0,
                    product=line.product_id,
                    partner=self.employee_id.work_contact_id,
                )
                m_lines.append(
                    Command.create(
                        {
                            "account_id": line.expense_account_id.id,
                            "partner_id": self.employee_id.work_contact_id.id,
                            "name": line.description,
                            "debit": currency.round(base),
                            "credit": 0.0,
                            "tax_ids": [Command.set(taxes.ids)] if taxes else False,
                            "analytic_distribution": line.analytic_distribution
                            or self.analytic_distribution,
                        }
                    )
                )
                t_debit = currency.round(t_debit + base)

                for tx in res["taxes"]:
                    amt = currency.round(tx["amount"])
                    if amt >= 0:
                        m_lines.append(
                            Command.create(
                                {
                                    "account_id": tx["account_id"],
                                    "partner_id": self.employee_id.work_contact_id.id,
                                    "name": tx["name"],
                                    "debit": amt,
                                    "credit": 0.0,
                                    "tax_repartition_line_id": tx[
                                        "tax_repartition_line_id"
                                    ],
                                    "tax_base_amount": base,
                                    "analytic_distribution": line.analytic_distribution
                                    or self.analytic_distribution,
                                }
                            )
                        )
                        t_debit = currency.round(t_debit + amt)
                    else:
                        m_lines.append(
                            Command.create(
                                {
                                    "account_id": tx["account_id"],
                                    "partner_id": self.employee_id.work_contact_id.id,
                                    "name": tx["name"],
                                    "debit": 0.0,
                                    "credit": abs(amt),
                                    "tax_repartition_line_id": tx[
                                        "tax_repartition_line_id"
                                    ],
                                    "tax_base_amount": base,
                                    "analytic_distribution": line.analytic_distribution
                                    or self.analytic_distribution,
                                }
                            )
                        )
                        t_credit = currency.round(t_credit + abs(amt))

            bal = currency.round(t_debit - t_credit)
            if bal > 0:
                current_advance_balance = self.employee_id.advance_balance
                available_advance = max(0.0, current_advance_balance)

                credit_to_advance = available_advance
                difference = bal - available_advance

                reimburse_account = (
                    self.company_id.advance_cash_reimbursement_account_id
                )
                return_account = self.company_id.advance_cash_return_account_id

                if difference > 0 and not reimburse_account:
                    credit_to_advance += difference
                    difference = 0
                elif difference < 0 and not return_account:
                    if not reimburse_account:
                        credit_to_advance = bal
                        difference = 0
                    else:
                        pass

                if credit_to_advance > 0:
                    m_lines.append(
                        Command.create(
                            {
                                "account_id": advance_account.id,
                                "partner_id": self.employee_id.work_contact_id.id,
                                "name": f"Clear Advance: {self.name}",
                                "debit": 0.0,
                                "credit": credit_to_advance,
                                "analytic_distribution": self.analytic_distribution,
                            }
                        )
                    )

                if difference > 0:
                    m_lines.append(
                        Command.create(
                            {
                                "account_id": reimburse_account.id,
                                "partner_id": self.employee_id.work_contact_id.id,
                                "name": f"Excess Expense: {self.name}",
                                "debit": 0.0,
                                "credit": difference,
                                "analytic_distribution": self.analytic_distribution,
                            }
                        )
                    )
                elif difference < 0:
                    target_account = return_account or reimburse_account

                    m_lines.append(
                        Command.create(
                            {
                                "account_id": target_account.id,
                                "partner_id": self.employee_id.work_contact_id.id,
                                "name": f"Return Pending: {self.name}",
                                "debit": abs(difference),
                                "credit": 0.0,
                                "analytic_distribution": self.analytic_distribution,
                            }
                        )
                    )

            move = (
                self.env["account.move"]
                .with_context(check_move_validity=False)
                .create(
                    {
                        "ref": f"{self.name} - {self.description or ''}",
                        "date": self.date,
                        "journal_id": self.journal_id.id,
                        "line_ids": m_lines,
                        "move_type": "entry",
                    }
                )
            )

            for line in self.line_ids:
                if line.tax_invoice_number:
                    target_taxes = line.vat_tax_id | line.wht_tax_id
                    for tax_inv in move.tax_invoice_ids:
                        if (
                            not tax_inv.tax_invoice_number
                            and tax_inv.tax_line_id in target_taxes
                        ):
                            tax_inv.write(
                                {
                                    "tax_invoice_number": line.tax_invoice_number,
                                    "tax_invoice_date": line.tax_invoice_date
                                    or self.date,
                                }
                            )

            move.action_post()
            self.move_id = move.id
            self.write({"state": "posted"})
            self.employee_id._compute_advance_balance()

    def action_create_reimbursement(self):
        """Open wizard to Pay Reimbursement (Direct Payment to Employee)."""
        self.ensure_one()
        if self.employee_id.advance_balance >= 0:
            raise UserError("Employee does not have an excess expense balance.")

        # Open Payment Wizard
        return {
            "name": "Pay Reimbursement",
            "type": "ir.actions.act_window",
            "res_model": "advance.cash.payment.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_advance_id": self.id},
        }

    def action_pay_reimbursement(self, payment_data):
        """Create Direct Payment for Reimbursement (Dr Other Payable / Cr Bank)."""
        self.ensure_one()
        pj = payment_data.get("payment_journal_id")
        if not pj:
            raise UserError("Payment Journal is required.")

        reimburse_amount = abs(self.employee_id.advance_balance)

        reimburse_account = self.company_id.advance_cash_reimbursement_account_id
        if not reimburse_account:
            reimburse_account = (
                self.journal_id.advance_account_id or self.journal_id.default_account_id
            )

        if not reimburse_account:
            raise UserError("Reimbursement Account configuration missing.")

        bank_account = self._get_payment_journal_account(
            pj,
            payment_type="outbound",
            payment_method_line=payment_data.get("payment_method_line_id"),
        )
        if not bank_account:
            raise UserError(
                f"Please configure a default/payment account for journal {pj.name}"
            )

        memo = f"Reimburse: {self.name}"

        move_vals = {
            "move_type": "entry",
            "date": payment_data.get("payment_date") or fields.Date.today(),
            "ref": memo,
            "journal_id": pj.id,
            "line_ids": [
                Command.create(
                    {
                        "name": memo,
                        "account_id": reimburse_account.id,
                        "debit": reimburse_amount,
                        "credit": 0.0,
                        "partner_id": self.employee_id.work_contact_id.id,
                        "analytic_distribution": self.analytic_distribution,
                    }
                ),
                Command.create(
                    {
                        "name": memo,
                        "account_id": bank_account.id,
                        "debit": 0.0,
                        "credit": reimburse_amount,
                        "partner_id": self.employee_id.work_contact_id.id,
                        "analytic_distribution": self.analytic_distribution,
                    }
                ),
            ],
        }

        move = self.env["account.move"].create(move_vals)
        move.action_post()

        self.reimburse_move_id = move.id
        return self.action_view_reimbursement()

    reimburse_move_id = fields.Many2one(
        "account.move", string="Reimbursement Payment", readonly=True
    )
    reimburse_payment_state = fields.Selection(
        related="reimburse_move_id.payment_state"
    )

    def action_view_reimbursement(self):
        self.ensure_one()
        return {
            "name": "Reimbursement Payment",
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "form",
            "res_id": self.reimburse_move_id.id,
        }

    total_untaxed = fields.Float("Untaxed", compute="_compute_summary_totals")
    total_tax = fields.Float("Tax", compute="_compute_summary_totals")
    total_amount = fields.Float("Total", compute="_compute_summary_totals")

    @api.depends("line_ids.amount", "line_ids.amount_tax", "line_ids.amount_untaxed")
    def _compute_summary_totals(self):
        for rec in self:
            rec.total_untaxed = sum(rec.line_ids.mapped("amount_untaxed"))
            rec.total_tax = sum(rec.line_ids.mapped("amount_tax"))
            rec.total_amount = sum(rec.line_ids.mapped("amount"))


class AdvanceCashLogLine(models.Model):
    _name = "advance.cash.log.line"
    _description = "Line Details"

    log_id = fields.Many2one(
        "advance.cash.log", string="Log", required=True, ondelete="cascade"
    )
    product_id = fields.Many2one(
        "product.product", string="Product", domain=[("can_be_expensed", "=", True)]
    )
    description = fields.Char("Description")
    company_id = fields.Many2one(
        related="log_id.company_id", string="Company", store=True, readonly=True
    )
    expense_account_id = fields.Many2one(
        "account.account",
        string="Account",
        domain=[
            (
                "account_type",
                "in",
                ("expense", "expense_depreciation", "expense_direct_cost"),
            )
        ],
    )

    def _default_analytic(self):
        return (
            self.log_id.analytic_distribution
            or self.env.company.advance_cash_analytic_distribution
        )

    analytic_distribution = fields.Json("Analytic", default=_default_analytic)
    analytic_precision = fields.Integer(
        store=False,
        default=lambda self: self.env["decimal.precision"].precision_get(
            "Percentage Analytic"
        ),
    )
    vat_tax_id = fields.Many2one(
        "account.tax",
        string="VAT",
        domain=[("type_tax_use", "=", "purchase"), ("amount", ">=", 0)],
    )
    wht_tax_id = fields.Many2one(
        "account.tax",
        string="WHT",
        domain=[("type_tax_use", "=", "purchase"), ("amount", "<", 0)],
    )
    amount = fields.Float("Total Amount")
    amount_untaxed = fields.Float("Untaxed", compute="_compute_tax_amounts", store=True)
    amount_tax = fields.Float("Tax", compute="_compute_tax_amounts", store=True)
    tax_invoice_number = fields.Char("Tax Invoice Number")
    tax_invoice_date = fields.Date("Tax Invoice Date")

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if self.product_id:
            self.description = self.product_id.display_name
            self.expense_account_id = (
                self.product_id.property_account_expense_id
                or self.product_id.categ_id.property_account_expense_categ_id
            )
            if self.product_id.supplier_taxes_id:
                vat = self.product_id.supplier_taxes_id.filtered(
                    lambda t: t.amount >= 0
                )[:1]
                wht = self.product_id.supplier_taxes_id.filtered(
                    lambda t: t.amount < 0
                )[:1]
                if vat:
                    self.vat_tax_id = vat.id
                if wht:
                    self.wht_tax_id = wht.id

            if not self.analytic_distribution and self.log_id.analytic_distribution:
                self.analytic_distribution = self.log_id.analytic_distribution

    @api.depends("amount", "vat_tax_id")
    def _compute_tax_amounts(self):
        for line in self:
            if line.vat_tax_id and line.amount:
                res = line.vat_tax_id.with_context(
                    force_price_include=True
                ).compute_all(
                    line.amount,
                    currency=line.log_id.currency_id,
                    quantity=1.0,
                    product=line.product_id,
                    partner=line.log_id.employee_id.work_contact_id,
                )
                line.amount_tax = res["total_included"] - res["total_excluded"]
                line.amount_untaxed = res["total_excluded"]
            else:
                line.amount_tax, line.amount_untaxed = 0.0, line.amount
