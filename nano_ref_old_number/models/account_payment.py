from odoo import api, fields, models, _


class AccountPaymentInherit(models.Model):
    _inherit = "account.payment"

    old_number = fields.Char(string='Old System Number', help="Document number from old system.")





