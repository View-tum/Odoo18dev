# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class StockPicking(models.Model):
    _inherit = "stock.picking"

    def action_create_product_transform(self):
        """Open the Product Transform form with data from this picking."""
        self.ensure_one()
        source_location = (
            self.location_id
            if self.picking_type_code == "outgoing"
            else self.location_dest_id
        )
        
        ctx = {
            'default_picking_id': self.id,
            'default_source_ref': f"{self.name} ({self.origin})" if self.origin else self.name,
            'default_location_id': source_location.id,
        }
        
        return {
            'name': _('Create Product Transform'),
            'type': 'ir.actions.act_window',
            'res_model': 'product.transform',
            'view_mode': 'form',
            'context': ctx,
            'target': 'current',
        }

    def action_create_rma_transform_return(self):
        self.ensure_one()
        if self.state != "done" or self.picking_type_code != "outgoing":
            return False
        return {
            "name": _("RMA Transform Return"),
            "type": "ir.actions.act_window",
            "res_model": "rma.transform.return",
            "view_mode": "form",
            "context": {},
            "target": "current",
        }
