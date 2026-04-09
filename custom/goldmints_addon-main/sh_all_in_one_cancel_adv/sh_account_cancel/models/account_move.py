# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import models

class Invoice(models.Model):
    _inherit = 'account.move'

    def action_invoice_cancel(self):
        for rec in self:

            move = rec
            move_line_ids = move.sudo().mapped('line_ids')
            reconcile_ids = []
            if move_line_ids:
                reconcile_ids = move_line_ids.sudo().mapped('id')
            reconcile_lines = self.env['account.partial.reconcile'].sudo().search(
                ['|', ('credit_move_id', 'in', reconcile_ids), ('debit_move_id', 'in', reconcile_ids)])
            payments = False
            if reconcile_lines:
                payments = self.env['account.payment'].search(['|', ('invoice_line_ids.id', 'in', reconcile_lines.mapped(
                    'credit_move_id').ids), ('invoice_line_ids.id', 'in', reconcile_lines.mapped('debit_move_id').ids)])

                reconcile_lines.sudo().unlink()
            else:
                payments = self.matched_payment_ids

            if payments:

                payment_ids = payments
                if payment_ids.sudo().mapped('move_id').mapped('line_ids'):
                    payment_lines = payment_ids.sudo().mapped('move_id').mapped('line_ids')
                    reconcile_ids = payment_lines.sudo().mapped('id')

                    reconcile_lines = self.env['account.partial.reconcile'].sudo().search(
                        ['|', ('credit_move_id', 'in', reconcile_ids), ('debit_move_id', 'in', reconcile_ids)])
                    if reconcile_lines:
                        reconcile_lines.sudo().unlink()
                    move.mapped(
                        'line_ids.analytic_line_ids').sudo().unlink()

            if payments:
                payment_ids = payments
                payment_ids.sudo().mapped('move_id').write(
                    {'state': 'draft', 'name': '/'})

                payment_ids.sudo().mapped('move_id').mapped(
                    'line_ids').sudo().write({'parent_state': 'draft'})
                # payment_ids.sudo().mapped('move_id').mapped('line_ids').sudo().unlink()


                if rec.company_id.payment_operation_type == 'cancel':
                    
                    payment_ids.sudo().write({'state': 'canceled'})

                elif rec.company_id.payment_operation_type == 'cancel_draft':
                    payment_ids.sudo().write({'state': 'draft' })

                elif rec.company_id.payment_operation_type == 'cancel_delete':
                    payment_ids.sudo().write(
                        {'state': 'draft', })
                    payment_ids.sudo().unlink()

                # payment_ids.sudo().mapped('move_id').with_context(
                #     {'force_delete': True}).unlink()

            move_line_ids.sudo().write({'parent_state': 'draft'})
            move.sudo().write({'state': 'draft', 'name': '/'})

            rec.sudo().write({'state': 'cancel'})

    def action_invoice_cancel_draft(self):
        for rec in self:
            move = rec
            move_line_ids = move.sudo().mapped('line_ids')
            reconcile_ids = []
            if move_line_ids:
                reconcile_ids = move_line_ids.sudo().mapped('id')
            reconcile_lines = self.env['account.partial.reconcile'].sudo().search(
                ['|', ('credit_move_id', 'in', reconcile_ids), ('debit_move_id', 'in', reconcile_ids)])

            payments = False
            if reconcile_lines:
                payments = self.env['account.payment'].search(['|', ('invoice_line_ids.id', 'in', reconcile_lines.mapped(
                    'credit_move_id').ids), ('invoice_line_ids.id', 'in', reconcile_lines.mapped('debit_move_id').ids)])

                reconcile_lines.sudo().unlink()
            else:
                payments = rec.matched_payment_ids

            if payments:
                payment_ids = payments
                if payment_ids.sudo().mapped('move_id').mapped('line_ids'):
                    payment_lines = payment_ids.sudo().mapped('move_id').mapped('line_ids')
                    reconcile_ids = payment_lines.sudo().mapped('id')

                    reconcile_lines = self.env['account.partial.reconcile'].sudo().search(
                        ['|', ('credit_move_id', 'in', reconcile_ids), ('debit_move_id', 'in', reconcile_ids)])
                    if reconcile_lines:
                        reconcile_lines.sudo().unlink()
                    move.mapped('line_ids.analytic_line_ids').sudo().unlink()

            if payments:
                payment_ids.sudo().mapped('move_id').write({'state': 'draft', 'name': '/'})
                payment_ids.sudo().mapped('move_id').mapped('line_ids').sudo().write({'parent_state': 'draft'})
                payment_ids.sudo().mapped('move_id').mapped('line_ids').sudo().unlink()

                if rec.company_id.payment_operation_type == 'cancel':
                    payment_ids.sudo().write({'state': 'canceled'})
                elif rec.company_id.payment_operation_type == 'cancel_draft':
                    payment_ids.sudo().write({'state': 'draft'})
                elif rec.company_id.payment_operation_type == 'cancel_delete':
                    payment_ids.sudo().write({'state': 'draft'})
                    payment_ids.sudo().unlink()

            move_line_ids.sudo().write({'parent_state': 'draft'})
            move.sudo().write({'state': 'draft'})

            rec.sudo().write({'state': 'draft', 'name': '/'})
           

    def action_invoice_cancel_delete(self):
        for rec in self:
            move = rec
            move_line_ids = move.sudo().mapped('line_ids')
            reconcile_ids = []
            if move_line_ids:
                reconcile_ids = move_line_ids.sudo().mapped('id')
            reconcile_lines = self.env['account.partial.reconcile'].sudo().search(
                ['|', ('credit_move_id', 'in', reconcile_ids), ('debit_move_id', 'in', reconcile_ids)])

            payments = False
            if reconcile_lines:
                payments = self.env['account.payment'].search(['|', ('invoice_line_ids.id', 'in', reconcile_lines.mapped(
                    'credit_move_id').ids), ('invoice_line_ids.id', 'in', reconcile_lines.mapped('debit_move_id').ids)])
                reconcile_lines.sudo().unlink()
            else:
                payments = rec.matched_payment_ids

            if payments:
                payment_ids = payments
                if payment_ids.sudo().mapped('move_id').mapped('line_ids'):
                    payment_lines = payment_ids.sudo().mapped('move_id').mapped('line_ids')
                    reconcile_ids = payment_lines.sudo().mapped('id')
                    
                    reconcile_lines = self.env['account.partial.reconcile'].sudo().search(
                        ['|', ('credit_move_id', 'in', reconcile_ids), ('debit_move_id', 'in', reconcile_ids)])
                    if reconcile_lines:
                        reconcile_lines.sudo().unlink()
                    move.mapped('line_ids.analytic_line_ids').sudo().unlink()

            if payments:
                payment_ids.sudo().mapped('move_id').write(
                    {'state': 'draft', 'name': '/'})
                payment_ids.sudo().mapped('move_id').mapped(
                    'line_ids').sudo().write({'parent_state': 'draft'})
                payment_ids.sudo().mapped('move_id').mapped('line_ids').sudo().unlink()

                if rec.company_id.payment_operation_type == 'cancel':
                    payment_ids.sudo().write({'state': 'canceled'})
                elif rec.company_id.payment_operation_type == 'cancel_draft':
                    payment_ids.sudo().write({'state': 'draft'})
                elif rec.company_id.payment_operation_type == 'cancel_delete':
                    payment_ids.sudo().write({'state': 'draft'})
                    payment_ids.sudo().unlink()

            move_line_ids.sudo().write({'parent_state': 'draft'})
            move.sudo().write({'state': 'draft'})

            rec.sudo().write({'state': 'draft', 'name': '/'})

            # Ensure that the invoice is deleted after all the state changes
            if rec.company_id.invoice_operation_type == 'cancel_delete':
                rec.sudo().with_context({'force_delete': True}).unlink()

  



    def sh_cancel(self):
        move = self
        move_line_ids = move.sudo().mapped('line_ids')
        
        reconcile_ids = []
        if move_line_ids:
            reconcile_ids = move_line_ids.sudo().mapped('id')
        reconcile_lines = self.env['account.partial.reconcile'].sudo().search(
            ['|', ('credit_move_id', 'in', reconcile_ids), ('debit_move_id', 'in', reconcile_ids)])

        payments = False
        if reconcile_lines:
            payments = self.env['account.payment'].search([
                '|', 
                ('move_id.line_ids.id', 'in', reconcile_lines.mapped('credit_move_id').ids),  # Correct reference to line_ids via move_id
                ('move_id.line_ids.id', 'in', reconcile_lines.mapped('debit_move_id').ids)  # Correct reference to line_ids via move_id
            ])
            reconcile_lines.sudo().unlink()
        else:
            payments = self.matched_payment_ids

        if payments:
            payment_ids = payments
            if payment_ids.sudo().mapped('move_id').mapped('line_ids'):
                payment_lines = payment_ids.sudo().mapped('move_id').mapped('line_ids')
                reconcile_ids = payment_lines.sudo().mapped('id')

                reconcile_lines = self.env['account.partial.reconcile'].sudo().search(
                    ['|', ('credit_move_id', 'in', reconcile_ids), ('debit_move_id', 'in', reconcile_ids)])
                if reconcile_lines:
                    reconcile_lines.sudo().unlink()
                move.mapped('line_ids.analytic_line_ids').sudo().unlink()

        if payments:
            # payment_ids.sudo().mapped('move_id').write({'state': 'draft', 'name': '/'})
            # payment_ids.sudo().mapped('move_id').mapped('line_ids').sudo().write({'parent_state': 'draft'})
            # payment_ids.sudo().mapped('move_id').mapped('line_ids').sudo().unlink()

            if self.company_id.payment_operation_type == 'cancel':
                payment_ids.sudo().write({'state': 'canceled'})
            elif self.company_id.payment_operation_type == 'cancel_draft':
                payment_ids.sudo().write({'state': 'draft'})
                payment_ids.sudo().mapped('move_id').with_context({'force_delete': True}).unlink()
            elif self.company_id.payment_operation_type == 'cancel_delete':
                payment_ids.sudo().write({'state': 'draft'})
                payment_ids.sudo().unlink()

        move_line_ids.sudo().write({'parent_state': 'draft'})
        move.sudo().write({'state': 'draft'})

        if self.company_id.invoice_operation_type == 'cancel':
            self.sudo().write({'state': 'cancel'})
        elif self.company_id.invoice_operation_type == 'cancel_draft':
            self.sudo().write({'state': 'draft', 'name': '/'})
        
        elif self.company_id.invoice_operation_type == 'cancel_delete':
            self.sudo().write({'state': 'draft', 'name': '/'})

        if self.company_id.invoice_operation_type == 'cancel_delete':
            self.sudo().with_context({'force_delete': True}).unlink()
            return {
                'name': 'Invoices',
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_type': 'form',
                'view_mode': 'list,kanban,form',
                'target': 'current',
            }
