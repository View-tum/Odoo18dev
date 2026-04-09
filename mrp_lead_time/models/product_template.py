from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = "product.template"

    mfg_lead_time = fields.Integer(
        string="MFG Lead Time",
        help="(365 custom) Specify the manufacturing lead time in days. This value will be copied to the Sales Order Line.",
    )
