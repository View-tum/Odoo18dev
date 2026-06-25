from odoo import api, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get('default_journal_id') or self.env.context.get('default_payment_method_line_id'):
            return res

        seed = self._get_payment_seed_from_context()
        payment_type = (
            res.get('payment_type')
            or self.env.context.get('default_payment_type')
            or seed.get('payment_type')
        )
        company = (
            self.env['res.company'].browse(res.get('company_id')).exists()
            or seed.get('company')
            or self.env.company
        )
        method_line = self._get_default_supported_payment_method_line(company, payment_type)
        if method_line:
            res['journal_id'] = method_line.journal_id.id
            res['payment_method_line_id'] = method_line.id
        else:
            preferred_journal = self._get_company_default_journal_for(company, payment_type)
            if preferred_journal:
                res['journal_id'] = preferred_journal.id
        return res

    @api.model
    def _get_payment_seed_from_context(self):
        lines = self._get_active_payment_move_lines()
        if not lines:
            return {}
        companies = lines.company_id
        if len(companies.root_id) > 1:
            return {}
        balance = sum(lines.mapped('balance'))
        company = min(companies, key=lambda company: len(company.parent_ids))
        return {
            'company': company,
            'payment_type': 'inbound' if balance > 0.0 else 'outbound',
        }

    @api.model
    def _get_active_payment_move_lines(self):
        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get('active_ids') or []
        if not active_ids:
            return self.env['account.move.line']
        if active_model == 'account.move.line':
            lines = self.env['account.move.line'].browse(active_ids).exists()
        elif active_model == 'account.move':
            moves = self.env['account.move'].browse(active_ids).exists()
            lines = moves.line_ids
        else:
            return self.env['account.move.line']
        return lines.filtered(
            lambda line: line.account_type in ('asset_receivable', 'liability_payable')
            and not line.reconciled
        )

    def _has_explicit_context_journal(self):
        return bool(self.env.context.get('default_journal_id'))

    def _has_explicit_context_payment_method_line(self):
        return bool(self.env.context.get('default_payment_method_line_id'))

    def _get_company_default_journal(self):
        self.ensure_one()
        if self.payment_type == 'outbound':
            return self.company_id.pmt_ap_journal_id
        if self.payment_type == 'inbound':
            return self.company_id.pmt_ar_journal_id
        return self.env["account.journal"]

    def _get_company_default_payment_method_line(self):
        self.ensure_one()
        if self.payment_type == 'outbound':
            return self.company_id.pmt_ap_payment_method_id
        if self.payment_type == 'inbound':
            return self.company_id.pmt_ar_payment_method_id
        return self.env["account.payment.method.line"]

    @api.model
    def _get_company_default_journal_for(self, company, payment_type):
        if payment_type == 'outbound':
            return company.pmt_ap_journal_id
        if payment_type == 'inbound':
            return company.pmt_ar_journal_id
        return self.env["account.journal"]

    @api.model
    def _get_company_default_payment_method_line_for(self, company, payment_type):
        if payment_type == 'outbound':
            return company.pmt_ap_payment_method_id
        if payment_type == 'inbound':
            return company.pmt_ar_payment_method_id
        return self.env["account.payment.method.line"]

    def _is_deferred_instrument_payment_method_line(self, method_line):
        return bool(
            method_line
            and (
                getattr(method_line, "is_cheque_incoming_line", False)
                or getattr(method_line, "is_cheque_outgoing_line", False)
                or getattr(method_line, "is_bank_draft_incoming_line", False)
                or getattr(method_line, "is_bank_draft_outgoing_line", False)
                or method_line.code in ("cheque", "cheque_incoming", "cheque_outgoing", "bank_draft")
            )
        )

    def _is_supported_default_payment_method_line(self, method_line):
        return bool(
            method_line
            and (
                method_line.payment_account_id
                or self._is_deferred_instrument_payment_method_line(method_line)
            )
        )

    @api.model
    def _find_postable_payment_method_line(self, company, payment_type, journal=False):
        if not payment_type:
            return self.env["account.payment.method.line"]
        if journal:
            candidates = journal._get_available_payment_method_lines(payment_type)
        else:
            candidates = self.env["account.payment.method.line"].search(
                [
                    ("journal_id.company_id", "=", company.id),
                    ("journal_id.type", "in", ("bank", "cash")),
                    ("payment_type", "=", payment_type),
                    ("payment_account_id", "!=", False),
                ]
            )
        postable = candidates.filtered(lambda line: line.payment_account_id)
        manual_line = postable.filtered(lambda line: line.code == "manual")[:1]
        return manual_line or postable[:1]

    @api.model
    def _get_default_supported_payment_method_line(self, company, payment_type):
        preferred_line = self._get_company_default_payment_method_line_for(company, payment_type)
        if self._is_supported_default_payment_method_line(preferred_line):
            return preferred_line
        preferred_journal = self._get_company_default_journal_for(company, payment_type)
        return (
            self._find_postable_payment_method_line(company, payment_type, preferred_journal)
            or self._find_postable_payment_method_line(company, payment_type)
        )

    def _get_postable_payment_method_line(self, journal=False):
        self.ensure_one()
        return self._find_postable_payment_method_line(self.company_id, self.payment_type, journal)

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
                continue
            preferred_line = wizard._get_company_default_payment_method_line()
            if wizard._is_supported_default_payment_method_line(preferred_line):
                wizard.journal_id = preferred_line.journal_id
                continue

            preferred_journal = wizard._get_company_default_journal()
            fallback_line = wizard._get_postable_payment_method_line(preferred_journal)
            if not fallback_line:
                fallback_line = wizard._get_postable_payment_method_line()
            if fallback_line:
                wizard.journal_id = fallback_line.journal_id
            elif preferred_journal:
                wizard.journal_id = preferred_journal

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
            preferred_line = False
            if wizard.payment_type == 'outbound' and wizard.company_id.pmt_ap_payment_method_id:
                preferred_line = wizard.company_id.pmt_ap_payment_method_id
            elif wizard.payment_type == 'inbound' and wizard.company_id.pmt_ar_payment_method_id:
                preferred_line = wizard.company_id.pmt_ar_payment_method_id
            if (
                preferred_line
                and preferred_line.journal_id == wizard.journal_id
                and wizard._is_supported_default_payment_method_line(preferred_line)
            ):
                wizard.payment_method_line_id = preferred_line
                continue

            fallback_line = wizard._get_postable_payment_method_line(wizard.journal_id)
            if not fallback_line:
                fallback_line = wizard._get_postable_payment_method_line()
            if fallback_line:
                if fallback_line.journal_id != wizard.journal_id:
                    wizard.journal_id = fallback_line.journal_id
                wizard.payment_method_line_id = fallback_line
