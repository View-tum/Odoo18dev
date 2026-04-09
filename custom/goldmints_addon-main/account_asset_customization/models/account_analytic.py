from odoo import fields, models


class AccountAnalyticPlan(models.Model):
    _inherit = "account.analytic.plan"

    is_asset_location = fields.Boolean(
        string="Is Asset Location",
        help="(365 custom) Indicates whether this stock location is designated for storing assets.",
    )
