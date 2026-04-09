from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    inter_vat_id = fields.Many2one(
        related="company_id.inter_vat_id",
        readonly=False,
    )
    inter_journal_id = fields.Many2one(
        related="company_id.inter_journal_id",
        readonly=False,
    )
    inter_fiscal_position_id = fields.Many2one(
        related="company_id.inter_fiscal_position_id",
        readonly=False,
    )
