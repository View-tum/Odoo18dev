from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    # Some downstream modules refer to website_id; add a placeholder if the field is absent.
    website_id = fields.Many2one(
        "website",
        string="Website",
        default=False,
        help="Placeholder field for compatibility with imports referencing website_id.",
    )
