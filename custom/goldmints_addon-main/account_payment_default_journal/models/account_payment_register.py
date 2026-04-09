from odoo import api, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    def _has_explicit_context_journal(self):
        """Respect explicit journal passed by another flow/custom module.

        Example: group payment wizard passes ``default_journal_id`` and expects
        the payment popup to keep that journal instead of being overwritten by
        company AP/AR defaults.
        """
        return bool(self.env.context.get('default_journal_id'))

    def _has_explicit_context_payment_method_line(self):
        """Respect explicit payment method line from caller context."""
        return bool(self.env.context.get('default_payment_method_line_id'))

    @api.depends(
        'can_edit_wizard',
        'company_id',
        'payment_type',
        'company_id.pmt_ap_journal_id',
        'company_id.pmt_ar_journal_id',
    )
    def _compute_journal_id(self):
        super()._compute_journal_id()
        for wizard in self:
            if not wizard.can_edit_wizard:
                continue
            if wizard._has_explicit_context_journal():
                # Keep the explicit choice from the caller (e.g. group payment).
                continue
            if wizard.payment_type == 'outbound' and wizard.company_id.pmt_ap_journal_id:
                wizard.journal_id = wizard.company_id.pmt_ap_journal_id
            elif wizard.payment_type == 'inbound' and wizard.company_id.pmt_ar_journal_id:
                wizard.journal_id = wizard.company_id.pmt_ar_journal_id

    @api.depends(
        'payment_type',
        'journal_id',
        'company_id.pmt_ap_payment_method_id',
        'company_id.pmt_ar_payment_method_id',
    )
    def _compute_payment_method_line_id(self):
        super()._compute_payment_method_line_id()
        for wizard in self:
            if not wizard.journal_id:
                continue
            if wizard._has_explicit_context_payment_method_line():
                # Another flow set the payment method line explicitly.
                continue
            preferred_line = False
            if wizard.payment_type == 'outbound' and wizard.company_id.pmt_ap_payment_method_id:
                preferred_line = wizard.company_id.pmt_ap_payment_method_id
            elif wizard.payment_type == 'inbound' and wizard.company_id.pmt_ar_payment_method_id:
                preferred_line = wizard.company_id.pmt_ar_payment_method_id
            if preferred_line and preferred_line.journal_id == wizard.journal_id:
                wizard.payment_method_line_id = preferred_line
