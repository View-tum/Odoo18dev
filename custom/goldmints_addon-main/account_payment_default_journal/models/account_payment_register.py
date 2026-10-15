from odoo import api, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    def _has_explicit_context_journal(self):
        return bool(self.env.context.get('default_journal_id'))

    def _has_explicit_context_payment_method_line(self):
        return bool(self.env.context.get('default_payment_method_line_id'))

    def _get_payment_default_config(self):
        self.ensure_one()
        if self.payment_type == 'outbound':
            return self.company_id.pmt_ap_journal_id, self.company_id.pmt_ap_payment_method_id
        if self.payment_type == 'inbound':
            return self.company_id.pmt_ar_journal_id, self.company_id.pmt_ar_payment_method_id
        return self.env['account.journal'], self.env['account.payment.method.line']

    def _get_usable_payment_method_lines(self, journal=None):
        self.ensure_one()
        journal = journal or self.journal_id
        if not journal:
            return self.env['account.payment.method.line']
        return journal._get_available_payment_method_lines(self.payment_type).filtered('payment_account_id')

    def _get_usable_default_journal(self):
        self.ensure_one()
        preferred_journal, preferred_line = self._get_payment_default_config()
        if preferred_journal:
            usable_lines = self._get_usable_payment_method_lines(preferred_journal)
            if usable_lines and (not preferred_line or preferred_line in usable_lines):
                return preferred_journal
        for journal in self.available_journal_ids.filtered(lambda item: item.type in ('bank', 'cash')):
            if self._get_usable_payment_method_lines(journal):
                return journal
        return self.env['account.journal']

    def _normalize_default_payment_routing(self, normalize_journal=True):
        for wizard in self:
            if not wizard.can_edit_wizard:
                continue
            target_journal = wizard.journal_id
            if normalize_journal and not wizard._has_explicit_context_journal():
                target_journal = wizard._get_usable_default_journal() or target_journal
            if not target_journal:
                continue
            usable_lines = wizard._get_usable_payment_method_lines(target_journal)
            target_line = wizard.payment_method_line_id
            if not wizard._has_explicit_context_payment_method_line() and usable_lines:
                _preferred_journal, preferred_line = wizard._get_payment_default_config()
                if preferred_line and preferred_line.journal_id == target_journal and preferred_line in usable_lines:
                    target_line = preferred_line
                elif target_line not in usable_lines:
                    target_line = usable_lines[:1]
            vals = {}
            if target_journal != wizard.journal_id:
                vals['journal_id'] = target_journal.id
            if target_line and target_line != wizard.payment_method_line_id:
                vals['payment_method_line_id'] = target_line.id
            if vals:
                wizard.write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        keep_payload_journal = self.env.context.get('keep_payment_register_payload_journal')
        explicit_journal_flags = [
            bool(keep_payload_journal or vals.get('settlement_journal_id'))
            for vals in vals_list
        ]
        wizards = super().create(vals_list)
        for wizard, has_explicit_journal in zip(wizards, explicit_journal_flags):
            wizard._normalize_default_payment_routing(normalize_journal=not has_explicit_journal)
        return wizards

    @api.depends(
        'can_edit_wizard',
        'company_id',
        'payment_type',
        'company_id.pmt_ap_journal_id',
        'company_id.pmt_ar_journal_id',
        'company_id.pmt_ap_payment_method_id',
        'company_id.pmt_ar_payment_method_id',
        'available_journal_ids',
    )
    def _compute_journal_id(self):
        super()._compute_journal_id()
        for wizard in self:
            if not wizard.can_edit_wizard:
                continue
            if wizard._has_explicit_context_journal():
                continue
            journal = wizard._get_usable_default_journal()
            if journal:
                wizard.journal_id = journal

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
                continue
            usable_lines = wizard._get_usable_payment_method_lines()
            if not usable_lines:
                continue
            _preferred_journal, preferred_line = wizard._get_payment_default_config()
            if preferred_line and preferred_line.journal_id == wizard.journal_id and preferred_line in usable_lines:
                wizard.payment_method_line_id = preferred_line
            elif wizard.payment_method_line_id not in usable_lines:
                wizard.payment_method_line_id = usable_lines[:1]
