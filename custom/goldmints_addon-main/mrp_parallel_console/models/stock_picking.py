# -*- coding: utf-8 -*-

from odoo import models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        for picking in self:
            if picking.state == "done":
                # Find the manufacturing order linked to this picking
                mo = picking.move_ids.move_dest_ids.raw_material_production_id
                if not mo:
                    mo = picking.move_ids.move_orig_ids.raw_material_production_id

                # Fallback to origin string match
                if not mo and picking.origin:
                    mo = self.env["mrp.production"].search([
                        ("name", "=", picking.origin)
                    ], limit=1)

                if mo:
                    # Sync component quantities immediately
                    mo.sudo().action_sync_picked_quantities()
        return res
