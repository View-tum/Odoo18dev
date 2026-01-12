from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_domestic_export = fields.Boolean(
        string="Domestic Purchase (Export)",
        help="Check this box if the customer buys domestically but sells internationally. "
             "When selected, VAT will use the normal rate instead of the Inter VAT, "
             "and the Fiscal Position will not be applied.",
    )
