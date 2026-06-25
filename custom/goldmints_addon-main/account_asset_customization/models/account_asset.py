from odoo import api, fields, models


class AccountAsset(models.Model):
    _inherit = "account.asset"

    responsible_id = fields.Many2one(
        comodel_name="res.users",
        string="Responsible",
        help="(365 custom) ผู้รับผิดชอบสินทรัพย์",
    )

    asset_location = fields.Char("Asset Location")

    asset_location_id = fields.Many2one(
        comodel_name="account.analytic.account",
        domain="[('plan_id.is_asset_location', '=', True)]",
        string="Asset Location",
        help="(365 custom) แผนกงาน/สถานที่เก็บสินทรัพย์",
    )

    last_post_depreciation_date = fields.Date(
        string="Last Post Depreciation Date",
        compute="_compute_last_post_depreciation_date",
        store=True,
    )

    @api.depends("depreciation_move_ids.state", "depreciation_move_ids.date")
    def _compute_last_post_depreciation_date(self):
        for asset in self:
            posted_moves = asset.depreciation_move_ids.filtered(lambda m: m.state == "posted")
            if posted_moves:
                asset.last_post_depreciation_date = max(posted_moves.mapped("date"))
            else:
                asset.last_post_depreciation_date = False
