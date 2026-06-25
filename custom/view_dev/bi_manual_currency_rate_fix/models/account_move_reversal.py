from odoo import models


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    def reverse_moves(self, is_modify=False):
        """
        Override to automatically unreconcile credit notes.
        This ensures partial payments on the original invoice are not hidden by the reversal.
        """
        action = super().reverse_moves(is_modify=is_modify)
        for invoice in self.move_ids:
            # Odoo 18 uses reversal_move_ids (One2many)
            for cn_move in invoice.reversal_move_ids:
                cn_move.line_ids.remove_move_reconcile()
        return action
