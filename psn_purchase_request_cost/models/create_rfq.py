from odoo import models, fields, api


class PurchaseRequestLineMakePurchaseOrderItem(models.TransientModel):
    _inherit = ["purchase.request.line.make.purchase.order.item"]  # Correct the inherited model

    cost = fields.Float(
        string="Cost",
        compute="_compute_cost",
        store=True
    )

    @api.depends('line_id')
    def _compute_cost(self):
        for item in self:
            item.cost = item.line_id.unit_cost if item.line_id else 0.0
