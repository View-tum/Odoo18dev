from odoo import Command, api, fields, models
from odoo.exceptions import UserError


class PettyCashLog(models.Model):
    _name = "petty.cash.log"
    _description = "Easy Petty Cash Logbook"
    _order = "date desc, id desc"
    _inherit = ["mail.thread", "mail.activity.mixin", "analytic.mixin"]

    name = fields.Char(
        string="Document Number",
        required=True,
        copy=False,
        readonly=True,
        default="New",
    )
    date = fields.Date(
        string="Date", default=fields.Date.context_today, required=True, tracking=True
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        tracking=True,
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
        tracking=True,
    )

    def _default_journal(self):
        # 1. Try company default from settings
        company_default = self.env.company.petty_cash_journal_id
        if company_default:
            return company_default
        # 2. Fallback to any cash journal
        return self.env["account.journal"].search(
            [("type", "=", "cash"), ("company_id", "=", self.env.company.id)], limit=1
        ) or self.env["account.journal"].search([("type", "=", "cash")], limit=1)

    journal_id = fields.Many2one(
        "account.journal",
        string="Journal",
        domain=[("type", "in", ["cash", "bank"])],
        required=True,
        tracking=True,
        default=_default_journal,
    )

    analytic_distribution = fields.Json(
        string="Analytic Distribution",
        default=lambda self: self.env.company.petty_cash_analytic_distribution,
    )

    analytic_precision = fields.Integer(
        store=False,
        default=lambda self: self.env["decimal.precision"].precision_get(
            "Percentage Analytic"
        ),
    )

    # 1. เพิ่ม Type 'deposit'
    transaction_type = fields.Selection(
        [
            ("in", "Replenish (In)"),
            ("out", "Expense (Out)"),
            ("deposit", "Deposit Excess (Bank)"),  # <-- NEW
        ],
        string="Transaction Type",
        default="out",
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

    partner_id = fields.Many2one("res.partner", string="Vendor")
    description = fields.Char(string="Description", required=True, tracking=True)
    expense_account_id = fields.Many2one(
        "account.account",
        string="Expense Account",
        domain="[('account_type', 'in', ['expense', 'expense_depreciation', 'expense_direct_cost'])]",
    )

    line_ids = fields.One2many("petty.cash.log.line", "log_id", string="Lines")
    amount = fields.Float(string="Amount", required=True, tracking=True)

    amount_total = fields.Float(
        string="Net Amount", compute="_compute_amount_total", store=True
    )

    amount_signed = fields.Float(
        "Amount (Signed)", compute="_compute_amount_signed", store=True
    )

    # 2. ปรับการคำนวณยอด Signed (Deposit ติดลบเหมือน Expense)
    @api.depends("amount_total", "transaction_type")
    def _compute_amount_signed(self):
        for rec in self:
            if rec.transaction_type == "in":
                rec.amount_signed = rec.amount_total
            else:
                # out or deposit counts as spending/reducing cash
                rec.amount_signed = -rec.amount_total

    total_untaxed = fields.Float("Untaxed", compute="_compute_summary_totals")
    total_tax = fields.Float("Tax", compute="_compute_summary_totals")
    total_amount = fields.Float("Total", compute="_compute_summary_totals")

    @api.depends("line_ids.amount", "line_ids.amount_tax", "line_ids.amount_untaxed")
    def _compute_summary_totals(self):
        for rec in self:
            rec.total_untaxed = sum(rec.line_ids.mapped("amount_untaxed"))
            rec.total_tax = sum(rec.line_ids.mapped("amount_tax"))
            rec.total_amount = sum(rec.line_ids.mapped("amount"))

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

    current_balance = fields.Float(
        "Current Balance", compute="_compute_current_balance"
    )

    petty_cash_limit = fields.Float(
        string="Max Limit", related="journal_id.petty_cash_limit", readonly=True
    )

    spent_amount = fields.Float(string="Amount Spent", compute="_compute_spent_amount")

    @api.depends("current_balance", "petty_cash_limit")
    def _compute_spent_amount(self):
        for rec in self:
            rec.spent_amount = rec.petty_cash_limit - rec.current_balance

    @api.depends("journal_id")
    def _compute_current_balance(self):
        for journal in self.mapped("journal_id"):
            account = journal.default_account_id
            if not account:
                self.filtered(lambda r: r.journal_id == journal).current_balance = 0.0
                continue

            # คำนวณยอดเงินจากทุก Journal ที่วิ่งเข้า Account นี้ (เช่น ฝากเงินจาก Bank เข้าเงินสดย่อย)
            domain = [
                ("account_id", "=", account.id),
                ("parent_state", "=", "posted"),
            ]
            result = self.env["account.move.line"].read_group(
                domain, ["balance"], ["account_id"]
            )
            balance = result[0]["balance"] if result else 0.0

            self.filtered(lambda r: r.journal_id == journal).current_balance = balance

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

    move_id = fields.Many2one("account.move", string="Journal Entry", readonly=True)

    @api.model
    def create(self, vals):
        if vals.get("name", "New") == "New":
            vals["name"] = (
                self.env["ir.sequence"].next_by_code("petty.cash.log") or "PC-LOG"
            )
        return super(PettyCashLog, self).create(vals)

    def write(self, vals):
        if not self.env.su:
            protected_fields = [
                "employee_id",
                "date",
                "amount",
                "journal_id",
                "description",
                "line_ids",
            ]
            if any(f in vals for f in protected_fields):
                for rec in self:
                    if rec.state not in ["draft"]:
                        raise UserError(
                            f"Cannot edit {rec.name} in '{rec.state}' state."
                        )
        return super(PettyCashLog, self).write(vals)

    def _get_payment_journal_account(
        self, journal, payment_type="outbound", payment_method_line=False
    ):
        self.ensure_one()
        if (
            payment_method_line
            and payment_method_line.journal_id == journal
            and payment_method_line.payment_account_id
        ):
            if payment_method_line.payment_type == payment_type:
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

        fallback_line = self.env["account.payment.method.line"].search(
            [("journal_id", "=", journal.id), ("payment_account_id", "!=", False)],
            limit=1,
        )
        return fallback_line.payment_account_id if fallback_line else False

    # 3. คำนวณ Amount Total (Deposit ใช้ยอด Header เหมือน In)
    @api.depends("amount", "line_ids.amount", "transaction_type")
    def _compute_amount_total(self):
        for rec in self:
            if rec.transaction_type in ["in", "deposit"]:
                rec.amount_total = rec.amount
            else:
                rec.amount_total = sum(rec.line_ids.mapped("amount"))

    def action_submit(self):
        self.ensure_one()
        if self.state != "draft":
            return
        self.state = "submitted"
        if self.manager_id and self.manager_id.user_id:
            self.activity_schedule(
                "mail.mail_activity_data_todo",
                user_id=self.manager_id.user_id.id,
                summary=f"Approve Petty Cash: {self.name}",
                note=f"Employee {self.employee_id.name} requests approval.",
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

    # 4. Action Confirm: แยกเคส Deposit
    def action_confirm(self, payment_data=None):
        for rec in self:
            if rec.state != "approved":
                raise UserError("Only Account Approved records can be confirmed.")

            if not payment_data:
                # กำหนดชื่อ Title ของ Wizard
                name = "Confirm Payment"
                if rec.transaction_type == "in":
                    name = "Confirm Replenish"
                elif rec.transaction_type == "deposit":
                    name = "Confirm Deposit to Bank"
                else:
                    name = "Confirm Clearing"

                return {
                    "name": name,
                    "type": "ir.actions.act_window",
                    "res_model": "petty.cash.payment.wizard",
                    "view_mode": "form",
                    "target": "new",
                    "context": {"default_petty_cash_id": self.id},
                }

            move_id = False
            # Process payment based on transaction type
            if rec.transaction_type == "in":
                # REPLENISHMENT: Dr Petty Cash / Cr Bank
                move_id = rec._create_replenishment_payment(payment_data)
            elif rec.transaction_type == "deposit":
                # DEPOSIT: Dr Bank / Cr Petty Cash
                move_id = rec._create_deposit_entry(payment_data)
            else:
                # EXPENSE: Dr Expense / Cr Petty Cash
                move_id = rec._create_journal_entry(payment_data=payment_data)

            rec.write({"state": "posted", "move_id": move_id})

    # 5. ฟังก์ชันใหม่: สร้างรายการฝากเงินคืนธนาคาร
    def _create_deposit_entry(self, payment_data):
        """Create manual journal entry for Deposit (Out to Bank): Dr Bank / Cr Petty Cash."""
        self.ensure_one()
        rec = self

        if not rec.journal_id.default_account_id:
            raise UserError(
                f"Please configure Default Account in '{rec.journal_id.name}'"
            )

        # Journal ปลายทาง (Bank ที่เอาเงินไปฝาก)
        pj = payment_data.get("payment_journal_id")
        if not pj:
            raise UserError("Target Bank Journal is required.")

        petty_cash_account = rec.journal_id.default_account_id

        # Get bank account from selected journal
        bank_account = rec._get_payment_journal_account(
            pj,
            payment_type="inbound",
            payment_method_line=payment_data.get("payment_method_line_id"),
        )
        if not bank_account:
            raise UserError(
                f"Please configure a default/payment account for journal {pj.name}"
            )

        memo = f"Deposit Excess: {rec.name} - {rec.description}"

        # We post this move in the Bank Journal (Target)
        target_journal = pj

        move_vals = {
            "move_type": "entry",
            "date": payment_data.get("payment_date") or rec.date,
            "ref": rec.name,
            "journal_id": target_journal.id,
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "name": memo,
                        "account_id": bank_account.id,
                        "debit": rec.amount_total,  # Bank เพิ่ม (Dr)
                        "credit": 0.0,
                        "partner_id": rec.employee_id.work_contact_id.id,
                        "analytic_distribution": rec.analytic_distribution,
                    },
                ),
                (
                    0,
                    0,
                    {
                        "name": memo,
                        "account_id": petty_cash_account.id,
                        "debit": 0.0,
                        "credit": rec.amount_total,  # Petty Cash ลด (Cr)
                        "partner_id": rec.employee_id.work_contact_id.id,
                        "analytic_distribution": rec.analytic_distribution,
                    },
                ),
            ],
            "petty_cash_id": rec.id,
        }

        move = self.env["account.move"].create(move_vals)
        move.action_post()
        return move.id

    def _create_replenishment_payment(self, payment_data):
        """Create manual journal entry for replenishment (In) to ensure exact Dr 111102 / Cr Bank."""
        self.ensure_one()
        rec = self

        if not rec.journal_id.default_account_id:
            raise UserError(
                f"Please configure Default Account in '{rec.journal_id.name}'"
            )

        pj = payment_data.get("payment_journal_id")
        if not pj:
            raise UserError("Payment Journal is required.")

        # For replenishment: Dr. Petty Cash Account / Cr. Bank Account
        petty_cash_account = rec.journal_id.default_account_id
        # Get bank account from selected journal
        bank_account = rec._get_payment_journal_account(
            pj,
            payment_type="outbound",
            payment_method_line=payment_data.get("payment_method_line_id"),
        )
        if not bank_account:
            raise UserError(
                f"Please configure a default/payment account for journal {pj.name}"
            )

        memo = f"{rec.name} - {rec.description}" if rec.description else rec.name

        target_journal = pj

        move_vals = {
            "move_type": "entry",
            "date": payment_data.get("payment_date") or rec.date,
            "ref": rec.name,
            "journal_id": target_journal.id,
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "name": memo,
                        "account_id": petty_cash_account.id,
                        "debit": rec.amount_total,  # Petty Cash เพิ่ม (Dr)
                        "credit": 0.0,
                        "partner_id": rec.employee_id.work_contact_id.id,
                        "analytic_distribution": rec.analytic_distribution,
                    },
                ),
                (
                    0,
                    0,
                    {
                        "name": memo,
                        "account_id": bank_account.id,
                        "debit": 0.0,
                        "credit": rec.amount_total,  # Bank ลด (Cr)
                        "partner_id": rec.employee_id.work_contact_id.id,
                        "analytic_distribution": rec.analytic_distribution,
                    },
                ),
            ],
            "petty_cash_id": rec.id,
        }

        move = self.env["account.move"].create(move_vals)
        move.action_post()

        # Update cheque status if exists
        if payment_data.get("is_cheque_method") and payment_data.get("cheque_id"):
            cheque = payment_data["cheque_id"]
            cheque.write(
                {
                    "status": "used",
                    "used_date": move.date,
                    "amount": rec.amount_total,
                }
            )

        return move.id

    def action_open_confirm_payment_wizard(self):
        """Deprecated: Use action_confirm directly which now returns the wizard if needed."""
        return self.action_confirm()

    def _create_journal_entry(self, payment_data=None):
        self.ensure_one()
        rec = self
        if rec.amount_total <= 0:
            raise UserError("Amount must be greater than 0")
        if not rec.journal_id.default_account_id:
            raise UserError(
                f"Please configure Default Account in the Cash Journal '{rec.journal_id.name}'"
            )

        currency = rec.journal_id.currency_id or rec.company_id.currency_id

        # Multi-line Expense: Dr. Expenses / Cr. Petty Cash
        if not rec.line_ids:
            raise UserError("No Expense Lines.")

        m_lines, t_debit, t_credit = [], 0.0, 0.0
        for line in rec.line_ids:
            base = line.amount_untaxed
            taxes = line.vat_tax_id | line.wht_tax_id
            res = taxes.with_context(force_price_include=False).compute_all(
                base,
                currency=currency,
                quantity=1.0,
                product=line.product_id,
                partner=rec.partner_id or rec.employee_id.work_contact_id,
            )
            m_lines.append(
                Command.create(
                    {
                        "account_id": line.expense_account_id.id,
                        "partner_id": rec.partner_id.id
                        if rec.partner_id
                        else rec.employee_id.work_contact_id.id,
                        "name": line.name,
                        "debit": currency.round(base),
                        "credit": 0.0,
                        "tax_ids": [Command.set(taxes.ids)] if taxes else False,
                        "analytic_distribution": line.analytic_distribution,
                    }
                )
            )
            t_debit = currency.round(t_debit + base)

            for tx in res["taxes"]:
                amt = currency.round(tx["amount"])
                account_id = tx["account_id"]
                tax_obj = self.env["account.tax"].browse(tx["id"])
                is_wht = "WHT" in (tax_obj.name or "").upper() or "หัก ณ ที่จ่าย" in (
                    tax_obj.name or ""
                )
                if is_wht and rec.journal_id.petty_cash_wht_account_id:
                    account_id = rec.journal_id.petty_cash_wht_account_id.id

                if not account_id:
                    raise UserError(
                        f"Please configure Account in Tax settings for '{tax_obj.name}'"
                    )

                if amt >= 0:
                    m_lines.append(
                        Command.create(
                            {
                                "account_id": account_id,
                                "partner_id": rec.partner_id.id
                                if rec.partner_id
                                else rec.employee_id.work_contact_id.id,
                                "name": tx["name"],
                                "debit": amt,
                                "credit": 0.0,
                                "tax_repartition_line_id": tx[
                                    "tax_repartition_line_id"
                                ],
                                "tax_base_amount": base,
                                "analytic_distribution": line.analytic_distribution,
                            }
                        )
                    )
                    t_debit = currency.round(t_debit + amt)
                else:
                    m_lines.append(
                        Command.create(
                            {
                                "account_id": account_id,
                                "partner_id": rec.partner_id.id
                                if rec.partner_id
                                else rec.employee_id.work_contact_id.id,
                                "name": tx["name"],
                                "debit": 0.0,
                                "credit": abs(amt),
                                "tax_repartition_line_id": tx[
                                    "tax_repartition_line_id"
                                ],
                                "tax_base_amount": base,
                                "analytic_distribution": line.analytic_distribution,
                            }
                        )
                    )
                    t_credit = currency.round(t_credit + abs(amt))

        # Counterpart: Cr. Petty Cash (Net Amount)
        net_payment = t_debit - t_credit
        m_lines.append(
            Command.create(
                {
                    "account_id": rec.journal_id.default_account_id.id,
                    "partner_id": rec.partner_id.id
                    if rec.partner_id
                    else rec.employee_id.work_contact_id.id,
                    "name": rec.name
                    + (f" - {rec.description}" if rec.description else ""),
                    "debit": 0.0,
                    "credit": net_payment,
                    "analytic_distribution": rec.analytic_distribution,
                }
            )
        )

        journal = payment_data.get("payment_journal_id") or rec.journal_id
        date = payment_data.get("payment_date") or rec.date

        move_vals = {
            "ref": rec.name,
            "date": date,
            "journal_id": journal.id,
            "move_type": "entry",
            "line_ids": m_lines,
        }
        move = self.env["account.move"].create(move_vals)

        # Assign Tax Invoice Number to Tax Lines if present
        for line in rec.line_ids:
            if line.tax_invoice_number:
                target_taxes = line.vat_tax_id | line.wht_tax_id
                for tax_inv in move.line_ids:
                    if tax_inv.tax_line_id in target_taxes:
                        if tax_inv.tax_invoice_ids:
                            tax_inv.tax_invoice_ids.write(
                                {
                                    "tax_invoice_number": line.tax_invoice_number,
                                    "tax_invoice_date": line.tax_invoice_date
                                    or rec.date,
                                    "partner_id": tax_inv.partner_id.id,
                                }
                            )
                        else:
                            tax_inv.write(
                                {
                                    "tax_invoice_ids": [
                                        Command.create(
                                            {
                                                "tax_invoice_number": line.tax_invoice_number,
                                                "tax_invoice_date": line.tax_invoice_date
                                                or rec.date,
                                                "partner_id": tax_inv.partner_id.id,
                                            }
                                        )
                                    ]
                                }
                            )

        move.action_post()
        return move.id

    def unlink(self):
        if any(rec.state == "posted" for rec in self):
            raise UserError("Cannot delete posted entries.")
        return super(PettyCashLog, self).unlink()

    def action_draft(self):
        for rec in self:
            if rec.move_id:
                if rec.move_id.state == "posted":
                    reversal = rec.move_id._reverse_moves(
                        default_values_list=[
                            {
                                "date": fields.Date.context_today(rec),
                                "ref": f"Reset to Draft: {rec.name}",
                            }
                        ],
                        cancel=False,
                    )
                    reversal.action_post()
                else:
                    rec.move_id.unlink()
            rec.write({"state": "draft", "move_id": False})

    def action_open_journal_entry(self):
        self.ensure_one()
        return {
            "name": "Journal Entry",
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "form",
            "res_id": self.move_id.id,
            "target": "current",
        }


