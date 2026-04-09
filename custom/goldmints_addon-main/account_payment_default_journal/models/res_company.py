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

    @api.depends('pmt_ap_journal_id', 'pmt_ap_journal_id.outbound_payment_method_line_ids')
    def _compute_pmt_ap_payment_method_id(self):
        for company in self:
            if not company.pmt_ap_journal_id:
                company.pmt_ap_payment_method_id = False
                continue
            available = company.pmt_ap_journal_id._get_available_payment_method_lines('outbound')
            if company.pmt_ap_payment_method_id not in available:
                company.pmt_ap_payment_method_id = available[:1] or False

    @api.depends('pmt_ar_journal_id', 'pmt_ar_journal_id.inbound_payment_method_line_ids')
    def _compute_pmt_ar_payment_method_id(self):
        for company in self:
            if not company.pmt_ar_journal_id:
                company.pmt_ar_payment_method_id = False
                continue
            available = company.pmt_ar_journal_id._get_available_payment_method_lines('inbound')
            if company.pmt_ar_payment_method_id not in available:
                company.pmt_ar_payment_method_id = available[:1] or False

    def _inverse_pmt_ap_payment_method_id(self):
        # No-op inverse: field is stored+editable, actual value is written by ORM.
        return

    def _inverse_pmt_ar_payment_method_id(self):
        # No-op inverse: field is stored+editable, actual value is written by ORM.
        return
