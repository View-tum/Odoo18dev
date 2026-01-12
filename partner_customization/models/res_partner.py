from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = "res.partner"
    
    customer_credit_rating = fields.Char(
        string="Credit Rating",
        help="(365 custom) The financial creditworthiness rating of the customer"
    )
    shop_type = fields.Selection(
        [('pharma','Pharma'), ('non_pharma','Non Pharma')],
        default=False,
        help="(365 custom) The type of the customer's shop (e.g., Pharma, Non-Pharma)."
    )
    customer_group = fields.Selection(
        [('wholesale','Wholesale'), ('retail','Retail')],
        default=False,
        help="(365 custom) The group this customer belongs to for classification (e.g., Wholesale, Retail)."
    )
    change_delivery_address = fields.Boolean(
        string="Change Delivery Address",
        help="(365 custom) Flag to indicate this partner needs delivery address changes handled specially."
    )
    memo = fields.Text(
        string="Sale Note",
        help="(365 custom) Internal sales-related notes or memo about this customer."
    )
    
