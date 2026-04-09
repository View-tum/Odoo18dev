# Copyright 2020 Jarsa Sistemas, S.A. de C.V.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models

class StockRequestOrder(models.Model):
    _inherit = 'stock.request.order'

    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        default=lambda self: self.env.user.partner_id,
    )

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        if self.partner_id and self.stock_request_ids:
            for stock_request in self.stock_request_ids:
                stock_request.partner_id = self.partner_id


