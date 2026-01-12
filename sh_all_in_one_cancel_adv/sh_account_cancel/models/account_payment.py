# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import models


class Payment(models.Model):
    _inherit = 'account.payment'

    def action_payment_cancel(self):
        for rec in self:
            if rec.sudo().mapped('move_id').mapped('line_ids'):
                payment_lines = rec.sudo().mapped('move_id').mapped('line_ids')
                reconcile_ids = payment_lines.sudo().mapped('id')

                reconcile_lines = self.env['account.partial.reconcile'].sudo().search(
                    ['|', ('credit_move_id', 'in', reconcile_ids), ('debit_move_id', 'in', reconcile_ids)])
                if reconcile_lines:
                    reconcile_lines.sudo().unlink()
            rec.sudo().mapped('move_id').write({'state': 'draft', 'name': '/'})

            rec.sudo().mapped('move_id').mapped(
                'line_ids').sudo().write({'parent_state': 'draft'})
            rec.sudo().mapped('move_id').mapped('line_ids').sudo().unlink()
#             rec.sudo().mapped('move_id').with_context({'force_delete':True}).unlink()
            rec.sudo().write({'state': 'canceled'})

    def action_payment_cancel_draft(self):
        for rec in self:
            if rec.sudo().mapped('move_id').mapped('line_ids'):
                payment_lines = rec.sudo().mapped('move_id').mapped('line_ids')
                reconcile_ids = payment_lines.sudo().mapped('id')
                reconcile_lines = self.env['account.partial.reconcile'].sudo().search(
                    ['|', ('credit_move_id', 'in', reconcile_ids), ('debit_move_id', 'in', reconcile_ids)])
                if reconcile_lines:
                    reconcile_lines.sudo().unlink()

            rec.sudo().mapped('move_id').write({'state': 'draft', 'name': '/'})
            rec.sudo().mapped('move_id').mapped(
                'line_ids').sudo().write({'parent_state': 'draft'})
#             rec.sudo().mapped('move_id').mapped('line_ids').sudo().unlink()
#             rec.sudo().mapped('move_id').with_context({'force_delete':True}).unlink()
            rec.sudo().write({'state': 'draft'})

    def action_payment_cancel_delete(self):
        for rec in self:

            if rec.sudo().mapped('move_id').mapped('line_ids'):
                payment_lines = rec.sudo().mapped('move_id').mapped('line_ids')
                reconcile_ids = payment_lines.sudo().mapped('id')
                reconcile_lines = self.env['account.partial.reconcile'].sudo().search(
                    ['|', ('credit_move_id', 'in', reconcile_ids), ('debit_move_id', 'in', reconcile_ids)])
                if reconcile_lines:
                    reconcile_lines.sudo().unlink()

            rec.sudo().mapped('move_id').write({'state': 'draft', 'name': '/'})
            rec.sudo().mapped('move_id').mapped(
                'line_ids').sudo().write({'parent_state': 'draft'})
            rec.sudo().mapped('move_id').mapped('line_ids').sudo().unlink()
#             rec.sudo().mapped('move_id').with_context({'force_delete':True}).unlink()
            rec.sudo().write({'state': 'draft'})
            rec.sudo().unlink()

    def sh_cancel(self):

        if self.sudo().mapped('move_id').mapped('line_ids'):
            payment_lines = self.sudo().mapped('move_id').mapped('line_ids')
            reconcile_ids = payment_lines.sudo().mapped('id')

            reconcile_lines = self.env['account.partial.reconcile'].sudo().search(
                ['|', ('credit_move_id', 'in', reconcile_ids), ('debit_move_id', 'in', reconcile_ids)])
            if reconcile_lines:
                reconcile_lines.sudo().unlink()

        self.sudo().mapped('move_id').write({'state': 'draft', 'name': '/'})
        self.sudo().mapped('move_id').mapped(
            'line_ids').sudo().write({'parent_state': 'draft'})
#         self.sudo().mapped('move_id').mapped('line_ids').sudo().unlink()

#         self.sudo().mapped('move_id').with_context({'force_delete':True}).unlink()

        if self.company_id.payment_operation_type == 'cancel':
            self.sudo().write({'state': 'canceled'})
        elif self.company_id.payment_operation_type == 'cancel_draft':
            self.sudo().write({'state': 'draft'})
        elif self.company_id.payment_operation_type == 'cancel_delete':
            self.sudo().write({'state': 'draft'})
            self.sudo().unlink()
            return {
                'name': 'Payments',
                'type': 'ir.actions.act_window',
                'res_model': 'account.payment',
                'view_type': 'form',
                'view_mode': 'list,kanban,form,graph',
                'target': 'current',
            }