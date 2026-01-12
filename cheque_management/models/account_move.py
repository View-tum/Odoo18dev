from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    cheque_inbound_outbound_id = fields.Many2one("cheque.inbound.outbound", "Cheque")

    @api.model
    def _get_invoice_in_payment_state(self):
        """Hook to give the state when the invoice becomes fully paid. This is necessary because the users working
        with only invoicing don't want to see the 'in_payment' state. Then, this method will be overridden in the
        accountant module to enable the 'in_payment' state."""
        state = super()._get_invoice_in_payment_state()
        reconciled_lines = self.line_ids.filtered(
            lambda line: line.account_id.account_type
            in ("asset_receivable", "liability_payable")
        )
        partials = (
            reconciled_lines.matched_debit_ids | reconciled_lines.matched_credit_ids
        )
        counterpart_moves = (
            partials.debit_move_id.move_id | partials.credit_move_id.move_id
        ) - self
        cheque_payments = counterpart_moves.origin_payment_id.filtered(
            lambda p: p.cheque_inbound_outbound_ids
            or p.payment_method_line_id.is_cheque_incoming_line
            or p.payment_method_line_id.is_cheque_outgoing_line
        )
        if not cheque_payments:
            return state

        cheques = cheque_payments.mapped("cheque_inbound_outbound_ids")
        if not cheques:
            return "in_payment"

        if any(cheque.state != "paid" for cheque in cheques):
            return "in_payment"

        # Guard: Ensure cheque amount matches sum of payments to prevent premature Paid status
        for cheque in cheques:
            payment_total = sum(cheque.payment_ids.mapped("amount"))
            if not cheque.currency_id.is_zero(cheque.amount - payment_total):
                return "in_payment"

        return "paid"

    def _compute_payment_state(self):
        super()._compute_payment_state()
        for move in self:
            reconciled_lines = move.line_ids.filtered(
                lambda line: line.account_id.account_type
                in ("asset_receivable", "liability_payable")
            )
            partials = (
                reconciled_lines.matched_debit_ids | reconciled_lines.matched_credit_ids
            )
            counterpart_moves = (
                partials.debit_move_id.move_id | partials.credit_move_id.move_id
            ) - move
            cheque_payments = counterpart_moves.origin_payment_id.filtered(
                lambda p: p.cheque_inbound_outbound_ids
                or p.payment_method_line_id.is_cheque_incoming_line
                or p.payment_method_line_id.is_cheque_outgoing_line
            )
            if not cheque_payments:
                continue

            cheques = cheque_payments.mapped("cheque_inbound_outbound_ids")
            is_all_paid = False
            if cheques and all(cheque.state == "paid" for cheque in cheques):
                is_all_paid = True
                # Guard: Ensure cheque amount matches sum of payments
                for cheque in cheques:
                    payment_total = sum(cheque.payment_ids.mapped("amount"))
                    if not cheque.currency_id.is_zero(cheque.amount - payment_total):
                        is_all_paid = False
                        break

            if is_all_paid:
                if move.payment_state == "in_payment":
                    move.payment_state = "paid"
            else:
                # If cheque(s) not yet validated or amount mismatch, keep invoice in payment.
                if move.payment_state == "paid":
                    move.payment_state = "in_payment"
