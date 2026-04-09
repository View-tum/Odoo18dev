from odoo import fields, models


class SaleSequenceType(models.Model):
    _name = "sale.sequence.type"
    _description = "Sale Sequence Type"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
    market_scope = fields.Selection(
        selection=[
            ("domestic", "ในประเทศ"),
            ("inter", "ต่างประเทศ"),
        ],
        string="Market Scope",
        default="domestic",
        help="ระบุว่าเอกสารประเภทนี้สำหรับขายในประเทศหรือต่างประเทศ",
    )
