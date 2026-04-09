# Copyright 2019 Elico Corp, Dominique K. <dominique.k@elico-corp.com.sg>
# Copyright 2019 Ecosoft Co., Ltd., Kitti U. <kittiu@ecosoft.co.th>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def copy_data(self, default=None):
        if default is None:
            default = {}
        default["order_line"] = [
            (0, 0, line.copy_data()[0])
            for line in self.order_line
            if not line.is_deposit
        ]
        return super().copy_data(default)

    def action_create_invoice(self):
        """Override to return down payment wizard if nothing to bill."""
        # Ensure we are in a state where billing is allowed
        if self.state in ("draft", "sent", "to approve"):
            # Normally standard Odoo blocks this, but if we call it from code we might need a check
            # or just let it fall through if we don't want to support DP in these states.
            # But the button is only visible in 'purchase' and 'done' now.
            pass

        if self.invoice_status == "no":
            action = self.env["ir.actions.actions"]._for_xml_id(
                "purchase_deposit.action_view_purchase_advance_payment_inv"
            )
            action["context"] = {"active_ids": self.ids}
            return action
        return super().action_create_invoice()


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    is_deposit = fields.Boolean(
        string="Is a deposit payment",
        help="Deposit payments are made when creating bills from a purchase"
        " order. They are not copied when duplicating a purchase order.",
    )

    def _prepare_account_move_line(self, move=False):
        res = super()._prepare_account_move_line(move=move)
        if self.is_deposit:
            res["quantity"] = -1 * self.qty_invoiced
        return res
