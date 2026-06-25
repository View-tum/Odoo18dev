from odoo import _, fields, models
from odoo.exceptions import UserError


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    apportioned_asset_line_id = fields.Many2one(
        "account.move.line",
        string="Apportioned Asset Line",
        copy=False,
        readonly=True,
    )


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_asset_creation_lines(self):
        if hasattr(super(), "_get_asset_creation_lines"):
            return super()._get_asset_creation_lines().filtered(
                lambda line: not line.product_id.product_tmpl_id.is_apportion_discount
            )
        return self.invoice_line_ids.filtered(
            lambda line: line.product_id.categ_id.is_fixed_asset
            and not line.product_id.product_tmpl_id.is_apportion_discount
        )

    def _get_asset_discount_allocations(self):
        self.ensure_one()
        discount_lines = self.invoice_line_ids.filtered(
            lambda line: (
                line.product_id.product_tmpl_id.is_apportion_discount
                and line.price_subtotal < 0
            )
        )
        asset_lines = self._get_asset_creation_lines().filtered(
            lambda line: line.price_subtotal > 0
        )
        discount_amount = -sum(discount_lines.mapped("price_subtotal"))
        asset_amount = sum(asset_lines.mapped("price_subtotal"))
        if not discount_amount or not asset_amount:
            return {}
        if self.currency_id.compare_amounts(discount_amount, asset_amount) > 0:
            raise UserError(
                _("The apportioned discount cannot exceed the fixed asset value.")
            )

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

    def _get_asset_amounts_for_bill_line(self, line, num_assets):
        allocation = self._get_asset_discount_allocations().get(line.id, 0.0)
        if not allocation:
            if hasattr(super(), "_get_asset_amounts_for_bill_line"):
                return super()._get_asset_amounts_for_bill_line(line, num_assets)
            amount = line.price_subtotal / num_assets if num_assets > 0 else line.price_subtotal
            return [amount] * num_assets

        total_amount = line.price_subtotal - allocation
        if num_assets <= 1:
            return [total_amount]

        amount = self.currency_id.round(total_amount / num_assets)
        amounts = [amount] * (num_assets - 1)
        amounts.append(self.currency_id.round(total_amount - sum(amounts)))
        return amounts

    def _get_asset_source_lines(self, line):
        discount_lines = self.invoice_line_ids.filtered(
            lambda discount_line: discount_line.apportioned_asset_line_id == line
        )
        if hasattr(super(), "_get_asset_source_lines"):
            return super()._get_asset_source_lines(line) | discount_lines
        return line | discount_lines

    def _allocate_discount_line_to_assets(self, discount_line, asset_lines, asset_amount):
        discount_amount = -discount_line.price_subtotal
        original_quantity = discount_line.quantity
        remaining = discount_amount
        values = []
        for asset_line in asset_lines[:-1]:
            allocation = self.currency_id.round(
                discount_amount * asset_line.price_subtotal / asset_amount
            )
            values.append((asset_line, allocation))
            remaining -= allocation
        values.append((asset_lines[-1], self.currency_id.round(remaining)))

        first_line_values = False
        for index, (asset_line, allocation) in enumerate(values):
            line_values = {
                "name": _("%(discount)s - Allocation: %(asset)s", discount=discount_line.name, asset=asset_line.name),
                "quantity": original_quantity * allocation / discount_amount,
                "apportioned_asset_line_id": asset_line.id,
            }
            if index:
                discount_line.copy(line_values)
            else:
                first_line_values = line_values
        discount_line.write(first_line_values)

    def _prepare_apportioned_asset_discount_lines(self):
        for move in self:
            if move.move_type != "in_invoice" or move.state != "draft":
                continue
            asset_lines = move._get_asset_creation_lines().filtered(
                lambda line: line.price_subtotal > 0
            )
            discount_lines = move.invoice_line_ids.filtered(
                lambda line: (
                    line.product_id.product_tmpl_id.is_apportion_discount
                    and line.price_subtotal < 0
                    and not line.apportioned_asset_line_id
                )
            )
            if not asset_lines or not discount_lines:
                continue
            move._get_asset_discount_allocations()
            asset_amount = sum(asset_lines.mapped("price_subtotal"))
            for discount_line in discount_lines:
                move._allocate_discount_line_to_assets(
                    discount_line, asset_lines, asset_amount
                )

    def action_post(self):
        self._prepare_apportioned_asset_discount_lines()
        return super().action_post()
