# Copyright 2023 Quartile Limited (https://www.quartile.co)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    is_deposit_move = fields.Boolean(
        string="Is Deposit Move",
        compute="_compute_is_deposit_move",
        help="Technical field to identify deposit bills.",
    )

    @api.depends("line_ids.purchase_line_id.is_deposit")
    def _compute_is_deposit_move(self):
        for move in self:
            move.is_deposit_move = any(
                line.purchase_line_id.is_deposit for line in move.line_ids
            )

    def action_post(self):
        res = super().action_post()
        for line in self.line_ids:
            if not line.purchase_line_id.is_deposit:
                continue
            line.purchase_line_id.taxes_id = line.tax_ids
            line.purchase_line_id.price_unit = line.price_unit
        return res
