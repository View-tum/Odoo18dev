from odoo import fields, models


class AddSignature(models.Model):
    _inherit = "ir.actions.report"

    show_signature = fields.Boolean(string="Signature Status", default=False)
    signature_image = fields.Binary(string="Approval Signature Image")