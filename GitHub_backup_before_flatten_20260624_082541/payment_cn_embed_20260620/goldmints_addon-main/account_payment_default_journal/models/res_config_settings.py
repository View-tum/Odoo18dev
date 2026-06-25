from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pmt_ap_journal_id = fields.Many2one(
        related="company_id.pmt_ap_journal_id",
        readonly=False,
    )
    pmt_ar_journal_id = fields.Many2one(
        related="company_id.pmt_ar_journal_id",
        readonly=False,
    )
    pmt_ap_payment_method_id = fields.Many2one(
        related="company_id.pmt_ap_payment_method_id",
        readonly=False,
    )
    pmt_ar_payment_method_id = fields.Many2one(
        related="company_id.pmt_ar_payment_method_id",
        readonly=False,
    )
