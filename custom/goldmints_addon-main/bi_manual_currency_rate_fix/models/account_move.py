from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    reversal_move_count = fields.Integer(
        string='Number of Credit Notes',
        compute='_compute_reversal_move_count',
    )

    def _compute_reversal_move_count(self):
        reversal_data = self.env['account.move']._read_group(
            [('reversed_entry_id', 'in', self.ids)],
            ['reversed_entry_id'], ['__count']
        )
        data_map = {reversed_entry.id: count for reversed_entry, count in reversal_data}
        for move in self:
            move.reversal_move_count = data_map.get(move.id, 0)

    def action_view_reversal_moves(self):
        self.ensure_one()
        reversal_moves = self.env['account.move'].search([('reversed_entry_id', '=', self.id)])
        action = {
            'type': 'ir.actions.act_window',
            'name': 'Credit Notes',
            'res_model': 'account.move',
            'domain': [('id', 'in', reversal_moves.ids)],
            'context': {'default_reversed_entry_id': self.id},
        }
        if len(reversal_moves) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': reversal_moves.id,
            })
        else:
            action.update({
                'view_mode': 'list,form',
            })
        return action

    def _reconcile_reversed_moves(self, reverse_moves, move_reverse_cancel):
        if self and not self.company_id[:1].auto_reconcile_reversals:
            return reverse_moves
        return super()._reconcile_reversed_moves(reverse_moves, move_reverse_cancel)
