# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import models


class LandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    def _remove_journal_entries(self):
        """
        This function removes journal entries and related accounting entries for a specific stock
        account.
        """
        self.ensure_one()
        account_move = self.sudo().account_move_id
        account_move_line_ids = account_move.sudo().mapped('line_ids')
        reconcile_ids = []
        if account_move_line_ids:
            reconcile_ids = account_move_line_ids.sudo().mapped('id')
        reconcile_lines = self.env['account.partial.reconcile'].sudo().search(['|',('credit_move_id','in',reconcile_ids),('debit_move_id','in',reconcile_ids)])
        if reconcile_lines:
            reconcile_lines.sudo().unlink()
        account_move.mapped('line_ids.analytic_line_ids').sudo().unlink()
        account_move.sudo().write({'state':'draft','name':'/'})
        account_move.sudo().with_context({'force_delete':True}).unlink()

    # For Update standard price on LAnded Cost Cancellation
    def update_standard_price(self):
        """
        This function updates the standard price of a product based on its valuation method and cost
        method.
        """
        for cost in self:
            cost = cost.with_company(cost.company_id)
            for line in cost.valuation_adjustment_lines.filtered(lambda line: line.move_id):
                product = line.move_id.product_id

                if product.valuation != "real_time":
                    continue

                if product.cost_method == 'average':
                    new_price = line.additional_landed_cost / product.quantity_svl if product.quantity_svl else line.additional_landed_cost
                    if new_price < 0:
                        new_price = -(new_price)
                    if new_price > 0:
                        standard_price = product.with_company(cost.company_id).sudo().standard_price
                        product.with_company(cost.company_id).sudo().with_context(disable_auto_svl=True).standard_price = standard_price - new_price
                    else:
                        return

    def action_landed_cost_cancel(self):
        """
        This function cancels a landed cost and removes associated journal entries and valuation layers.
        """
        for rec in self:
            rec.update_standard_price()
            if rec.mapped('valuation_adjustment_lines'):
                rec.mapped('valuation_adjustment_lines').sudo().unlink()
            rec._remove_journal_entries()

            if rec.mapped('stock_valuation_layer_ids'):
                rec.mapped('stock_valuation_layer_ids').sudo().unlink()

            rec.sudo().write({'state': 'cancel'})

    def action_landed_cost_cancel_draft(self):
        """
        This function set draft state of a landed cost and removes related journal entries and
        valuation adjustment lines.
        """
        for rec in self:
            rec.update_standard_price()
            if rec.mapped('valuation_adjustment_lines'):
                rec.mapped('valuation_adjustment_lines').sudo().unlink()

            rec._remove_journal_entries()

            if rec.mapped('stock_valuation_layer_ids'):
                rec.mapped('stock_valuation_layer_ids').sudo().unlink()

            rec.sudo().write({'state': 'draft'})

    def action_landed_cost_cancel_delete(self):
        """
        This function cancels and deletes landed cost records, removing associated journal entries and
        valuation layers.
        """
        for rec in self:
            rec.update_standard_price()
            if rec.mapped('valuation_adjustment_lines'):
                rec.mapped('valuation_adjustment_lines').sudo().unlink()

            rec._remove_journal_entries()

            if rec.mapped('stock_valuation_layer_ids'):
                rec.mapped('stock_valuation_layer_ids').sudo().unlink()

            rec.sudo().write({'state': 'cancel'})
            rec.sudo().unlink()

    def sh_cancel(self):
        if self.company_id.landed_cost_operation_type == 'cancel':
            self.action_landed_cost_cancel()
        elif self.company_id.landed_cost_operation_type == 'cancel_draft':
            self.action_landed_cost_cancel_draft()
        elif self.company_id.landed_cost_operation_type == 'cancel_delete':
            self.action_landed_cost_cancel_delete()

            return {
                'name': 'Landed Costs',
                'type': 'ir.actions.act_window',
                'res_model': 'stock.landed.cost',
                'view_type': 'form',
                'view_mode': 'list,form',
                'target': 'current',
            }