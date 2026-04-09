from odoo import api, fields, models
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    is_po_locked = fields.Boolean(compute="_compute_is_po_locked", store=False)

    def _user_can_always_edit(self):
        user = self.env.user
        return user.has_group("account.group_account_user") or user.has_group("base.group_system")

    @api.depends("order_line", "order_line.purchase_request_lines", "origin", "user_id")
    def _compute_is_po_locked(self):
        for order in self:
            if not order.user_id:
                if self.env.user.has_group("account.group_account_user"):
                    order.is_po_locked = False
                else:
                    order.is_po_locked = True
                continue
            if order._user_can_always_edit():
                order.is_po_locked = False
                continue
            lines = order.order_line
            is_pr = False
            if lines:
                model_fields = lines._fields
                if "purchase_request_lines" in model_fields:
                    is_pr = bool(lines.filtered(lambda l: l.purchase_request_lines))
                elif "purchase_request_line_id" in model_fields:
                    is_pr = bool(lines.filtered(lambda l: l.purchase_request_line_id))
            if is_pr:
                order.is_po_locked = True
                continue
            if order.user_id and order.user_id != self.env.user:
                order.is_po_locked = True
                continue
            origin = order.origin or ""
            is_mto_reorder = ("OP" in origin) or ("SO" in origin)
            if is_mto_reorder and order.user_id and order.user_id != self.env.user:
                order.is_po_locked = True
                continue
            order.is_po_locked = False

    def write(self, vals):
        critical_fields = {"partner_id", "order_line", "date_order", "currency_id"}
        if critical_fields.intersection(vals.keys()):
            for order in self:
                if not order.user_id and not self.env.user.has_group("account.group_account_user"):
                    raise UserError("Only Accounting can edit this Purchase Order without a buyer assigned.")
                order._compute_is_po_locked()
                if not order._user_can_always_edit() and order.is_po_locked:
                    raise UserError("You cannot edit this Purchase Order due to locking rules.")
        return super().write(vals)