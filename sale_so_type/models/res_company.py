from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    inter_vat_id = fields.Many2one(
        "account.tax",
        string="Foreign VAT",
        help="Default VAT for foreign sales (SO Type = Foreign)",
    )
    inter_journal_id = fields.Many2one(
        "account.journal",
        string="Foreign Journal",
        domain=[("type", "=", "sale")],
        help="Default Journal for foreign sales (SO Type = Foreign)",
    )
    inter_fiscal_position_id = fields.Many2one(
        "account.fiscal.position",
        string="Foreign Fiscal Position",
        help="Default Fiscal Position for foreign sales (SO Type = Foreign)",
    )
