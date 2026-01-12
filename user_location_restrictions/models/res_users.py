# -*- coding: utf-8 -*-
from odoo import api, fields, models

class ResUsers(models.Model):
    _inherit = "res.users"

    allowed_warehouse_ids = fields.Many2many(
        "stock.warehouse",
        "res_users_stock_warehouse_rel",
        "user_id",
        "warehouse_id",
        string="Allowed Warehouses",
        help="Warehouses this user can access (when 'Inventory Location Restricted' group is enabled).",
    )

    allowed_location_ids = fields.Many2many(
        "stock.location",
        "res_users_stock_location_rel",
        "user_id",
        "location_id",
        string="Allowed Locations",
        domain="[('usage','in',('internal','view','transit'))]",
        help="Root/internal locations this user can access, including their child locations.",
    )

    allowed_picking_type_ids = fields.Many2many(
        "stock.picking.type",
        "res_users_stock_picking_type_rel",
        "user_id",
        "picking_type_id",
        string="Allowed Operation Types",
        help="Operation types (Picking Types) this user can access.",
    )

    @api.onchange('allowed_warehouse_ids')
    def _onchange_allowed_warehouse_ids(self):
        # Convenience: when warehouses are selected, suggest operation types belonging to them
        for user in self:
            if user.allowed_warehouse_ids:
                pts = self.env['stock.picking.type'].search([('warehouse_id', 'in', user.allowed_warehouse_ids.ids)])
                user.allowed_picking_type_ids = [(6, 0, pts.ids)]