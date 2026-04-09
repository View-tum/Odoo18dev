from odoo import api, fields, models, _


class AccountMoveInherit(models.Model):
    _inherit = "account.move"

    old_number = fields.Char(string='Old System Number', help="Document number from old system.")





