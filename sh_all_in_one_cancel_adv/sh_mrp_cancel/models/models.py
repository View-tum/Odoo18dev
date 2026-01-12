# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import models


class Move(models.Model):
    _inherit = 'stock.move'

    def _sh_unreseve_qty(self):
        for move_line in self.sudo().mapped('move_line_ids'):
            # unreserve qty

            quant = self.env['stock.quant'].sudo().search([('location_id', '=', move_line.location_id.id),
                                                           ('product_id', '=',move_line.product_id.id),
                                                           ('lot_id', '=', move_line.lot_id.id)], limit=1)

            if quant:
                quant.write({'quantity': quant.quantity + move_line.quantity})

            quant = self.env['stock.quant'].sudo().search([('location_id', '=', move_line.location_dest_id.id),
                                                           ('product_id', '=',move_line.product_id.id),
                                                           ('lot_id', '=', move_line.lot_id.id)], limit=1)

            if quant:
                quant.write({'quantity': quant.quantity - move_line.quantity})


class Production(models.Model):
    _inherit = 'mrp.production'

    def action_mrp_cancel(self):
        for rec in self:
            if rec.company_id.cancel_child_mo:

                domain = [('origin', '=', rec.name)]
                find_child_mo = self.env['mrp.production'].search(domain)
                print(f"=\n\n=>> find_child_mo: {find_child_mo}")
                if find_child_mo:
                    for data in find_child_mo:
                        data.action_mrp_cancel()
            # rec.process_action_mrp_cancel()

            
            if rec.sudo().mapped('move_raw_ids'):
                rec.sudo().mapped('move_raw_ids').sudo().write(
                    {'state': 'cancel'})
                rec.sudo().mapped('move_raw_ids').mapped(
                    'move_line_ids').sudo().write({'state': 'cancel'})
                rec.sudo().mapped('move_raw_ids')._sh_unreseve_qty()
            if rec._check_account_installed():
                if rec.sudo().mapped('move_raw_ids').mapped('account_move_ids'):
                    accounting_ids = rec.sudo().mapped('move_raw_ids').mapped('account_move_ids')
                    accounting_ids.sudo().write({'state':'cancel','name':'/'})
                    # accounting_ids.sudo().unlink()
                    accounting_ids.sudo().mapped('line_ids').sudo().write({'parent_state':'draft'})
                    accounting_ids.sudo().mapped('line_ids').sudo().unlink()
                

            if rec.sudo().mapped('workorder_ids'):
                rec.sudo().mapped('workorder_ids').write({'state': 'cancel'})

            if rec.sudo().mapped('move_byproduct_ids'):
                rec.sudo().mapped('move_byproduct_ids').sudo().write(
                    {'state': 'cancel'})
                rec.sudo().mapped('move_byproduct_ids').mapped(
                    'move_line_ids').sudo().write({'state': 'cancel'})
                rec.sudo().mapped('move_byproduct_ids')._sh_unreseve_qty()
                if rec._check_account_installed():
                    if rec.sudo().mapped('move_byproduct_ids').mapped('account_move_ids'):
                        accounting_ids = rec.sudo().mapped('move_byproduct_ids').mapped('account_move_ids')
                        accounting_ids.sudo().write({'state':'cancel','name':'/'})
                        # accounting_ids.sudo().unlink()
                        accounting_ids.sudo().mapped('line_ids').sudo().write({'parent_state':'draft'})
                        accounting_ids.sudo().mapped('line_ids').sudo().unlink()

            if rec.sudo().mapped('move_dest_ids'):
                rec.sudo().mapped('move_dest_ids').sudo().write(
                    {'state': 'cancel'})
                rec.sudo().mapped('move_dest_ids').mapped(
                    'move_line_ids').sudo().write({'state': 'cancel'})
                rec.sudo().mapped('move_dest_ids')._sh_unreseve_qty()
                if rec._check_account_installed():
                    if rec.sudo().mapped('move_dest_ids').mapped('account_move_ids'):
                        accounting_ids = rec.sudo().mapped('move_dest_ids').mapped('account_move_ids')
                        accounting_ids.sudo().write({'state':'cancel','name':'/'})
                        # accounting_ids.sudo().unlink()
                        accounting_ids.sudo().mapped('line_ids').sudo().write({'parent_state':'draft'})
                        accounting_ids.sudo().mapped('line_ids').sudo().unlink()

            if rec.sudo().mapped('move_finished_ids'):
                rec.sudo().mapped('move_finished_ids').sudo().write(
                    {'state': 'cancel'})
                rec.sudo().mapped('move_finished_ids').mapped(
                    'move_line_ids').sudo().write({'state': 'cancel'})
                rec.sudo().mapped('move_finished_ids')._sh_unreseve_qty()
                
                if rec._check_account_installed():
                    if rec.sudo().mapped('move_finished_ids').mapped('account_move_ids'):
                        accounting_ids = rec.sudo().mapped('move_finished_ids').mapped('account_move_ids')
                        accounting_ids.sudo().write({'state':'cancel','name':'/'})
                        # accounting_ids.sudo().unlink()
                        accounting_ids.sudo().mapped('line_ids').sudo().write({'parent_state':'draft'})
                        accounting_ids.sudo().mapped('line_ids').sudo().unlink()

            if rec.sudo().mapped('finished_move_line_ids'):
                rec.sudo().mapped('finished_move_line_ids').sudo().write(
                    {'state': 'cancel'})
                
            if rec.sudo().mapped('picking_ids'):
                rec.sudo().mapped('picking_ids').mapped(
                    'move_ids_without_package').sudo().write({'state': 'cancel'})
                rec.sudo().mapped('picking_ids').mapped('move_ids_without_package').mapped(
                    'move_line_ids').sudo().write({'state': 'cancel'})
                rec.sudo().mapped('picking_ids').mapped(
                    'move_ids_without_package')._sh_unreseve_qty()

                rec.sudo().mapped('picking_ids').write({'state': 'cancel'})

            rec.sudo().write({'state': 'cancel'})

    def action_mrp_cancel_draft(self):
        for rec in self:

            if rec.company_id.cancel_child_mo:
                domain = [('origin', '=', rec.name)]
                find_child_mo = self.env['mrp.production'].search(domain)
                if find_child_mo:
                    for data in find_child_mo:
                        data.action_mrp_cancel_draft()
            # rec.process_action_mrp_cancel_draft()

            if rec.sudo().mapped('move_raw_ids'):
                rec.sudo().mapped('move_raw_ids').sudo().write(
                    {'state': 'draft'})
                rec.sudo().mapped('move_raw_ids').mapped(
                    'move_line_ids').sudo().write({'state': 'draft'})
                rec.sudo().mapped('move_raw_ids')._sh_unreseve_qty()
            
            # 
            if self._check_account_installed():
                rec.sudo().mapped('move_raw_ids').mapped(
                'stock_valuation_layer_ids').sudo().unlink()
                if rec.sudo().mapped('move_raw_ids').mapped('account_move_ids'):
                    accounting_ids = rec.sudo().mapped('move_raw_ids').mapped('account_move_ids')
                    accounting_ids.sudo().write({'state':'draft','name':'/'})
                    # accounting_ids.sudo().unlink()
                    accounting_ids.sudo().mapped('line_ids').sudo().write({'parent_state':'draft'})
                    accounting_ids.sudo().mapped('line_ids').sudo().unlink()

            if rec.sudo().mapped('workorder_ids'):
                rec.sudo().mapped('workorder_ids').write({'state': 'ready'})

            if rec.sudo().mapped('move_byproduct_ids'):
                rec.sudo().mapped('move_byproduct_ids').sudo().write(
                    {'state': 'draft'})
                rec.sudo().mapped('move_byproduct_ids').mapped(
                    'move_line_ids').sudo().write({'state': 'draft'})
                rec.sudo().mapped('move_byproduct_ids')._sh_unreseve_qty()
                
                    
                if self._check_account_installed():
                    rec.sudo().mapped('move_byproduct_ids').mapped(
                    'stock_valuation_layer_ids').sudo().unlink()
                    if rec.sudo().mapped('move_byproduct_ids').mapped('account_move_ids'):
                        accounting_ids = rec.sudo().mapped('move_byproduct_ids').mapped('account_move_ids')
                        accounting_ids.sudo().write({'state':'draft','name':'/'})
                        # accounting_ids.sudo().unlink()
                        accounting_ids.sudo().mapped('line_ids').sudo().write({'parent_state':'draft'})
                        accounting_ids.sudo().mapped('line_ids').sudo().unlink()

            if rec.sudo().mapped('move_dest_ids'):
                rec.sudo().mapped('move_dest_ids').sudo().write(
                    {'state': 'draft'})
                rec.sudo().mapped('move_dest_ids').mapped(
                    'move_line_ids').sudo().write({'state': 'draft'})
                rec.sudo().mapped('move_dest_ids')._sh_unreseve_qty()
                
                    
                if self._check_account_installed():
                    rec.sudo().mapped('move_dest_ids').mapped(
                    'stock_valuation_layer_ids').sudo().unlink()
                    if rec.sudo().mapped('move_dest_ids').mapped('account_move_ids'):
                        accounting_ids = rec.sudo().mapped('move_dest_ids').mapped('account_move_ids')
                        accounting_ids.sudo().write({'state':'draft','name':'/'})
                        # accounting_ids.sudo().unlink()
                        accounting_ids.sudo().mapped('line_ids').sudo().write({'parent_state':'draft'})
                        accounting_ids.sudo().mapped('line_ids').sudo().unlink()

            if rec.sudo().mapped('move_finished_ids'):
                rec.sudo().mapped('move_finished_ids').sudo().write(
                    {'state': 'draft'})
                rec.sudo().mapped('move_finished_ids').mapped(
                    'move_line_ids').sudo().write({'state': 'draft'})
                rec.sudo().mapped('move_finished_ids')._sh_unreseve_qty()
                
                if self._check_account_installed():
                    rec.sudo().mapped('move_finished_ids').mapped(
                    'stock_valuation_layer_ids').sudo().unlink()
                    if rec.sudo().mapped('move_finished_ids').mapped('account_move_ids'):
                        accounting_ids = rec.sudo().mapped('move_finished_ids').mapped('account_move_ids')
                        accounting_ids.sudo().write({'state':'draft','name':'/'})
                        # accounting_ids.sudo().unlink()
                        accounting_ids.sudo().mapped('line_ids').sudo().write({'parent_state':'draft'})
                        accounting_ids.sudo().mapped('line_ids').sudo().unlink()

            if rec.sudo().mapped('finished_move_line_ids'):
                rec.sudo().mapped('finished_move_line_ids').sudo().write(
                    {'state': 'draft'})
            rec.sudo().write({'state': 'draft'})
            
            if rec.sudo().mapped('picking_ids'):
                rec.sudo().mapped('picking_ids').mapped(
                    'move_ids_without_package').sudo().write({'state': 'draft'})
                
                rec.sudo().mapped('picking_ids').mapped('move_ids_without_package').mapped(
                    'move_line_ids').sudo().write({'state': 'draft'})
                
                rec.sudo().mapped('picking_ids').mapped(
                    'move_ids_without_package')._sh_unreseve_qty()
                
                if self._check_account_installed():
                    rec.sudo().mapped('picking_ids').mapped('move_ids_without_package').mapped(
                        'stock_valuation_layer_ids').sudo().unlink()
                
                rec.sudo().mapped('picking_ids').write({'state': 'draft'})
                
            rec.sudo().write({'state': False})

    def action_mrp_cancel_delete(self):
        for rec in self:
            if rec.company_id.cancel_child_mo:
                domain = [('origin', '=', rec.name)]
                find_child_mo = self.env['mrp.production'].search(domain)
                if find_child_mo:
                    for data in find_child_mo:
                        data.action_mrp_cancel_delete()
            # rec.process_action_mrp_cancel_delete()

            if rec.sudo().mapped('move_raw_ids'):
                rec.sudo().mapped('move_raw_ids').sudo().write(
                    {'state': 'draft'})
                rec.sudo().mapped('move_raw_ids').mapped(
                    'move_line_ids').sudo().write({'state': 'draft'})
            rec.sudo().mapped('move_raw_ids')._sh_unreseve_qty()

            if self._check_account_installed():

                if rec.sudo().mapped('move_raw_ids').mapped('account_move_ids'):
                    accounting_ids = rec.sudo().mapped('move_raw_ids').mapped('account_move_ids')
                    
                    accounting_ids.sudo().write({'state':'cancel','name':'/'})

                    accounting_ids.unlink()

                    accounting_ids.sudo().mapped('line_ids').sudo().write({'parent_state':'draft'})
                    accounting_ids.sudo().mapped('line_ids').sudo().unlink()
            
            rec.sudo().mapped('move_raw_ids').mapped('move_line_ids').sudo().unlink()
            rec.sudo().mapped('move_raw_ids').sudo().unlink()

            if self._check_account_installed():
                rec.sudo().mapped('move_raw_ids').mapped(
                    'stock_valuation_layer_ids').sudo().unlink()

            if rec.sudo().mapped('workorder_ids'):
                rec.sudo().mapped('workorder_ids').write({'state': 'ready'})

            if rec.sudo().mapped('move_byproduct_ids'):
                rec.sudo().mapped('move_byproduct_ids').sudo().write(
                    {'state': 'draft'})
                rec.sudo().mapped('move_byproduct_ids').mapped(
                    'move_line_ids').sudo().write({'state': 'draft'})
                rec.sudo().mapped('move_byproduct_ids')._sh_unreseve_qty()
                if self._check_account_installed():
                    if rec.sudo().mapped('move_byproduct_ids').mapped('account_move_ids'):
                        accounting_ids = rec.sudo().mapped('move_byproduct_ids').mapped('account_move_ids')
                        accounting_ids.sudo().write({'state':'cancel','name':'/'})

                        accounting_ids.sudo().unlink()
                        accounting_ids.sudo().mapped('line_ids').sudo().write({'parent_state':'draft'})
                        accounting_ids.sudo().mapped('line_ids').sudo().unlink()
                    
                rec.sudo().mapped('move_byproduct_ids').mapped('move_line_ids').sudo().unlink()
                rec.sudo().mapped('move_byproduct_ids').sudo().unlink()
                if self._check_account_installed():
                    rec.sudo().mapped('move_byproduct_ids').mapped(
                        'stock_valuation_layer_ids').sudo().unlink()

            if rec.sudo().mapped('move_dest_ids'):
                rec.sudo().mapped('move_dest_ids').sudo().write(
                    {'state': 'draft'})
                rec.sudo().mapped('move_dest_ids').mapped(
                    'move_line_ids').sudo().write({'state': 'draft'})
                rec.sudo().mapped('move_dest_ids')._sh_unreseve_qty()
                if self._check_account_installed():
                    if rec.sudo().mapped('move_dest_ids').mapped('account_move_ids'):
                        accounting_ids = rec.sudo().mapped('move_dest_ids').mapped('account_move_ids')
                        
                        accounting_ids.sudo().write({'state':'cancel','name':'/'})
                        accounting_ids.sudo().unlink()
                        accounting_ids.sudo().mapped('line_ids').sudo().write({'parent_state':'draft'})
                        accounting_ids.sudo().mapped('line_ids').sudo().unlink()
                    
                rec.sudo().mapped('move_dest_ids').mapped('move_line_ids').sudo().unlink()
                rec.sudo().mapped('move_dest_ids').sudo().unlink()
                if self._check_account_installed():
                    rec.sudo().mapped('move_dest_ids').mapped(
                        'stock_valuation_layer_ids').sudo().unlink()

            if rec.sudo().mapped('move_finished_ids'):
                rec.sudo().mapped('move_finished_ids').sudo().write(
                    {'state': 'draft'})
                rec.sudo().mapped('move_finished_ids').mapped(
                    'move_line_ids').sudo().write({'state': 'draft'})
                rec.sudo().mapped('move_finished_ids')._sh_unreseve_qty()
                if self._check_account_installed():

                    if rec.sudo().mapped('move_finished_ids').mapped('account_move_ids'):
                        accounting_ids = rec.sudo().mapped('move_finished_ids').mapped('account_move_ids')
                        accounting_ids.sudo().write({'state':'cancel','name':'/'})
                        accounting_ids.sudo().unlink()

                        accounting_ids.sudo().mapped('line_ids').sudo().write({'parent_state':'draft'})
                        accounting_ids.sudo().mapped('line_ids').sudo().unlink()
                    
                    
                rec.sudo().mapped('move_finished_ids').mapped('move_line_ids').sudo().unlink()
                rec.sudo().mapped('move_finished_ids').sudo().unlink()
                if self._check_account_installed():
                    rec.sudo().mapped('move_finished_ids').mapped(
                        'stock_valuation_layer_ids').sudo().unlink()

            if rec.sudo().mapped('finished_move_line_ids'):
                rec.sudo().mapped('finished_move_line_ids').sudo().write(
                    {'state': 'draft'})
                rec.sudo().mapped('finished_move_line_ids').sudo().unlink()

            if rec.sudo().mapped('picking_ids'):
                rec.sudo().mapped('picking_ids').mapped(
                    'move_ids_without_package').sudo().write({'state': 'draft'})
                rec.sudo().mapped('picking_ids').mapped('move_ids_without_package').mapped(
                    'move_line_ids').sudo().write({'state': 'draft'})
                rec.sudo().mapped('picking_ids').mapped(
                    'move_ids_without_package')._sh_unreseve_qty()
                if self._check_account_installed():
                    rec.sudo().mapped('picking_ids').mapped('move_ids_without_package').mapped(
                        'stock_valuation_layer_ids').sudo().unlink()
                rec.sudo().mapped('picking_ids').write({'state': 'draft'})
            
            # update draft to cancel
            rec.sudo().write({'state': 'cancel'})

            rec.sudo().unlink()

    def sh_cancel(self):
        if self.company_id.cancel_child_mo:

            domain = [('origin', '=', self.name)]
            find_child_mo = self.env['mrp.production'].search(domain)

            if find_child_mo:
                for data in find_child_mo:

                    data.sh_cancel()
        
        # self.process_the_cancel()

        if self.company_id.mrp_operation_type == 'cancel':
            self.action_mrp_cancel()
        
        elif self.company_id.mrp_operation_type == 'cancel_draft':
            self.action_mrp_cancel_draft()
        elif self.company_id.mrp_operation_type == 'cancel_delete':
            self.action_mrp_cancel_delete()

            return {
                'name':'Manufacturing Orders',
                'type':'ir.actions.act_window',
                'res_model':'mrp.production',
                'view_type':'list',
                'view_mode':'list,form',
                'target':'current',
            }

    def _check_account_installed(self):
        account_app = self.env['ir.module.module'].sudo().search([('name', '=', 'account')], limit=1)
        if account_app.state != 'installed':
            return False
        else:
            return True



    