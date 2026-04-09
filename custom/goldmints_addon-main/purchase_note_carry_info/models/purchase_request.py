from odoo import fields, models


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    purchase_note = fields.Text(
        string="Purchase Note",
        help="(365 custom) Internal note for this Purchase Request. This note will be automatically carried over to the Purchase Order and other related documents."
    )
