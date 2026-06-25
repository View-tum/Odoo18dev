from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    original_discount_amount = fields.Float(
        string="Original Discount Amount",
        help="Legacy stored discount amount retained for existing documents.",
    )
    apportioned_discount = fields.Monetary(
        string="Apportioned Discount",
        currency_field="currency_id",
        compute="_compute_apportioned_discount",
        help="Informational allocation of visible discount lines to asset lines.",
    )

    @api.depends(
        "order_id.order_line.price_subtotal",
        "order_id.order_line.product_id",
        "order_id.order_line.product_id.product_tmpl_id.is_apportion_discount",
        "order_id.order_line.product_id.categ_id.is_fixed_asset",
    )
    def _compute_apportioned_discount(self):
        for line in self:
            line.apportioned_discount = 0.0
        for order in self.mapped("order_id"):
            allocations = order._get_asset_discount_allocations()
            for line in self.filtered(lambda current: current.order_id == order):
                line.apportioned_discount = allocations.get(line.id, 0.0)


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    total_apportioned_discount = fields.Monetary(
        string="Total Apportioned Discount",
        currency_field="currency_id",
        compute="_compute_total_apportioned_discount",
        help="Informational total allocated from visible discount lines.",
    )

    @api.depends(
        "order_line.price_subtotal",
        "order_line.product_id",
        "order_line.product_id.product_tmpl_id.is_apportion_discount",
        "order_line.product_id.categ_id.is_fixed_asset",
    )
    def _compute_total_apportioned_discount(self):
        for order in self:
            order.total_apportioned_discount = sum(
                order._get_asset_discount_allocations().values()
            )

    def _get_asset_discount_allocations(self):
        self.ensure_one()
        discount_lines = self.order_line.filtered(
            lambda line: (
                line.product_id.product_tmpl_id.is_apportion_discount
                and line.price_subtotal < 0
            )
        )
        asset_lines = self.order_line.filtered(
            lambda line: (
                line.product_id.categ_id.is_fixed_asset
                and not line.product_id.product_tmpl_id.is_apportion_discount
                and line.price_subtotal > 0
            )
        )
        discount_amount = -sum(discount_lines.mapped("price_subtotal"))
        asset_amount = sum(asset_lines.mapped("price_subtotal"))
        if not discount_amount or not asset_amount:
            return {}

        allocations = {}
        remaining = discount_amount
        for line in asset_lines[:-1]:
            allocation = self.currency_id.round(
                discount_amount * line.price_subtotal / asset_amount
            )
            allocations[line.id] = allocation
            remaining -= allocation
        allocations[asset_lines[-1].id] = self.currency_id.round(remaining)
        return allocations

    def _get_apportion_discount_lines(self):
        return self.order_line.filtered(
            lambda line: line.product_id.product_tmpl_id.is_apportion_discount
        )

    def _receive_apportion_discount_lines(self):
        for line in self._get_apportion_discount_lines().filtered(
            lambda current: (
                current.product_id.type == "service"
                and current.qty_received != current.product_qty
            )
        ):
            line.qty_received = line.product_qty

    def button_confirm(self):
        result = super().button_confirm()
        self.filtered(
            lambda order: order.state in ("purchase", "done")
        )._receive_apportion_discount_lines()
        return result

    def write(self, vals):
        result = super().write(vals)
        if vals.get("state") in ("purchase", "done"):
            self._receive_apportion_discount_lines()
        return result

    def action_apportion_discount(self):
        self.ensure_one()
        if not self._get_apportion_discount_lines().filtered(
            lambda line: line.price_subtotal < 0
        ):
            raise UserError(
                _(
                    "No negative discount line was found. Add a product marked "
                    "'Treat as Apportion Discount' with a negative amount."
                )
            )
        return True
