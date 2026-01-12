from odoo import fields, models

class ResCompany(models.Model):
    _inherit = 'res.company'

    sale_default_analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Default Sale Analytic Account',
        check_company=True,
    )
