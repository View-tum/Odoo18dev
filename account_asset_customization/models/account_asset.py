from odoo import fields, models


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
