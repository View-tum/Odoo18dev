# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    claim_id = fields.Many2one('crm.claim.ept', string='Claim')
    reversal_move_count = fields.Integer(compute='_compute_reversal_move_count')

    @api.depends('reversal_move_ids')
    def _compute_reversal_move_count(self):
        for move in self:
            move.reversal_move_count = len(move.reversal_move_ids)

    def action_view_reversal_moves(self):
        moves = self.mapped('reversal_move_ids')
        if not moves:
            return {'type': 'ir.actions.act_window_close'}

        move_types = set(moves.mapped('move_type'))
        if move_types <= {'out_receipt'}:
            action = self.env['ir.actions.actions']._for_xml_id('account.action_move_out_receipt_type')
        elif move_types <= {'in_receipt'}:
            action = self.env['ir.actions.actions']._for_xml_id('account.action_move_in_receipt_type')
        elif move_types <= set(self.get_sale_types(include_receipts=False)):
            action = self.env['ir.actions.actions']._for_xml_id('account.action_move_out_invoice_type')
        elif move_types <= set(self.get_purchase_types(include_receipts=False)):
            action = self.env['ir.actions.actions']._for_xml_id('account.action_move_in_invoice_type')
        else:
            action = self.env['ir.actions.actions']._for_xml_id('account.action_move_journal_line')

        if len(moves) > 1:
            action['domain'] = [('id', 'in', moves.ids)]
        else:
            form_view = [(self.env.ref('account.view_move_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [
                    (state, view) for state, view in action['views'] if view != 'form'
                ]
            else:
                action['views'] = form_view
            action['res_id'] = moves.id
        return action
