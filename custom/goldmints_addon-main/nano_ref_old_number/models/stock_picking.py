from odoo import api, fields, models, _


class StockPickingInherit(models.Model):
    _inherit = "stock.picking"

    old_number = fields.Char(string='Old System Number', help="Document number from old system.")





