# -*- coding: utf-8 -*-
from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    sale_smart_button_ids = fields.Many2many(
        comodel_name="sale.order",
        compute="_compute_sale_links",
        string="Sales Orders",
        store=False,
    )
    sale_smart_button_count = fields.Integer(
        compute="_compute_sale_links",
        string="Sales Orders",
        store=False,
    )

    @api.depends(
        "sale_id",
        "move_ids_without_package.sale_line_id",
    )
    def _compute_sale_links(self):
        SaleOrder = self.env["sale.order"]
        for picking in self:
            orders = SaleOrder
            if picking.sale_id:
                orders = picking.sale_id
            else:
                orders = (
                    picking.move_ids_without_package.mapped("sale_line_id.order_id").exists()
                )
            picking.sale_smart_button_ids = orders
            picking.sale_smart_button_count = len(orders)

    def action_view_sale_orders(self):
        self.ensure_one()
        action = {
            "type": "ir.actions.act_window",
            "name": "Sales Orders",
            "res_model": "sale.order",
            "view_mode": "list,form",
            "domain": [("id", "in", self.sale_smart_button_ids.ids)],
            "target": "current",
        }
        if self.sale_smart_button_count == 1:
            action.update({"view_mode": "form", "res_id": self.sale_smart_button_ids.id})
        return action
