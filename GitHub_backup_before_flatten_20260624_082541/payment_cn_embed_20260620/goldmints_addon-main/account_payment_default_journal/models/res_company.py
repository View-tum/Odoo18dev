from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    pmt_ap_journal_id = fields.Many2one(
        "account.journal",
        string="Default AP Journal",
        domain="[('type', 'in', ('bank', 'cash'))]",
        check_company=True,
        help="Default journal for paying Vendor Bills (Outbound).",
    )
    pmt_ar_journal_id = fields.Many2one(
        "account.journal",
        string="Default AR Journal",
        domain="[('type', 'in', ('bank', 'cash'))]",
        check_company=True,
        help="Default journal for receiving Customer Invoices (Inbound).",
    )
    pmt_ap_payment_method_id = fields.Many2one(
        "account.payment.method.line",
        string="Default AP Payment Method",
        compute="_compute_pmt_ap_payment_method_id",
        inverse="_inverse_pmt_ap_payment_method_id",
        store=True,
        readonly=False,
        domain="[('journal_id', '=', pmt_ap_journal_id), ('payment_type', '=', 'outbound')]",
        check_company=True,
        help="Default payment method line for paying Vendor Bills.",
    )
    pmt_ar_payment_method_id = fields.Many2one(
        "account.payment.method.line",
        string="Default AR Payment Method",
        compute="_compute_pmt_ar_payment_method_id",
        inverse="_inverse_pmt_ar_payment_method_id",
        store=True,
        readonly=False,
        domain="[('journal_id', '=', pmt_ar_journal_id), ('payment_type', '=', 'inbound')]",
        check_company=True,
        help="Default payment method line for receiving Customer Invoices.",
    )

    def _is_deferred_instrument_payment_method_line(self, method_line):
        self.ensure_one()
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
        self.ensure_one()
        return bool(
            method_line
            and (
                method_line.payment_account_id
                or self._is_deferred_instrument_payment_method_line(method_line)
            )
        )

    def _get_supported_payment_method_line(self, journal, payment_type):
        self.ensure_one()
        if not journal:
            return self.env["account.payment.method.line"]
        available = journal._get_available_payment_method_lines(payment_type)
        supported = available.filtered(
            lambda line: self._is_supported_default_payment_method_line(line)
        )
        manual_line = supported.filtered(lambda line: line.code == "manual")[:1]
        return manual_line or supported[:1]

    @api.depends(
        'pmt_ap_journal_id',
        'pmt_ap_journal_id.outbound_payment_method_line_ids',
        'pmt_ap_journal_id.outbound_payment_method_line_ids.payment_account_id',
    )
    def _compute_pmt_ap_payment_method_id(self):
        for company in self:
            if not company.pmt_ap_journal_id:
                company.pmt_ap_payment_method_id = False
                continue
            if not company._is_supported_default_payment_method_line(company.pmt_ap_payment_method_id):
                company.pmt_ap_payment_method_id = company._get_supported_payment_method_line(
                    company.pmt_ap_journal_id,
                    'outbound',
                )

    @api.depends(
        'pmt_ar_journal_id',
        'pmt_ar_journal_id.inbound_payment_method_line_ids',
        'pmt_ar_journal_id.inbound_payment_method_line_ids.payment_account_id',
    )
    def _compute_pmt_ar_payment_method_id(self):
        for company in self:
            if not company.pmt_ar_journal_id:
                company.pmt_ar_payment_method_id = False
                continue
            if not company._is_supported_default_payment_method_line(company.pmt_ar_payment_method_id):
                company.pmt_ar_payment_method_id = company._get_supported_payment_method_line(
                    company.pmt_ar_journal_id,
                    'inbound',
                )

    def _inverse_pmt_ap_payment_method_id(self):
        return

    def _inverse_pmt_ar_payment_method_id(self):
        return
