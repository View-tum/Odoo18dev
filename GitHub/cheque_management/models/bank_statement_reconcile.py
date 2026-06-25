from odoo import models, _
from odoo.exceptions import UserError


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    def _get_related_cheques_for_reconcile(self):
        cheques = self.env["cheque.inbound.outbound"]
        cheques |= self.matched_payment_ids.mapped("cheque_inbound_outbound_ids")
        cheques |= self.matched_move_line_ids.mapped(
            "move_id.cheque_inbound_outbound_id"
        )
        return cheques.filtered(lambda c: c)

    def action_reconcile(self):
        for line in self:
            cheques = line._get_related_cheques_for_reconcile()
            allowed_states = ("bank_deposit", "transform")
            if cheques and any(cheque.state not in allowed_states for cheque in cheques):
                raise UserError(_("Cheque must be at Bank Deposit or Transform stage before reconciliation."))
            if cheques:
                for cheque in cheques:
                    if cheque.cheque_journal_entry_id and cheque.cheque_journal_entry_id != line.move_id:
                        move = cheque.cheque_journal_entry_id
                        cheque.cheque_journal_entry_id = False
                        cheque.cheque_validation_entry_id = False
                        move.button_draft()
                        move.with_context(force_delete=True).unlink()
                    cheque.cheque_journal_entry_id = line.move_id.id
                    cheque.cheque_validation_entry_id = line.move_id.id

        res = super().action_reconcile()
        if isinstance(res, dict):
            return res

        for line in self:
            if not line.is_reconciled:
                continue
            cheques = line._get_related_cheques_for_reconcile()
            if line.journal_id:
                cheques = cheques.filtered(
                    lambda c: c.bank_account_journal_id == line.journal_id
                )
            cheques = cheques.filtered(lambda c: c.state in ("bank_deposit", "transform"))
            if cheques:
                cheques.action_validate()

        return res

    def _get_reconcile_lines(self):
        lines = self.env["account.move.line"]
        
        for payment in self.matched_payment_ids:
            # Always match against the payment's outstanding line directly to prevent double-posting
            lines += payment.move_id.line_ids.filtered(
                lambda line: not line.reconciled
                and line.account_id.account_type
                not in ("asset_receivable", "liability_payable")
                and line.account_id.reconcile
            )

        lines += self.matched_move_line_ids

        return lines.filtered(
            lambda line: line.move_id.status not in ("void", "transform", "cancel")
        )
