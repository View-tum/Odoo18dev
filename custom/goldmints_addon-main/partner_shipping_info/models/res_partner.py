from odoo import models, fields


class ResPartner(models.Model):
    _inherit = "res.partner"

    shipping_mark = fields.Text(
        string="Shipping Mark", help="(365 custom) Shipping Mark for the partner"
    )
    # incoterm = fields.Text(
    #     string="Incoterm Description", help="(365 custom) Incoterm description"
    # )
    
    incoterm = fields.Many2one(
        'account.incoterms', 'Incoterm',
        help="(365 custom) International Commercial Terms are a series of predefined commercial terms used in international transactions.")
