from odoo import api, fields, models, _
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit = "sale.order"

    # ---------- Helpers ----------

    def _company_total_from_orders(self, orders, company):
        """Sum the given orders' amount_total converted into the company's currency."""
        total = 0.0
        company_currency = company.currency_id
        today = fields.Date.context_today(self)
        for so in orders:
            # Convert each order total from its currency into the company currency
            date = so.date_order or today
            total += so.currency_id._convert(
                so.amount_total or 0.0,
                company_currency,
                company,
                date,
            )
        return total

    def _pending_quotations_total_company(self, commercial_partner, company, exclude_order_id=None):
        """Sum ALL *other* quotations and unpaid/ uninvoiced sale orders 
        for this commercial partner in company currency.
    
        Includes:
        - Quotations: states 'draft' or 'sent'
        - Sale orders: state 'sale'
            * with invoices not fully paid, OR
            * with no invoices
        """
        SaleOrder = self.env["sale.order"]
    
        # Quotations
        domain = [
            ("state", "in", ["draft", "sent"]),
            ("company_id", "=", company.id),
            ("partner_id.commercial_partner_id", "=", commercial_partner.id),
        ]
        if exclude_order_id:
            if isinstance(exclude_order_id, (list, tuple)):
                domain.append(("id", "not in", exclude_order_id))
            else:
                domain.append(("id", "!=", exclude_order_id))

        orders = SaleOrder.search(domain)
    
        # Sale orders with invoices not fully paid OR no invoices at all
        sale_orders = SaleOrder.search([
            ("state", "=", "sale"),
            ("company_id", "=", company.id),
            ("partner_id.commercial_partner_id", "=", commercial_partner.id),
        ])
        sale_orders = sale_orders.filtered(
            lambda so: not so.invoice_ids or any(inv.payment_state != "paid" for inv in so.invoice_ids)
        )
    
        # Combine both
        others = orders | sale_orders
        return self._company_total_from_orders(others, company)



    def _company_amount_for_order(self, order):
        """This order's total converted to its company's currency."""
        company = order.company_id
        company_currency = company.currency_id
        date = order.date_order or fields.Date.context_today(order)
        return order.currency_id._convert(
            order.amount_total or 0.0,
            company_currency,
            company,
            date,
        )

    # ---------- Onchange warning ----------

    @api.onchange("partner_id", "order_line", "pricelist_id", "currency_id")
    def _onchange_partner_credit_limit_warning(self):
        # Chain with other modules' logic if any
        res = super()._onchange_partner_credit_limit_warning() if hasattr(super(), "_onchange_partner_credit_limit_warning") else {}

        for order in self:
            partner = order.partner_id
            if not partner:
                continue

            commercial_partner = partner.commercial_partner_id
            if not getattr(commercial_partner, "use_partner_credit_limit", False):
                continue

            limit_company_currency = float(getattr(commercial_partner, "credit_limit", 0.0) or 0.0)
            if limit_company_currency <= 0.0:
                continue

            company = order.company_id

            # IMPORTANT in onchange: use _origin.id so we don't double-count this record
            exclude_id = order._origin.id or False

            others_total_company = self._pending_quotations_total_company(
                commercial_partner, company, exclude_order_id=exclude_id
            )
            this_total_company = self._company_amount_for_order(order)
            aggregate_total_company = others_total_company + this_total_company

            if aggregate_total_company > limit_company_currency:
                over_by = aggregate_total_company - limit_company_currency
                company_cur = company.currency_id.name
                msg = _(
                    "Credit limit exceeded for %(partner)s.\n\n"
                    "• Credit limit: %(limit).2f %(cur)s\n"
                    "• Other quotations total: %(others).2f %(cur)s\n"
                    "• This quotation: %(this).2f %(cur)s\n"
                    "• Aggregate quotations: %(agg).2f %(cur)s\n\n"
                    "Over by: %(over).2f %(cur)s. You won't be able to confirm this quotation."
                ) % {
                    "partner": commercial_partner.display_name,
                    "limit": limit_company_currency,
                    "others": others_total_company,
                    "this": this_total_company,
                    "agg": aggregate_total_company,
                    "over": over_by,
                    "cur": company_cur,
                }
                # Odoo expects a dict with 'warning'
                warning = {"warning": {"title": _("Credit Limit Exceeded"), "message": msg}}
                # Merge into res safely
                if res:
                    # prefer our warning if multiple
                    res["warning"] = warning["warning"]
                else:
                    res = warning

        return res

    # ---------- Confirmation block ----------

    def action_confirm(self):
        for order in self:
            partner = order.partner_id
            if not partner:
                continue

            commercial_partner = partner.commercial_partner_id
            if not getattr(commercial_partner, "use_partner_credit_limit", False):
                continue

            limit_company_currency = float(getattr(commercial_partner, "credit_limit", 0.0) or 0.0)
            if limit_company_currency <= 0.0:
                continue

            company = order.company_id

            # Here we use the real DB id (not _origin) since we're confirming a saved record
            others_total_company = self._pending_quotations_total_company(
                commercial_partner, company, exclude_order_id=order.id
            )
            this_total_company = self._company_amount_for_order(order)
            aggregate_total_company = others_total_company + this_total_company

            if aggregate_total_company > limit_company_currency:
                raise UserError(
                    _(
                        "Cannot confirm: credit limit exceeded for %(partner)s.\n\n"
                        "• Credit limit: %(limit).2f %(cur)s\n"
                        "• Other quotations total: %(others).2f %(cur)s\n"
                        "• This quotation: %(this).2f %(cur)s\n"
                        "• Aggregate quotations: %(agg).2f %(cur)s"
                    )
                    % {
                        "partner": commercial_partner.display_name,
                        "limit": limit_company_currency,
                        "others": others_total_company,
                        "this": this_total_company,
                        "agg": aggregate_total_company,
                        "cur": company.currency_id.name,
                    }
                )

        return super(SaleOrder, self).action_confirm()
