from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sale_default_analytic_account_id = fields.Many2one(
        related='company_id.sale_default_analytic_account_id',
        string='Default Sale Analytic Account',
        readonly=False,
        check_company=True,
        help="Select a default analytic account to be applied to new Sale Order Lines."
    )
