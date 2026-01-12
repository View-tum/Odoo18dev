# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockReturnPicking(models.TransientModel):
    _inherit = "stock.return.picking"

    location_id = fields.Many2one(
        "stock.location",
        string="Return Location",
        domain=[("usage", "=", "internal")],
        help="Destination location for returned products.",
    )

    def _prepare_picking_default_values(self):
        self.ensure_one()
        vals = super()._prepare_picking_default_values()
        if self.location_id:
            vals["location_dest_id"] = self.location_id.id
        return vals

    def _prepare_picking_default_values_based_on(self, picking):
        self.ensure_one()
        vals = super()._prepare_picking_default_values_based_on(picking)
        if self.location_id:
            vals["location_dest_id"] = self.location_id.id
        return vals
