from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    is_reverse_cheque_entry = fields.Boolean('Is Reverse Cheque Entry?')
