# account_accrual_wizard/wizards/accrual_create_wizard.py
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountAccrualCreateWizard(models.TransientModel):
    _name = "account.accrual.create.wizard"
    _description = "Accrual Creation Wizard (multi-line)"

    name = fields.Char(string="Description", required=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    date = fields.Date(
        string="Accrual Date",
        required=True,
        default=fields.Date.context_today,
    )
    period_start = fields.Date(string="Period Start")
    period_end = fields.Date(string="Period End")

    accrual_account_id = fields.Many2one(
        "account.account",
        string="Header Accrual Account",
        required=False,  # optional
        domain=[("deprecated", "=", False)],
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )

    line_ids = fields.One2many(
        "account.accrual.create.wizard.line",
        "wizard_id",
        string="Accrual Lines",
    )

    attachment_ids = fields.Many2many(
        "ir.attachment",
        "acc_create_wizard_attachment_rel",
        "wizard_id",
        "attachment_id",
        string="Supporting Documents",
    )

    def action_create_accrual(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("Please add at least one line."))

        total = sum(self.line_ids.mapped("amount"))
        if not total:
            raise UserError(_("Total amount must be greater than zero."))

        accrual_vals = {
            "description": self.name,
            "company_id": self.company_id.id,
            "date": self.date,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "accrual_account_id": self.accrual_account_id.id or False,
            "currency_id": self.currency_id.id,
        }
        accrual = self.env["account.accrual"].create(accrual_vals)

        # create lines
        for line in self.line_ids:
            self.env["account.accrual.line"].create(
                {
                    "accrual_id": accrual.id,
                    "product_id": line.product_id.id,
                    "partner_id": line.partner_id.id or False,
                    "name": line.name,
                    "expense_account_id": line.expense_account_id.id or False,
                    "analytic_account_id": line.analytic_account_id.id or False,
                    "amount": line.amount,
                }
            )

        # move attachments -> accrual
        if self.attachment_ids:
            self.attachment_ids.write(
                {
                    "res_model": "account.accrual",
                    "res_id": accrual.id,
                }
            )
            accrual.attachment_ids = [(6, 0, self.attachment_ids.ids)]

        # post JE
        accrual.action_post()

        action = self.env.ref("account_accrual_wizard.action_account_accrual").read()[0]
        action["res_id"] = accrual.id
        action["view_mode"] = "form"
        return action


class AccountAccrualCreateWizardLine(models.TransientModel):
    _name = "account.accrual.create.wizard.line"
    _description = "Accrual Creation Wizard Line"

    wizard_id = fields.Many2one(
        "account.accrual.create.wizard",
        string="Wizard",
        required=True,
        ondelete="cascade",
    )

    product_id = fields.Many2one(
        "product.product",
        string="Product",
        required=True,
    )

    partner_id = fields.Many2one(
        "res.partner",
        string="Vendor",
    )
    name = fields.Char(
        string="Description",
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
    currency_id = fields.Many2one(
        related="wizard_id.currency_id",
        store=True,
        readonly=True,
    )

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.display_name
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
