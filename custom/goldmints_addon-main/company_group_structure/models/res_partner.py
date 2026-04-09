# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_company_group = fields.Boolean(string="Company Group")
    company_group_parent_id = fields.Many2one(
        "res.partner",
        string="Company Group (Legacy)",
        domain=[("is_company_group", "=", True)],
        help="Legacy field. Use Company Group instead.",
    )
    company_group_id = fields.Many2one(
        "res.partner",
        string="Company Group",
    )
    company_group_company_ids = fields.One2many(
        "res.partner",
        "company_group_id",
        string="Group Companies",
        domain=[("company_type", "=", "company"), ("is_company_group", "=", False)],
    )
    report_outstanding = fields.Monetary(
        string="Outstanding (Posted AR)",
        compute="_compute_company_group_report_amounts",
        currency_field="currency_id",
        groups="account.group_account_invoice,account.group_account_readonly",
    )
    report_to_invoice = fields.Monetary(
        string="To Invoice (Sales Orders)",
        compute="_compute_company_group_report_amounts",
        currency_field="currency_id",
        groups="account.group_account_invoice,account.group_account_readonly",
    )
    report_open_quotations = fields.Monetary(
        string="Open Quotations",
        compute="_compute_company_group_report_amounts",
        currency_field="currency_id",
        groups="account.group_account_invoice,account.group_account_readonly",
    )
    report_total_due = fields.Monetary(
        string="Total Exposure",
        compute="_compute_company_group_report_amounts",
        currency_field="currency_id",
        groups="account.group_account_invoice,account.group_account_readonly",
    )
    report_over_credit = fields.Monetary(
        string="Over Credit",
        compute="_compute_company_group_report_amounts",
        currency_field="currency_id",
        groups="account.group_account_invoice,account.group_account_readonly",
    )
    report_remaining_credit = fields.Monetary(
        string="Remaining Credit",
        compute="_compute_company_group_report_amounts",
        currency_field="currency_id",
        groups="account.group_account_invoice,account.group_account_readonly",
    )
    report_oldest_unpaid_invoice_date = fields.Date(
        string="Oldest Unpaid Invoice Date",
        compute="_compute_company_group_report_amounts",
        groups="account.group_account_invoice,account.group_account_readonly",
    )
    report_last_payment_date = fields.Date(
        string="Last Payment Date",
        compute="_compute_company_group_report_amounts",
        groups="account.group_account_invoice,account.group_account_readonly",
    )
    report_days_sales_outstanding = fields.Float(
        string="DSO",
        compute="_compute_company_group_report_amounts",
        groups="account.group_account_invoice,account.group_account_readonly",
    )
    report_credit_status = fields.Selection(
        [
            ("ok", "OK"),
            ("over", "Over"),
            ("hold", "Hold"),
        ],
        string="Credit Status",
        compute="_compute_company_group_report_amounts",
        groups="account.group_account_invoice,account.group_account_readonly",
    )
    report_payment_term_id = fields.Many2one(
        "account.payment.term",
        string="Payment Term",
        related="property_payment_term_id",
        readonly=True,
    )

    @api.model
    def _get_so_approved_amount_map(self, company, commercial_partner_ids):
        """Return approved SO exposure per commercial partner in company currency.

        Exposure is computed from confirmed sales orders (sale/done) as:
            max(0, amount_total - amount_invoiced)
        This records risk as soon as SO is approved, independent of delivery status.
        """
        amounts = {}
        if not commercial_partner_ids:
            return amounts

        sale_orders = self.env["sale.order"].sudo().with_company(company).search([
            ("company_id", "=", company.id),
            ("partner_id.commercial_partner_id", "in", commercial_partner_ids),
            ("state", "in", ("sale", "done")),
        ])
        today = fields.Date.context_today(self)
        for so in sale_orders:
            commercial_partner = so.partner_id.commercial_partner_id
            if not commercial_partner:
                continue
            pending_amount = max(0.0, (so.amount_total or 0.0) - (so.amount_invoiced or 0.0))
            if not pending_amount:
                continue
            amount_company_currency = so.currency_id._convert(
                pending_amount,
                company.currency_id,
                company,
                so.date_order or today,
            )
            amounts[commercial_partner.id] = amounts.get(commercial_partner.id, 0.0) + amount_company_currency
        return amounts

    @api.depends_context("company")
    def _compute_company_group_report_amounts(self):
        for partner in self:
            partner.report_outstanding = 0.0
            partner.report_to_invoice = 0.0
            partner.report_open_quotations = 0.0
            partner.report_total_due = 0.0
            partner.report_over_credit = 0.0
            partner.report_remaining_credit = 0.0
            partner.report_oldest_unpaid_invoice_date = False
            partner.report_last_payment_date = False
            partner.report_days_sales_outstanding = 0.0
            partner.report_credit_status = "ok"

        company = self.env.company
        groups = self.filtered(lambda partner: partner.is_company_group)
        companies = self.filtered(
            lambda partner: partner.company_type == "company" and not partner.is_company_group
        )

        def _sum_orders_company_currency(order):
            date = order.date_order or fields.Date.context_today(self)
            return order.currency_id._convert(
                order.amount_total or 0.0,
                company.currency_id,
                company,
                date,
            )

        group_companies = self.env["res.partner"]
        if groups:
            group_companies = self.env["res.partner"].with_company(company).with_context(
                active_test=False
            ).search([
                ("company_group_id", "in", groups.ids),
                ("company_type", "=", "company"),
            ])

        report_companies = (companies | group_companies).with_company(company)
        report_company_ids = report_companies.ids

        quotation_totals = {}
        so_approved_totals = {}
        if report_company_ids:
            sale_orders = self.env["sale.order"].with_company(company).search([
                ("company_id", "=", company.id),
                ("partner_id.commercial_partner_id", "in", report_company_ids),
                ("state", "in", ("draft", "sent")),
            ])
            for so in sale_orders:
                commercial_partner = so.partner_id.commercial_partner_id
                if not commercial_partner:
                    continue
                quotation_totals.setdefault(commercial_partner.id, 0.0)
                quotation_totals[commercial_partner.id] += _sum_orders_company_currency(so)
            so_approved_totals = self._get_so_approved_amount_map(company, report_company_ids)

        oldest_unpaid = {}
        last_paid = {}
        if report_company_ids:
            unpaid_groups = self.env["account.move"].read_group(
                domain=[
                    ("state", "=", "posted"),
                    ("payment_state", "!=", "paid"),
                    ("move_type", "in", ("out_invoice", "out_refund")),
                    ("commercial_partner_id", "in", report_company_ids),
                    ("company_id", "=", company.id),
                ],
                fields=["invoice_date:min", "commercial_partner_id"],
                groupby=["commercial_partner_id"],
            )
            for row in unpaid_groups:
                partner = row["commercial_partner_id"]
                if partner:
                    oldest_unpaid[partner] = row.get("invoice_date")

            paid_groups = self.env["account.move"].read_group(
                domain=[
                    ("state", "=", "posted"),
                    ("payment_state", "=", "paid"),
                    ("move_type", "in", ("out_invoice", "out_refund")),
                    ("commercial_partner_id", "in", report_company_ids),
                    ("company_id", "=", company.id),
                ],
                fields=["invoice_date:max", "commercial_partner_id"],
                groupby=["commercial_partner_id"],
            )
            for row in paid_groups:
                partner = row["commercial_partner_id"]
                if partner:
                    last_paid[partner] = row.get("invoice_date")

        totals = {}
        for member in report_companies:
            group_id = member.company_group_id.id
            if not group_id:
                continue
            totals.setdefault(
                group_id,
                {"credit": 0.0, "to_invoice": 0.0, "quotes": 0.0, "dso_num": 0.0, "dso_den": 0.0},
            )
            totals[group_id]["credit"] += member.credit or 0.0
            totals[group_id]["to_invoice"] += so_approved_totals.get(member.id, 0.0)
            totals[group_id]["quotes"] += quotation_totals.get(member.id, 0.0)
            credit_weight = member.credit or 0.0
            totals[group_id]["dso_num"] += (member.days_sales_outstanding or 0.0) * credit_weight
            totals[group_id]["dso_den"] += credit_weight

        if groups:
            for group in groups.with_company(company):
                amounts = totals.get(
                    group.id,
                    {"credit": 0.0, "to_invoice": 0.0, "quotes": 0.0, "dso_num": 0.0, "dso_den": 0.0},
                )
                outstanding = amounts["credit"]
                to_invoice = amounts["to_invoice"]
                open_quotes = amounts["quotes"]
                total_due = outstanding + to_invoice + open_quotes
                limit = group.credit_limit or 0.0
                group.report_outstanding = outstanding
                group.report_to_invoice = to_invoice
                group.report_open_quotations = open_quotes
                group.report_total_due = total_due
                group.report_over_credit = max(0.0, total_due - limit)
                group.report_remaining_credit = limit - total_due
                group.report_credit_status = "over" if group.report_over_credit > 0 else "ok"
                if getattr(group, "credit_limit_on_hold", False):
                    group.report_credit_status = "hold"

                group_members = report_companies.filtered(lambda partner: partner.company_group_id.id == group.id)
                if group_members:
                    oldest_dates = [
                        oldest_unpaid.get(member.id)
                        for member in group_members
                        if oldest_unpaid.get(member.id)
                    ]
                    if oldest_dates:
                        group.report_oldest_unpaid_invoice_date = min(oldest_dates)

                    last_dates = [
                        last_paid.get(member.id)
                        for member in group_members
                        if last_paid.get(member.id)
                    ]
                    if last_dates:
                        group.report_last_payment_date = max(last_dates)

                    if amounts["dso_den"]:
                        group.report_days_sales_outstanding = amounts["dso_num"] / amounts["dso_den"]
                    else:
                        group.report_days_sales_outstanding = sum(
                            (member.days_sales_outstanding or 0.0) for member in group_members
                        ) / len(group_members)

        for company_partner in companies.with_company(company):
            outstanding = company_partner.credit or 0.0
            to_invoice = so_approved_totals.get(company_partner.id, 0.0)
            open_quotes = quotation_totals.get(company_partner.id, 0.0)
            total_due = outstanding + to_invoice + open_quotes
            limit = company_partner.credit_limit or 0.0
            company_partner.report_outstanding = outstanding
            company_partner.report_to_invoice = to_invoice
            company_partner.report_open_quotations = open_quotes
            company_partner.report_total_due = total_due
            company_partner.report_over_credit = max(0.0, total_due - limit)
            company_partner.report_remaining_credit = limit - total_due
            company_partner.report_credit_status = "over" if company_partner.report_over_credit > 0 else "ok"
            if getattr(company_partner, "credit_limit_on_hold", False):
                company_partner.report_credit_status = "hold"
            company_partner.report_oldest_unpaid_invoice_date = oldest_unpaid.get(company_partner.id)
            company_partner.report_last_payment_date = last_paid.get(company_partner.id)
            company_partner.report_days_sales_outstanding = company_partner.days_sales_outstanding or 0.0

    @api.onchange("is_company_group")
    def _onchange_is_company_group(self):
        for partner in self:
            if partner.is_company_group:
                partner.company_type = "company"
                partner.company_group_id = False

    @api.onchange("company_type")
    def _onchange_company_type(self):
        for partner in self:
            if partner.company_type != "company":
                partner.is_company_group = False
                partner.company_group_id = False

    # Constraints removed per requirement: allow flexible assignments.

    def _get_company_group_partner(self):
        self.ensure_one()
        return self.company_group_id or self

    def _get_company_group_members(self):
        self.ensure_one()
        group_partner = self._get_company_group_partner()
        return self.with_context(active_test=False).search([("company_group_id", "=", group_partner.id)])

    def _get_company_group_companies(self):
        self.ensure_one()
        group_partner = self._get_company_group_partner()
        return self.with_context(active_test=False).search(
            [
                ("company_group_id", "=", group_partner.id),
                ("company_type", "=", "company"),
                ("is_company_group", "=", False),
            ]
        )

    def _get_company_group_credit_limit(self):
        self.ensure_one()
        companies = self._get_company_group_companies()
        if companies:
            return sum(companies.mapped("credit_limit"))
        return float(self._get_company_group_partner().credit_limit or 0.0)
