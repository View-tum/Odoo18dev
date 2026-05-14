# -*- coding: utf-8 -*-
# Copyright (C) 2020-today ITAAS (Dev K.Book)

from odoo import models, fields, api


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    number = fields.Integer()


class StockMove(models.Model):
    _inherit = 'stock.move'

    number = fields.Integer()
    gm_lot_display = fields.Char(
        string='Lot Summary',
        compute='_compute_gm_lot_display',
    )

    @api.depends('move_line_ids.lot_id', 'move_line_ids.lot_name', 'move_line_ids.quantity')
    def _compute_gm_lot_display(self):
        for move in self:
            lot_names = []
            # Keep the one2many order coming from the form to avoid sorting NewId
            # records during onchange before the lines are saved.
            for line in move.move_line_ids:
                if not line.quantity:
                    continue
                lot_name = line.lot_id.name or line.lot_name
                if lot_name and lot_name not in lot_names:
                    lot_names.append(lot_name)
            move.gm_lot_display = ', '.join(lot_names)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_number_line = fields.Boolean(compute='get_number', store=True, compute_sudo=True)

    @api.depends('move_ids', 'move_ids.sequence', 'move_line_ids')
    def get_number(self):
        for obj in self:
            number = 1
            for sm in obj.move_ids.filtered(lambda x: x.product_id).sorted(lambda x: x.sequence):
                sm.number = number
                number += 1
            number = 1
            for sml in obj.move_line_ids.filtered(lambda x: x.product_id):
                sml.number = number
                number += 1
            obj.is_number_line = True
