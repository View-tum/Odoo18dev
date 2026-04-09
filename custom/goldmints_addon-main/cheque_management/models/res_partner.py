from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    payee_name_ids = fields.One2many(
        "res.partner.payee.name",
        "partner_id",
        string="Payee Names",
    )
