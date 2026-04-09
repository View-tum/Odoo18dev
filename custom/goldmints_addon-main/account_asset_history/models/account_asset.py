from odoo import models, fields, api


class AccountAsset(models.Model):
    _inherit = "account.asset"

    history_record_ids = fields.One2many(
        comodel_name="asset.history.record",
        inverse_name="asset_id",
        string="Asset History Records",
    )
    history_count = fields.Integer(
        string="History Count",
        compute="_compute_history_count",
    )

    @api.depends("history_record_ids")
    def _compute_history_count(self):
        for asset in self:
            asset.history_count = len(asset.history_record_ids)

    def action_view_asset_history(self):
        self.ensure_one()
        action = self.env.ref("account_asset_history.action_asset_history_record").read()[0]
        action["domain"] = [("asset_id", "=", self.id)]
        action["context"] = {"default_asset_id": self.id}
        return action
