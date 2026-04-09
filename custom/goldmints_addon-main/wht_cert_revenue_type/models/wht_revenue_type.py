from odoo import models, fields

class WhtRevenueType(models.Model):
    _name = 'wht.revenue.type'
    _description = 'WHT Revenue Type Master Data'

    code = fields.Char(string='Revenue Type', required=True, help="e.g., SER, DIV")
    name = fields.Char(string='Description', required=True, help="e.g., ค่าบริการ")
    wht_rate = fields.Float(string='WHT Rate (%)', required=True)
    active = fields.Boolean(default=True)