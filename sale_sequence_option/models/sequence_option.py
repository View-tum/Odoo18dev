from odoo import fields, models


class IrSequenceOption(models.Model):
    _inherit = "ir.sequence.option"

    model = fields.Selection(
        selection_add=[("sale.order", "sale.order")],
        ondelete={"sale.order": "cascade"},
    )
