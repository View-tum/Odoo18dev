# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import models


class Move(models.Model):
    _inherit = 'stock.move'

    def _check_stock_account_installed(self):
        stock_account_app = self.env['ir.module.module'].sudo().search(
            [('name', '=', 'stock_account')], limit=1)
        if stock_account_app.state != 'installed':
            return False
        else:
            return True

    # def _sh_unreseve_qty(self):
    #     for move_line in self.sudo().mapped('move_line_ids'):
    #         if move_line.state not in ['draft', 'cancel', 'assigned', 'waiting']:
    #             if move_line.product_id.type != 'consu':
    #                 continue
    #             # unreserve qty
    #             quant = self.env['stock.quant'].sudo().search([('location_id', '=', move_line.location_id.id),
    #                                                            ('product_id', '=',move_line.product_id.id),
    #                                                            ('lot_id', '=', move_line.lot_id.id)], limit=1)

    #             if quant:
    #                 quant.write(
    #                     {'quantity': quant.quantity + move_line.quantity})
    #             else:
    #                 self.env['stock.quant'].sudo().create({'location_id': move_line.location_id.id,
    #                                                        'product_id': move_line.product_id.id,
    #                                                        'lot_id': move_line.lot_id.id,
    #                                                        'quantity': move_line.quantity
    #                                                        })

    #             quant = self.env['stock.quant'].sudo().search([('location_id', '=', move_line.location_dest_id.id),
    #                                                            ('product_id', '=',move_line.product_id.id),
    #                                                            ('lot_id', '=', move_line.lot_id.id)], limit=1)

    #             if quant:
    #                 quant.write(
    #                     {'quantity': quant.quantity - move_line.quantity})
    #             else:
    #                 self.env['stock.quant'].sudo().create({'location_id': move_line.location_dest_id.id,
    #                                                        'product_id': move_line.product_id.id,
    #                                                        'lot_id': move_line.lot_id.id,
    #                                                        'quantity': move_line.quantity * (-1)
    #                                                        })

    def _sh_unreseve_qty(self):
        for move_line in self.sudo().mapped('move_line_ids'):
            if move_line.state not in ['draft', 'cancel', 'assigned', 'waiting']:
                # Check if the product has inventory tracking
                if move_line.product_id.tracking == 'none':  # 'none' means no inventory tracking
                    continue  # Skip this move line if the product doesn't have tracking enabled
                
                # Unreserve qty for products that have inventory tracking (by lot, serial, or quantity)
                quant = self.env['stock.quant'].sudo().search([
                    ('location_id', '=', move_line.location_id.id),
                    ('product_id', '=', move_line.product_id.id),
                    ('lot_id', '=', move_line.lot_id.id)
                ], limit=1)

                if quant:
                    quant.write({'quantity': quant.quantity + move_line.quantity})
                else:
                    self.env['stock.quant'].sudo().create({
                        'location_id': move_line.location_id.id,
                        'product_id': move_line.product_id.id,
                        'lot_id': move_line.lot_id.id,
                        'quantity': move_line.quantity
                    })

                quant = self.env['stock.quant'].sudo().search([
                    ('location_id', '=', move_line.location_dest_id.id),
                    ('product_id', '=', move_line.product_id.id),
                    ('lot_id', '=', move_line.lot_id.id)
                ], limit=1)

                if quant:
                    quant.write({'quantity': quant.quantity - move_line.quantity})
                else:
                    self.env['stock.quant'].sudo().create({
                        'location_id': move_line.location_dest_id.id,
                        'product_id': move_line.product_id.id,
                        'lot_id': move_line.lot_id.id,
                        'quantity': move_line.quantity * (-1)
                    })


    def action_move_cancel(self):
        for rec in self:
            rec._sh_unreseve_qty()
            rec.sudo().write({'state': 'cancel'})
            rec.mapped('move_line_ids').sudo().write({'state': 'cancel'})

            if rec._check_stock_account_installed():
                # cancel related accouting entries
                account_move = rec.sudo().mapped('account_move_ids')
                account_move_line_ids = account_move.sudo().mapped('line_ids')
                reconcile_ids = []
                if account_move_line_ids:
                    reconcile_ids = account_move_line_ids.sudo().mapped('id')
                reconcile_lines = self.env['account.partial.reconcile'].sudo().search(
                    ['|', ('credit_move_id', 'in', reconcile_ids), ('debit_move_id', 'in', reconcile_ids)])
                if reconcile_lines:
                    reconcile_lines.sudo().unlink()
                account_move.mapped(
                    'line_ids.analytic_line_ids').sudo().unlink()
                account_move.sudo().write({'state': 'draft', 'name': '/'})
                account_move.sudo().with_context(**{'force_delete': True}).unlink()

                # cancel stock valuation
                stock_valuation_layer_ids = rec.sudo().mapped('stock_valuation_layer_ids')
                if stock_valuation_layer_ids:
                    stock_valuation_layer_ids.sudo().unlink()

    def action_move_cancel_draft(self):
        for rec in self:
            rec._sh_unreseve_qty()
            rec.sudo().write({'state': 'draft'})
            rec.mapped('move_line_ids').sudo().write({'state': 'draft'})

            if rec._check_stock_account_installed():
                # cancel related accouting entries
                account_move = rec.sudo().mapped('account_move_ids')
                account_move_line_ids = account_move.sudo().mapped('line_ids')
                reconcile_ids = []
                if account_move_line_ids:
                    reconcile_ids = account_move_line_ids.sudo().mapped('id')
                reconcile_lines = self.env['account.partial.reconcile'].sudo().search(
                    ['|', ('credit_move_id', 'in', reconcile_ids), ('debit_move_id', 'in', reconcile_ids)])
                if reconcile_lines:
                    reconcile_lines.sudo().unlink()
                account_move.mapped(
                    'line_ids.analytic_line_ids').sudo().unlink()
                account_move.sudo().write({'state': 'draft', 'name': '/'})
                account_move.sudo().with_context(**{'force_delete': True}).unlink()

                # cancel stock valuation
                stock_valuation_layer_ids = rec.sudo().mapped('stock_valuation_layer_ids')
                if stock_valuation_layer_ids:
                    stock_valuation_layer_ids.sudo().unlink()

    def action_move_cancel_delete(self):
        for rec in self:
            rec._sh_unreseve_qty()
            rec.sudo().write({'state': 'draft'})
            rec.mapped('move_line_ids').sudo().write({'state': 'draft'})

            if rec._check_stock_account_installed():
                # cancel related accouting entries
                account_move = rec.sudo().mapped('account_move_ids')
                account_move_line_ids = account_move.sudo().mapped('line_ids')
                reconcile_ids = []
                if account_move_line_ids:
                    reconcile_ids = account_move_line_ids.sudo().mapped('id')
                reconcile_lines = self.env['account.partial.reconcile'].sudo().search(
                    ['|', ('credit_move_id', 'in', reconcile_ids), ('debit_move_id', 'in', reconcile_ids)])
                if reconcile_lines:
                    reconcile_lines.sudo().unlink()
                account_move.mapped(
                    'line_ids.analytic_line_ids').sudo().unlink()
                account_move.sudo().write({'state': 'draft', 'name': '/'})
                account_move.sudo().with_context(**{'force_delete': True}).unlink()

                # cancel stock valuation
                stock_valuation_layer_ids = rec.sudo().mapped('stock_valuation_layer_ids')
                if stock_valuation_layer_ids:
                    stock_valuation_layer_ids.sudo().unlink()

            rec.mapped('move_line_ids').sudo().unlink()
            rec.sudo().unlink()
