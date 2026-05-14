from odoo import api, fields, models, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    settlement_move_ids = fields.Many2many(
        'account.move', 
        compute='_compute_settlement_move_ids', 
        string='Settlement Entries'
    )
    settlement_move_count = fields.Integer(
        compute='_compute_settlement_move_ids', 
        string='Settlement Count'
    )

    def _compute_settlement_move_ids(self):
        for move in self:
            matched_moves = self.env['account.move']
            if move.state == 'posted':
                for line in move.line_ids.filtered(lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable')):
                    partials = line.matched_debit_ids | line.matched_credit_ids
                    for partial in partials:
                        matched_line = partial.debit_move_id if partial.credit_move_id == line else partial.credit_move_id
                        if matched_line.move_id.ref and matched_line.move_id.ref.startswith('PAY-SETTLE'):
                            matched_moves |= matched_line.move_id
            move.settlement_move_ids = matched_moves
            move.settlement_move_count = len(matched_moves)

    def action_view_settlement_moves(self):
        self.ensure_one()
        return {
            'name': _('Settlement Entries'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.settlement_move_ids.ids)],
        }
