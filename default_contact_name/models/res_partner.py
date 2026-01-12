from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    default_contact_name = fields.Char(string="Default Contact Name")
