from odoo import fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    user_id = fields.Many2one(
        "res.users",
        related="partner_id.user_id",
        string="Salesperson",
        readonly=True,
    )