class PettyCashLogLine(models.Model):
    _name = "petty.cash.log.line"
    _description = "Petty Cash Log Line"

    def _default_analytic(self):
        return (
            self.log_id.analytic_distribution
            or self.env.company.petty_cash_analytic_distribution
        )

    log_id = fields.Many2one("petty.cash.log", string="Log", ondelete="cascade")
    company_id = fields.Many2one(
        related="log_id.company_id",
        string="Company",
        store=True,
        readonly=True,
    )
    product_id = fields.Many2one(
        "product.product", string="Product", domain=[("can_be_expensed", "=", True)]
    )
    name = fields.Char("Description", required=True)
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
            self.name = self.product_id.display_name
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

    @api.depends("amount", "vat_tax_id")
    def _compute_tax_amounts(self):
        for line in self:
            if line.vat_tax_id and line.amount:
                currency = (
                    line.log_id.journal_id.currency_id
                    or line.log_id.company_id.currency_id
                )
                res = line.vat_tax_id.with_context(
                    force_price_include=True
                ).compute_all(
                    line.amount,
                    currency=currency,
                    quantity=1.0,
                    product=line.product_id,
                    partner=line.log_id.partner_id
                    or line.log_id.employee_id.work_contact_id,
                )
                line.amount_tax = res["total_included"] - res["total_excluded"]
                line.amount_untaxed = res["total_excluded"]
            else:
                line.amount_tax, line.amount_untaxed = 0.0, line.amount
