from odoo import fields, models

class PaymentMethod(models.Model):
    _inherit = "payment.method"

    image = fields.Image(required=False)