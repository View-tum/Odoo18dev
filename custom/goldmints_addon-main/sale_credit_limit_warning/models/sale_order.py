from collections import defaultdict

from markupsafe import escape

from odoo import api, fields, models, _
from odoo.tools import formatLang


class SaleOrder(models.Model):
    _inherit = "sale.order"

    credit_banner_mode = fields.Selection(
        selection=[
            ("auto", "Auto"),
            ("show", "Show"),
            ("hide", "Hide"),
        ],
        string="Credit Banner Mode",
        default="auto",
        copy=False,
        help="Auto: show when over limit. Show/Hide: manually force visibility.",
    )
    partner_credit_warning_html = fields.Html(
        string="Credit Warning Details",
        compute="_compute_partner_credit_warning",
        sanitize=False,
    )

    def action_check_credit(self):
        """Toggle banner visibility between Show and Hide."""
        for order in self:
            if order.credit_banner_mode == "show":
                order.credit_banner_mode = "hide"
            else:
                order.credit_banner_mode = "show"
        return {"type": "ir.actions.client", "tag": "reload"}

    def _company_amount_for_order(self, order, company):
        order_currency = order.currency_id or company.currency_id
        conversion_date = order.date_order or fields.Date.context_today(order)
        return order_currency._convert(
            order.amount_total or 0.0,
            company.currency_id,
            company,
            conversion_date,
        )

    def _get_group_partner_and_members(self, customer, company):
        customer = customer.sudo().with_company(company).commercial_partner_id
        group_partner = customer.company_group_id.sudo().with_company(company)

        partner_obj = self.env["res.partner"].sudo().with_company(company).with_context(active_test=False)
        group_members = self.env["res.partner"]
        if group_partner:
            group_members = partner_obj.search([
                ("company_group_id", "=", group_partner.id),
                ("company_type", "=", "company"),
            ])

        if not group_members:
            group_members = customer if customer.company_type == "company" else customer.commercial_partner_id
            group_partner = group_partner or group_members

        return group_partner, group_members.sudo().with_company(company)

    def _get_pending_invoiced_amount_map(self, company, commercial_partner_ids):
        result = defaultdict(float)
        if not commercial_partner_ids:
            return result

        pending_invoices = self.env["account.move"].sudo().with_company(company).search([
            ("company_id", "=", company.id),
            ("state", "=", "posted"),
            ("move_type", "in", ("out_invoice", "out_refund")),
            ("payment_state", "not in", ("paid", "reversed")),
            ("commercial_partner_id", "in", commercial_partner_ids),
        ])
        for invoice in pending_invoices:
            pending_amount = (
                invoice.amount_total_signed
                if invoice.payment_state == "in_payment"
                else invoice.amount_residual_signed
            )
            result[invoice.commercial_partner_id.id] += pending_amount
        return result

    def _build_credit_card_html(self, title, status_over, credit_limit, billed, pending_so, current_so, available, currency):
        def _fmt(amount):
            return formatLang(self.env, amount or 0.0, currency_obj=currency)

        status_label = _("Exceeded Credit Limit!!") if status_over else _("Within Credit Limit")
        status_color = "#D92D20" if status_over else "#067647"
        value_color = "#D92D20" if available < 0 else "#101828"

        return f"""
            <div class="border rounded p-2" style="
                background:#F6ECD1;
                border-color:#E6D9B5 !important;
                min-width:340px;
                flex:1 1 340px;
            ">
                <div class="mb-1">
                    <span class="fw-semibold">{escape(title)}:</span>
                    <span style="font-weight:700; color:{status_color}; margin-left:6px;">{escape(status_label)}</span>
                </div>
                <table class="table table-sm mb-0" style="--table-bg: transparent;">
                    <tr><td class="py-0">{escape(_('Credit Limit'))}</td><td class="py-0 text-end">{escape(_fmt(credit_limit))}</td></tr>
                    <tr><td class="py-0">{escape(_('Billed'))}</td><td class="py-0 text-end">{escape(_fmt(billed))}</td></tr>
                    <tr><td class="py-0">{escape(_('Pending SO'))}</td><td class="py-0 text-end">{escape(_fmt(pending_so))}</td></tr>
                    <tr><td class="py-0">{escape(_('This SO'))}</td><td class="py-0 text-end">{escape(_fmt(current_so))}</td></tr>
                    <tr><td class="py-0 fw-semibold">{escape(_('Available'))}</td><td class="py-0 text-end fw-semibold" style="color:{value_color};">{escape(_fmt(available))}</td></tr>
                </table>
            </div>
        """

    @api.depends(
        "company_id",
        "partner_id",
        "amount_total",
        "currency_id",
        "currency_rate",
        "date_order",
        "state",
        "credit_banner_mode",
    )
    def _compute_partner_credit_warning(self):
        for order in self:
            order.partner_credit_warning = ""
            order.partner_credit_warning_html = ""

        orders_to_check = self.filtered(
            lambda o: o.company_id.account_use_credit_limit and o.partner_id and o.state in ("draft", "sent")
        )
        if not orders_to_check:
            return

        for company, company_orders in orders_to_check.grouped(lambda o: o.company_id).items():
            company_orders = company_orders.with_company(company)
            customers = company_orders.mapped("partner_id.commercial_partner_id").sudo().with_company(company)
            if not customers:
                continue

            customer_group_map = {}
            relevant_partner_ids = set(customers.ids)
            for customer in customers:
                has_company_group = bool(customer.company_group_id)
                group_partner, group_members = self._get_group_partner_and_members(customer, company)
                customer_group_map[customer.id] = {
                    "has_company_group": has_company_group,
                    "group_partner": group_partner,
                    "group_members": group_members,
                }
                if has_company_group:
                    relevant_partner_ids.update(group_members.ids)

            invoiced_amounts = self._get_pending_invoiced_amount_map(company, list(relevant_partner_ids))
            so_approved_amounts = self.env["res.partner"]._get_so_approved_amount_map(
                company,
                list(relevant_partner_ids),
            )

            customer_totals_cache = {}
            group_totals_cache = {}
            currency = company.currency_id

            for order in company_orders:
                customer = order.partner_id.commercial_partner_id.sudo().with_company(company)
                group_data = customer_group_map[customer.id]
                has_company_group = group_data["has_company_group"]
                group_partner = group_data["group_partner"]
                group_members = group_data["group_members"]
                current_so_amount = self._company_amount_for_order(order, company)

                if customer.id not in customer_totals_cache:
                    customer_limit = float(customer.credit_limit or 0.0)
                    customer_billed = float(invoiced_amounts.get(customer.id, 0.0))
                    customer_pending_so = float(so_approved_amounts.get(customer.id, 0.0))
                    customer_available = customer_limit - customer_billed - customer_pending_so - current_so_amount
                    customer_totals_cache[customer.id] = {
                        "limit": customer_limit,
                        "billed": customer_billed,
                        "pending_so": customer_pending_so,
                        "available": customer_available,
                    }
                customer_totals = customer_totals_cache[customer.id]

                customer_has_limit = bool(customer_totals["limit"])
                customer_over = customer_has_limit and customer_totals["available"] < 0.0

                group_has_limit = False
                group_over = False
                group_totals = {}
                if has_company_group:
                    group_key = group_partner.id
                    if group_key not in group_totals_cache:
                        # Prefer configured group limit; fallback to sum of member limits.
                        group_limit = float(group_partner.credit_limit or 0.0)
                        if not group_limit and hasattr(group_partner, "_get_company_group_credit_limit"):
                            group_limit = float(group_partner._get_company_group_credit_limit() or 0.0)
                        group_billed = sum(invoiced_amounts.get(member_id, 0.0) for member_id in group_members.ids)
                        group_pending_so = float(sum(so_approved_amounts.get(member_id, 0.0) for member_id in group_members.ids))
                        if group_limit:
                            group_available = group_limit - group_billed - group_pending_so - current_so_amount
                        else:
                            # If no group limit is configured, avoid misleading negative "available".
                            group_available = 0.0
                        group_totals_cache[group_key] = {
                            "limit": group_limit,
                            "billed": group_billed,
                            "pending_so": group_pending_so,
                            "available": group_available,
                        }
                    group_totals = group_totals_cache[group_key]
                    group_has_limit = bool(group_totals["limit"])
                    group_over = group_has_limit and group_totals["available"] < 0.0

                has_alert = customer_over or (has_company_group and group_over)

                if order.credit_banner_mode == "hide":
                    continue
                if not (has_alert or order.credit_banner_mode == "show"):
                    continue

                customer_card = self._build_credit_card_html(
                    _("Status"),
                    customer_over,
                    customer_totals["limit"],
                    customer_totals["billed"],
                    customer_totals["pending_so"],
                    current_so_amount,
                    customer_totals["available"],
                    currency,
                )

                cards_html = [customer_card]
                if has_company_group and (group_totals.get("limit") or order.credit_banner_mode == "show"):
                    group_card = self._build_credit_card_html(
                        _("Group Status"),
                        group_over,
                        group_totals["limit"],
                        group_totals["billed"],
                        group_totals["pending_so"],
                        current_so_amount,
                        group_totals["available"],
                        currency,
                    )
                    cards_html.append(group_card)

                order.partner_credit_warning_html = (
                    "<div style='display:flex; gap:12px; flex-wrap:wrap; width:100%;'>"
                    + "".join(cards_html)
                    + "</div>"
                )
                order.partner_credit_warning = _("Credit details shown")
