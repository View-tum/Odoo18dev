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
        inverse='_set_gm_lot_display',
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

    def _set_gm_lot_display(self):
        import re
        for move in self:
            if move.state in ('done', 'cancel') or move.product_id.tracking == 'none':
                continue

            input_text = move.gm_lot_display or ""
            # Parse the input text (comma separated or newline)
            raw_names = re.split(r'[,\n]+', input_text)
            new_lot_names = []
            for name in raw_names:
                name = name.strip()
                if name and name not in new_lot_names:
                    new_lot_names.append(name)
            
            move_lines_commands = []
            mls = move.move_line_ids
            existing_lines_by_name = {}
            for ml in mls:
                lname = ml.lot_id.name or ml.lot_name
                if lname:
                    existing_lines_by_name.setdefault(lname, []).append(ml)
            
            # Remove lines for lots not in the string
            for lname, ml_list in existing_lines_by_name.items():
                if lname not in new_lot_names:
                    for ml in ml_list:
                        move_lines_commands.append((2, ml.id, 0))
            
            mls_without_lots = mls.filtered(lambda ml: not ml.lot_id and not ml.lot_name)
            
            # Add or update lines for new lots
            for lname in new_lot_names:
                if lname not in existing_lines_by_name:
                    lot = self.env['stock.lot'].search([
                        ('name', '=', lname),
                        ('product_id', '=', move.product_id.id),
                        ('company_id', '=', move.company_id.id)
                    ], limit=1)
                    
                    if mls_without_lots[:1]:
                        ml = mls_without_lots[:1]
                        vals = {
                            'lot_name': lname,
                            'lot_id': lot.id if lot else False,
                        }
                        # For serial numbers, quantity must be 1. For lots, leave as is (usually 0 to be filled).
                        if not ml.quantity and move.product_id.tracking == 'serial':
                            vals['quantity'] = 1.0
                        move_lines_commands.append((1, ml.id, vals))
                        mls_without_lots -= ml
                    else:
                        move_line_vals = move._prepare_move_line_vals(quantity=0)
                        move_line_vals['lot_id'] = lot.id if lot else False
                        move_line_vals['lot_name'] = lname
                        if move.product_id.tracking == 'serial':
                            move_line_vals['quantity'] = 1.0
                        move_lines_commands.append((0, 0, move_line_vals))
                        
            if move_lines_commands:
                move.write({'move_line_ids': move_lines_commands})



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
