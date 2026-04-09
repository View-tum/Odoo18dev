from odoo import models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _create_invoices(self, grouped=False, final=False, date=None):
        moves = super()._create_invoices(grouped=grouped, final=final, date=date)
        draft_moves = moves.filtered(lambda m: m.state == "draft")
        if draft_moves:
            try:
                # Auto-confirm invoices created from sales
                draft_moves.action_post()
            except UserError:
                # If posting fails (e.g., missing accounts), leave drafts as-is
                pass
        return moves

