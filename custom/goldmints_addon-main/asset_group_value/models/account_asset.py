from odoo import api, fields, models

class AccountAsset(models.Model):
    _inherit = "account.asset"

    total_group_value = fields.Monetary(
        string="Total Group Value",
        compute="_compute_total_group_value",
        help="Sum of original value of this parent asset and all its children.",
    )

    @api.depends("original_value", "children_ids.original_value")
    def _compute_total_group_value(self):
        for asset in self:
            if asset.children_ids:
                # If it's a parent, sum itself + all children
                total = asset.original_value + sum(asset.children_ids.mapped("original_value"))
                asset.total_group_value = total
            elif asset.parent_id:
                # If it's a child, show the parent's total group value for consistency in list views
                asset.total_group_value = asset.parent_id.total_group_value
            else:
                # Standalone asset
                asset.total_group_value = asset.original_value
