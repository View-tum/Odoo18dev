from odoo import models, _
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tools import float_is_zero

class AccountBankStatement(models.Model):
    _inherit = "account.bank.statement"

    def action_auto_match_cheques(self):
        matched_cheques = self.env["account.bank.statement.line"]
        matched_fees = self.env["account.bank.statement.line"]
        skipped_lines = []
        failed_lines = []

        for statement in self:
            if statement.state != 'open':
                continue
            
            threshold = abs(statement.company_id.cheque_auto_reconcile_threshold or 0.0)
            rounding_account = statement.company_id.cheque_rounding_account_id

            for line in statement.line_ids.filtered(lambda l: not l.is_reconciled):
                if not line.payment_ref:
                    continue

                try:
                    with self.env.cr.savepoint():
                        result = line._auto_match_cheque_statement_line(threshold, rounding_account)
                        if result == "cheque":
                            matched_cheques |= line
                        elif result == "fee":
                            matched_fees |= line
                        elif result:
                            skipped_lines.append(result)
                except Exception as error:
                    failed_lines.append("%s: %s" % (line.payment_ref, error))

        message_parts = []
        if matched_cheques:
            message_parts.append(_("Matched cheque lines: %s") % len(matched_cheques))
        if matched_fees:
            message_parts.append(_("Matched bank fee lines: %s") % len(matched_fees))
        if skipped_lines:
            message_parts.append(_("Skipped lines: %s") % len(skipped_lines))
        if failed_lines:
            message_parts.append(_("Failed lines: %s") % len(failed_lines))

        message = "\n".join(message_parts) or _("No cheque lines were matched.")
        for statement in self:
            statement.message_post(body=message.replace("\n", "<br/>"))

        notification_type = failed_lines and "warning" or "success"
        if failed_lines:
            message = "%s\n%s" % (message, "\n".join(failed_lines[:5]))

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Auto Match Cheques"),
                "message": message,
                "type": notification_type,
                "sticky": bool(failed_lines),
            },
        }


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    def _auto_match_cheque_statement_line(self, threshold, rounding_account):
        self.ensure_one()
        cheque_no = self.payment_ref.strip()
        cheques = self.env['cheque.inbound.outbound'].search([
            ('name', '=', cheque_no),
            ('state', '=', 'bank_deposit')
        ])

        if len(cheques) != 1:
            if self._can_auto_match_cheque_fee_line(cheque_no, threshold, rounding_account):
                self._auto_match_cheque_fee_line(rounding_account, self.currency_id or self.company_currency_id)
                return "fee"
            return _("Cheque %s was not uniquely found at Bank Deposit stage.") % cheque_no

        cheque = cheques[0]
        currency = self.currency_id or self.company_currency_id
        payment = cheque.payment_ids[:1] or cheque.payment_id
        amount_difference = abs(self.amount) - cheque.amount

        if payment and abs(amount_difference) <= threshold:
            self._auto_match_cheque_payment_line(cheque, payment, amount_difference, rounding_account, currency)
            return "cheque"

        if self.amount < 0 and abs(self.amount) <= threshold and rounding_account:
            self._auto_match_cheque_fee_line(rounding_account, currency)
            return "fee"

        return _("Cheque %s difference is outside threshold.") % cheque_no

    def _can_auto_match_cheque_fee_line(self, cheque_no, threshold, rounding_account):
        if not rounding_account or self.amount >= 0 or abs(self.amount) > threshold:
            return False
        return len(self.env['cheque.inbound.outbound'].search([
            ('name', '=', cheque_no),
            ('state', 'in', ('bank_deposit', 'paid', 'transform')),
        ])) == 1

    def _auto_match_cheque_payment_line(self, cheque, payment, amount_difference, rounding_account, currency):
        self.matched_payment_ids = [Command.set([payment.id])]

        if cheque.cheque_journal_entry_id and cheque.cheque_journal_entry_id != self.move_id:
            move = cheque.cheque_journal_entry_id
            cheque.cheque_journal_entry_id = False
            cheque.cheque_validation_entry_id = False
            move.button_draft()
            move.with_context(force_delete=True).unlink()

        cheque.cheque_journal_entry_id = self.move_id.id
        cheque.cheque_validation_entry_id = self.move_id.id

        manual_balance = self.amount - cheque.amount if self.amount > 0 else cheque.amount - abs(self.amount)
        self._replace_auto_cheque_manual_line(manual_balance, rounding_account, currency)
        self.action_reconcile()

    def _auto_match_cheque_fee_line(self, rounding_account, currency):
        self.matched_payment_ids = [Command.clear()]
        self._replace_auto_cheque_manual_line(-self.amount_residual, rounding_account, currency)
        self.action_reconcile()

    def _replace_auto_cheque_manual_line(self, balance, rounding_account, currency):
        auto_lines = self.matched_manual_ids.filtered(lambda line: line.name == _("Auto cheque difference"))
        if auto_lines:
            auto_lines.unlink()
        if float_is_zero(balance, precision_rounding=currency.rounding):
            return
        if not rounding_account:
            raise UserError(_("Please configure Cheque Rounding Account before auto-matching cheque differences."))
        self.matched_manual_ids = [Command.create({
            'account_id': rounding_account.id,
            'name': _("Auto cheque difference"),
            'balance': balance,
        })]
