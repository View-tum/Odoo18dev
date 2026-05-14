from odoo import api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

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
            try:
                # Auto-confirm invoices created from sales
                draft_moves.action_post()
                # 🚀 IMMEDIATE COMMIT: Release ir.sequence_date_range lock instantly!
                # This prevents "could not serialize access due to concurrent update"
                # and stops other users' browsers from freezing.
                self.env.cr.commit()
            except UserError:
                # If posting fails (e.g., missing accounts), leave drafts as-is
                pass
        return moves

    @api.onchange("commitment_date", "expected_date")
    def _onchange_commitment_date(self):
        """Suppress upstream warning about delivery date sooner than expected date."""
        return
