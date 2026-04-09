from odoo import fields, models, api


class SaleCommissionRate(models.Model):
    _name = "sale.commission.rate"
    _description = "Sale Commission Rate"
    _order = "value asc"
    _rec_name = "name"

    name = fields.Char(
        string="Commission Rate Name",
        compute="_compute_name",
        store=True,
        readonly=True,
    )
    value = fields.Float(
        string="Commission Value",
        default=0.0,
        help="(365 custom) The percentage or fixed amount used to calculate sales commissions.",
    )
    description = fields.Char(
        string="Description",
        help="(365 custom) Detailed description of this commission rate.",
    )

    _sql_constraints = [
        ("rate_value_unique", "unique(value)", "Commission value must be unique."),
        ("value_positive", "CHECK(value >= 0)", "Commission value cannot be negative."),
    ]

    @api.depends("value")
    def _compute_name(self):
        for record in self:
            record.name = str(record.value) + "%"
