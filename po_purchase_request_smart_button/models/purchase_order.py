from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    pr_ids = fields.Many2many(
        comodel_name="purchase.request",
        compute="_compute_pr_ids",
        string="Purchase Requests",
        store=False,
        help="(365 custom) All Purchase Requests related to this Purchase Order, computed automatically from its lines."
    )
    pr_count = fields.Integer(
        compute="_compute_pr_ids",
        string="PR Count",
        store=False,
        help="(365 custom) The number of Purchase Requests linked to this Purchase Order."
    )

    @api.depends("order_line", "order_line.purchase_request_lines")
    def _compute_pr_ids(self):
        for po in self:
            prs = po.order_line.mapped("purchase_request_lines.request_id").exists()
            po.pr_ids = prs
            po.pr_count = len(prs)

    def action_view_prs(self):
        self.ensure_one()
        action = {
            "type": "ir.actions.act_window",
            "name": "Purchase Requests",
            "res_model": "purchase.request",
            "view_mode": "tree,form",
            "domain": [("id", "in", self.pr_ids.ids)],
            "target": "current",
        }
        if self.pr_count == 1:
            action.update({"view_mode": "form", "res_id": self.pr_ids.id})
        return action
