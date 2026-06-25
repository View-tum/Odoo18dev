from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    van_sales_payment_state = fields.Selection(
        [
            ("not_paid", "Not Paid"),
            ("partial", "Partial Paid"),
            ("paid", "Paid"),
        ],
        string="Customer Payment",
        compute="_compute_van_sales_payment_state",
    )
    van_sales_amount_residual = fields.Monetary(
        string="Customer Balance",
        currency_field="currency_id",
        compute="_compute_van_sales_payment_state",
    )
    van_sales_receive_payment_available = fields.Boolean(
        compute="_compute_van_sales_payment_state",
    )

    def _is_mobile_warehouse_order(self):
        target_name = "mobile warehouse"
        return any(
            order.warehouse_id
            and target_name in (order.warehouse_id.name or "").strip().lower()
            for order in self
        )

    def _get_latest_delivery_effective_date(self):
        done_pickings = self.mapped("picking_ids").filtered(
            lambda p: (
                p.state == "done"
                and p.picking_type_id.code == "outgoing"
                and p.date_done
            )
        )
        if not done_pickings:
            return False
        latest_done = max(done_pickings.mapped("date_done"))
        return fields.Date.to_date(latest_done)

    def _get_van_sales_customer_invoices(self):
        self.ensure_one()
        return self.invoice_ids.filtered(
            lambda move: move.state == "posted" and move.move_type == "out_invoice"
        )

    def _get_van_sales_open_payment_invoices(self):
        self.ensure_one()
        return self._get_van_sales_customer_invoices().filtered(
            lambda move: not move.currency_id.is_zero(move.amount_residual)
        )

    @api.depends(
        "invoice_ids",
        "invoice_ids.state",
        "invoice_ids.move_type",
        "invoice_ids.amount_total",
        "invoice_ids.amount_residual",
        "warehouse_id",
    )
    def _compute_van_sales_payment_state(self):
        for order in self:
            currency = order.currency_id or order.company_id.currency_id
            invoices = order._get_van_sales_customer_invoices()
            residual = currency.round(sum(invoices.mapped("amount_residual")))
            total = currency.round(sum(invoices.mapped("amount_total")))
            paid_amount = currency.round(total - residual)

            if invoices and currency.is_zero(residual):
                payment_state = "paid"
            elif invoices and currency.compare_amounts(paid_amount, 0.0) > 0:
                payment_state = "partial"
            else:
                payment_state = "not_paid"

            order.van_sales_payment_state = payment_state
            order.van_sales_amount_residual = residual
            order.van_sales_receive_payment_available = bool(
                order._is_mobile_warehouse_order()
                and invoices
                and currency.compare_amounts(residual, 0.0) > 0
            )

    def action_receive_van_sale_payment(self):
        self.ensure_one()
        invoices = self._get_van_sales_open_payment_invoices()
        if not invoices:
            raise UserError(_("No open posted customer invoice is available for payment."))

        if len(invoices.mapped("company_id")) != 1:
            raise UserError(_("Please receive payment for one company at a time."))
        if len(invoices.mapped("currency_id")) != 1:
            raise UserError(_("Please receive payment for one currency at a time."))
        if len(invoices.mapped("partner_id.commercial_partner_id")) != 1:
            raise UserError(_("Please receive payment for one customer at a time."))

        open_lines = invoices.line_ids.filtered(
            lambda line: line.account_type == "asset_receivable"
            and not line.reconciled
            and line.parent_state == "posted"
        )
        if not open_lines:
            raise UserError(_("No open receivable line is available for payment."))

        action = open_lines.action_register_payment(ctx={"default_group_payment": True})
        context = dict(action.get("context") or {})
        default_journal = (
            self.company_id.mobile_bank_transfer_journal_id
            or self.company_id.mobile_cash_journal_id
            or self.company_id.mobile_cheque_journal_id
        )
        if default_journal:
            context.setdefault("default_journal_id", default_journal.id)
        context.update(
            {
                "active_model": "account.move.line",
                "active_ids": open_lines.ids,
                "default_group_payment": True,
                "van_sales_order_id": self.id,
            }
        )
        action.update(
            {
                "name": _("Receive Payment"),
                "context": context,
                "target": "new",
            }
        )
        return action

    def _create_invoices(self, grouped=False, final=False, date=None):
        moves = super()._create_invoices(grouped=grouped, final=final, date=date)
        draft_moves = moves.filtered(lambda m: m.state == "draft")
        if draft_moves:
            # Align invoice dates with the latest delivery effective date for non-mobile orders.
            for move in draft_moves.filtered(lambda m: m.move_type == "out_invoice"):
                orders = move.invoice_line_ids.sale_line_ids.order_id
                # if not orders or orders._is_mobile_warehouse_order():All warehouse update invoice date to effective date
                #     continue
                effective_date = orders._get_latest_delivery_effective_date()
                if effective_date:
                    move.write({"invoice_date": effective_date, "date": effective_date})
            draft_moves.action_post()
        return moves

    @api.onchange("commitment_date", "expected_date")
    def _onchange_commitment_date(self):
        """Suppress upstream warning about delivery date sooner than expected date."""
        return
